"""Compute every analysis result once and cache it.

Outputs
  data/processed/*.parquet   tables the notebooks, dashboard and report read
  reports/key_metrics.json   the single source for every number quoted in the
                             README, memo and docs (regenerated on each run)
"""
from __future__ import annotations

import json
from dataclasses import replace
from datetime import date
from functools import lru_cache
from pathlib import Path

import numpy as np
import pandas as pd

from src import benchmarking, client, cost_model as cm, data, drivers, penalty as pen, shrinkage
from src.config import ROOT, load_config

METRICS_PATH = ROOT / "reports" / "key_metrics.json"


# ----------------------------------------------------------------- shared helpers
def payments() -> pd.Series:
    return data.condition_params()["base_payment_per_discharge"]


def penalty_params(**overrides) -> pen.PenaltyParams:
    c = load_config()["penalty_model"]
    base = pen.PenaltyParams(penalty_cap_pct=c["penalty_cap_pct"], hrrp_payment_share=c["hrrp_payment_share"],
                             neutrality_modifier=c["neutrality_modifier"])
    return replace(base, **overrides)


def program_params(preset: str = "broad", **overrides) -> cm.ProgramParams:
    cfg = load_config()
    spec = dict(cfg["intervention"]["presets"][preset])
    spec.pop("label", None)
    spec["target_conditions"] = tuple(spec["target_conditions"])
    pm = cfg["penalty_model"]
    p = cm.ProgramParams(**spec, penalty_cap_pct=pm["penalty_cap_pct"], hrrp_payment_share=pm["hrrp_payment_share"],
                         neutrality_modifier=pm["neutrality_modifier"], data_years=pm["performance_years"])
    return replace(p, **overrides)


def preset_label(preset: str) -> str:
    return load_config()["intervention"]["presets"][preset]["label"]


@lru_cache(maxsize=1)
def shrinkage_k() -> pd.Series:
    path = Path(load_config()["data"]["processed_dir"]) / "shrinkage_k.parquet"
    if path.exists():
        return pd.read_parquet(path).set_index("condition_code")["k"]
    return shrinkage.fit_k(data.table("fct_hospital_condition")).set_index("condition_code")["k"]


def model_inputs(facility_ids=None) -> cm.ModelInputs:
    hc = data.hospital_conditions()
    if facility_ids is not None:
        hc = hc[hc["facility_id"].isin(list(facility_ids))]
    return cm.ModelInputs.build(hc, payments(), shrinkage_k())


def pilot_hospitals(n: int | None = None) -> list[str]:
    """Client hospitals where each program dollar returns the most to the hospital (benefit-cost ratio),
    i.e. ranked on the penalty a heart failure / pneumonia program can actually address, not on total
    penalty (ranking on last year's total penalty picks hospitals at their peak: winner's curse)."""
    n = n or load_config()["intervention"]["pilot_hospitals_top_n"]
    m = model_inputs(client.client_ids())
    p = program_params("targeted")
    bcr = {}
    for fid in client.client_ids():
        t = cm.evaluate(m.subset([fid]), p)["totals"]
        bcr[fid] = t["benefit_cost_ratio"] if t["program_cost"] > 0 else -1.0
    return sorted(bcr, key=bcr.get, reverse=True)[:n]


def phase_in(m: cm.ModelInputs, p: cm.ProgramParams) -> pd.DataFrame:
    iv = load_config()["intervention"]
    start = iv["program_start"] if isinstance(iv["program_start"], date) else date.fromisoformat(str(iv["program_start"]))
    return cm.phase_in(m, p, start=start, first_fy=2027, n_years=iv["horizon_years"],
                       ramp_first_year=iv["ramp_first_year"], discount_rate=iv["discount_rate"])


def sensitivity_table(m: cm.ModelInputs, p: cm.ProgramParams, pct: float = 0.30) -> pd.DataFrame:
    """Every key input -30% / +30%: does the conclusion (sign of net benefit) change?"""
    base = cm.evaluate(m, p)["totals"]
    rows = []
    for name, label in cm.TORNADO_PARAMS.items():
        val = getattr(p, name)
        if val == 0:
            continue
        for direction, factor in (("-30%", 1 - pct), ("+30%", 1 + pct)):
            v = val * factor
            if name in ("reach", "ma_share", "hospital_share_of_savings"):
                v = min(v, 0.95)
            t = cm.evaluate(m, replace(p, **{name: v}))["totals"]
            rows.append({
                "parameter": name, "label": label, "change": direction, "value": v, "base_value": val,
                "hospital_net": t["hospital_net"], "combined_net": t["combined_net"],
                "hospital_sign_flips": bool(np.sign(t["hospital_net"]) != np.sign(base["hospital_net"])),
                "combined_sign_flips": bool(np.sign(t["combined_net"]) != np.sign(base["combined_net"])),
            })
    return pd.DataFrame(rows)


def client_peer_grid(hc: pd.DataFrame, dim: pd.DataFrame, ph: pd.DataFrame) -> list[dict]:
    """Each client hospital's percentile among its peers (same ownership and HRRP volume), by condition."""
    out = []
    for f in client.client_ids():
        b = benchmarking.benchmark(hc, dim, f).set_index("condition_code")["percentile_vs_peers"]
        s_ = benchmarking.peer_summary(dim, ph, f)
        out.append({"facility_id": f, "name": dim.set_index("facility_id").loc[f, "facility_name"],
                    "index": _r(s_["target_index"]), "index_percentile": _r(s_["index_percentile"], 1),
                    "n_peers": s_["n_peers"], **{c: _r(b.get(c), 1) for c in ["HF", "PN", "COPD", "AMI", "CABG", "HIP_KNEE"]}})
    return out


def pilot_unit_economics(m: cm.ModelInputs, p: cm.ProgramParams) -> dict:
    """Per avoided readmission: what the program costs vs what comes back (steady state)."""
    t = cm.evaluate(m, p)["totals"]
    n = t["readmissions_avoided"]
    return {"program_cost_per_readmission_avoided": _r(t["program_cost"] / n, 0),
            "penalty_relief_per_readmission_avoided": _r(t["avoided_penalty"] / n, 0),
            "payer_saving_per_readmission_avoided": _r(p.payment_per_readmission, 0),
            "lost_margin_per_readmission_avoided": _r(p.lost_margin_per_readmission, 0)}


def pilot_power(m: cm.ModelInputs, p: cm.ProgramParams, break_even_effect: float | None) -> dict:
    """Can a pilot of this size show the effect it needs? Two-group comparison of 30-day readmission
    (enrolled vs similar non-enrolled patients), 80% power, two-sided 5% test, equal group sizes."""
    from scipy.stats import norm
    res = cm.evaluate(m, p)
    rows = res["rows"][res["rows"]["targeted"]].copy()
    rows["effect"] = p.condition_effect(rows["condition_code"].to_numpy())
    rows["p0"] = rows["readmissions_avoided"] / (rows["enrollees"] * rows["effect"])   # baseline risk of enrollees
    w = rows["enrollees"]
    p0 = float((rows["p0"] * w).sum() / w.sum())
    base_rel = float((rows["effect"] * rows["p0"] * w).sum() / (rows["p0"] * w).sum())
    z = norm.ppf(0.975) + norm.ppf(0.80)

    def n_per_group(rel):
        p1 = p0 * (1 - rel)
        return float(z ** 2 * (p0 * (1 - p0) + p1 * (1 - p1)) / (p0 - p1) ** 2)

    def mde(n):
        lo, hi = 0.0, 0.99
        for _ in range(60):
            mid = (lo + hi) / 2
            lo, hi = (mid, hi) if n_per_group(mid) > n else (lo, mid)
        return (lo + hi) / 2
    per_year = float(res["totals"]["enrollees"])
    ramp = load_config()["intervention"]["ramp_first_year"]
    n12, n24 = per_year * ramp, per_year * (ramp + 1)
    be_rel = base_rel * (break_even_effect / p.relative_reduction) if break_even_effect else None
    return {"enrollees_per_year_steady": _r(per_year, 0), "enrolled_first_12_months": _r(n12, 0),
            "enrolled_first_24_months": _r(n24, 0), "baseline_readmission_risk_enrolled": _r(p0, 3),
            "base_case_relative_reduction": _r(base_rel, 3),
            "n_per_group_for_base_effect": _r(n_per_group(base_rel), 0),
            "n_per_group_for_break_even_effect": _r(n_per_group(be_rel), 0) if be_rel else None,
            "min_detectable_reduction_12m": _r(mde(n12), 3), "min_detectable_reduction_24m": _r(mde(n24), 3)}


def years_to_payback(df: pd.DataFrame, col: str = "hospital_net_cum") -> str:
    pos = df[df[col] > 0]
    return f"FY{int(pos['fiscal_year'].iloc[0])}" if len(pos) else f"not within FY{int(df['fiscal_year'].max())}"


def _r(x, nd=4):
    if x is None:
        return None
    if isinstance(x, (np.floating, float)):
        return None if np.isnan(x) else round(float(x), nd)
    if isinstance(x, (np.integer,)):
        return int(x)
    return x


# ----------------------------------------------------------------- build
def build() -> dict:
    cfg = load_config()
    seed = cfg["random_seed"]
    fct = data.table("fct_hospital_condition")
    dim = data.table("dim_hospital")
    ph = data.table("mart_penalty_hospital")
    pc = data.table("mart_penalty_condition")
    seg = data.table("mart_segment_summary")
    dq = data.table("dq_check_results")
    hc = data.hospital_conditions()
    names = dim.set_index("facility_id")["facility_name"].to_dict()

    # --- shrinkage (pass-through) ---------------------------------------------------
    k = shrinkage.fit_k(fct)
    data.save_table(k, "shrinkage_k")
    shrinkage_k.cache_clear()
    data.save_table(shrinkage.binned_check(fct), "shrinkage_bins")

    # --- drivers ---------------------------------------------------------------------
    coefs, reg_info = drivers.adjusted_associations(hc)
    data.save_table(coefs, "regression_coefs")
    curve = drivers.concentration_curve(ph)
    data.save_table(curve, "concentration_curve")
    mix = drivers.condition_mix(seg)

    # penalty per excess readmission above the threshold, by condition
    t = fct[fct["has_err"] & fct["is_payment_eligible"]].merge(pc[["facility_id", "condition_code", "penalty_contribution_annual"]],
                                                               on=["facility_id", "condition_code"])
    t["excess_above_threshold"] = (t["discharges_est_annual"] * t["expected_rate_pct"] / 100
                                   * np.maximum(t["err"] - t["penalty_threshold_err"], 0))
    cond = t.groupby("condition_code").agg(penalty=("penalty_contribution_annual", "sum"),
                                           excess_above_threshold=("excess_above_threshold", "sum"),
                                           expected_rate_pct=("expected_rate_pct", "median"))
    cond["penalty_per_excess_readmission"] = cond["penalty"] / cond["excess_above_threshold"]
    cond = cond.join(mix.set_index("condition_code")[["share_discharges", "share_excess_readmissions", "share_penalty",
                                                       "n_hospitals", "mean_err", "share_above_threshold",
                                                       "discharges_annual", "excess_readmissions_annual_pos"]])
    cond = cond.join(payments().rename("payment_per_discharge"))
    cond["penalty_per_excess_vs_readmission_cost"] = (cond["penalty_per_excess_readmission"]
                                                      / cfg["intervention"]["presets"]["broad"]["cost_per_readmission"])
    data.save_table(cond.reset_index(), "condition_summary")

    # --- penalty sensitivity (national + client) --------------------------------------
    ids = client.client_ids()
    rows = []
    for label, pp in [("Base case", penalty_params()),
                      ("Hidden discharges at minimum (25)", penalty_params(discharges_case="low")),
                      ("Hidden discharges at maximum", penalty_params(discharges_case="high")),
                      ("Threshold = 1.00 instead of national median", penalty_params(threshold_method="one")),
                      ("Payment per discharge -30%", penalty_params(payment_scale=0.7)),
                      ("Payment per discharge +30%", penalty_params(payment_scale=1.3))]:
        _, hh = pen.estimate(fct, payments(), pp)
        s = pen.summarize(hh)
        rows.append({"scenario": label, "n_hospitals_penalized": s["n_hospitals_penalized"],
                     "total_penalty": s["total_penalty"],
                     "client_penalty": float(hh.loc[hh["facility_id"].isin(ids), "penalty"].sum())})
    pen_sens = pd.DataFrame(rows)
    data.save_table(pen_sens, "penalty_sensitivity")

    # --- client group -----------------------------------------------------------------
    client_pen = (pc[pc["facility_id"].isin(ids)]
                  .merge(dim[["facility_id", "facility_name", "size_band", "ownership_group"]], on="facility_id"))
    client_h = ph[ph["facility_id"].isin(ids)].merge(
        dim[["facility_id", "facility_name", "city", "size_band", "ownership_group", "readmission_index",
             "n_conditions_with_err", "eligible_discharges_3yr"]], on="facility_id").sort_values(
        "penalty_est_annual", ascending=False)
    data.save_table(client_h, "client_hospitals")
    target = client.target_hospital_id()
    bench = benchmarking.benchmark(hc, dim, target)
    peer_sum = benchmarking.peer_summary(dim, ph, target)
    data.save_table(bench, "benchmark_target")

    # --- business case ------------------------------------------------------------------
    m_client = model_inputs(ids)
    pilot = pilot_hospitals()
    m_pilot = m_client.subset(pilot)
    p_broad, p_tgt = program_params("broad"), program_params("targeted")
    scen_defs = [
        ("broad_all", f"{preset_label('broad')} — all 8 hospitals", m_client, p_broad),
        ("targeted_all", f"{preset_label('targeted')} — all 8 hospitals", m_client, p_tgt),
        ("targeted_pilot", f"{preset_label('targeted')} — pilot at top-{len(pilot)} hospitals", m_pilot, p_tgt),
        ("targeted_pilot_risk30", "Pilot + 30% of payer savings shared back (shared-savings contract)", m_pilot,
         replace(p_tgt, hospital_share_of_savings=0.30)),
        ("targeted_pilot_no_rtm", "Pilot if today's penalty simply continued (no regression to the mean)", m_pilot,
         replace(p_tgt, persistence=1.0)),
        ("targeted_pilot_beds_refilled", "Pilot if freed beds are refilled (no lost margin)", m_pilot,
         replace(p_tgt, beds_refilled=True)),
        ("broad_fy2026_rules", "Broad program under FY2026 rules (no MA in score, 3-year window)", m_client,
         replace(p_broad, ma_share=0.0, window_years=3.0)),
    ]
    scen_rows, phase_frames = [], []
    for key, label, m, p in scen_defs:
        res = cm.evaluate(m, p)
        tt = res["totals"]
        ph_df = phase_in(m, p).assign(scenario=key)
        phase_frames.append(ph_df)
        scen_rows.append({"scenario": key, "label": label, **tt,
                          "payback": years_to_payback(ph_df),
                          "cum_hospital_net_6y": float(ph_df["hospital_net_cum"].iloc[-1]),
                          "cum_combined_net_6y": float(ph_df["combined_net_cum"].iloc[-1])})
        if key in ("broad_all", "targeted_pilot"):
            data.save_table(res["hospitals"].merge(dim[["facility_id", "facility_name", "size_band"]], on="facility_id"),
                            f"bc_hospitals_{key}")
            data.save_table(res["rows"], f"bc_rows_{key}")
    scen = pd.DataFrame(scen_rows)
    data.save_table(scen, "bc_scenarios")
    data.save_table(pd.concat(phase_frames, ignore_index=True), "bc_phase_in")

    tor = cm.tornado(m_pilot, p_tgt)
    data.save_table(tor, "bc_tornado")
    sens = sensitivity_table(m_pilot, p_tgt)
    data.save_table(sens, "bc_sensitivity")
    sens_broad = sensitivity_table(m_client, p_broad)
    data.save_table(sens_broad, "bc_sensitivity_broad")
    be = {
        "pilot_relative_reduction": cm.break_even(m_pilot, p_tgt, "relative_reduction", lo=0.0, hi=0.6),
        "pilot_cost_per_enrollee": cm.break_even(m_pilot, p_tgt, "cost_per_enrollee", lo=0.0, hi=3000.0),
        "broad_relative_reduction": cm.break_even(m_client, p_broad, "relative_reduction", lo=0.0, hi=0.6),
        "broad_cost_per_enrollee": cm.break_even(m_client, p_broad, "cost_per_enrollee", lo=0.0, hi=3000.0),
        "pilot_relative_reduction_combined": cm.break_even(m_pilot, p_tgt, "relative_reduction", "combined_net", 0.0, 0.6),
        "pilot_hospital_share_of_savings": cm.break_even(m_pilot, p_tgt, "hospital_share_of_savings", lo=0.0, hi=1.0),
    }
    g = cm.grid(m_pilot, p_tgt, "relative_reduction", np.round(np.arange(0.02, 0.305, 0.02), 3),
                "cost_per_enrollee", np.arange(100, 1001, 50))
    data.save_table(g, "bc_grid")
    ranges = {k_: tuple(v) for k_, v in cfg["intervention"]["ranges"].items()}
    mc = cm.monte_carlo(m_pilot, p_tgt, ranges, n=cfg["intervention"]["monte_carlo_runs"], seed=seed)
    data.save_table(mc, "bc_monte_carlo")

    # national: where would each design pay back on the hospital P&L?
    m_all = model_inputs(dim.loc[dim["is_payment_eligible"], "facility_id"])
    nat = {}
    nma = cfg["intervention"]["national_ma_share"]
    for key, p in (("broad", replace(p_broad, ma_share=nma)), ("targeted", replace(p_tgt, ma_share=nma))):
        hh = cm.evaluate(m_all, p)["hospitals"]
        run = hh[hh["program_runs"]]
        nat[key] = {"hospitals_running": int(len(run)), "hospitals_positive": int((run["hospital_net"] > 0).sum()),
                    "share_positive": float((run["hospital_net"] > 0).mean())}
        data.save_table(hh, f"bc_national_{key}")

    # --- python-side sanity checks -------------------------------------------------------
    _, h_py = pen.estimate(fct, payments(), penalty_params())
    diff = float((h_py.set_index("facility_id")["penalty"] - ph.set_index("facility_id")["penalty_est_annual"]).abs().max())
    kn = cfg["known_numbers"]
    n_pen = int(ph["is_penalized"].sum())
    mc2 = cm.monte_carlo(m_pilot, p_tgt, ranges, n=len(mc), seed=seed)   # same seed, same size => identical
    reproducible = bool(np.array_equal(mc2["hospital_net"].to_numpy(), mc["hospital_net"].to_numpy()))
    py_checks = pd.DataFrame([
        {"check_id": "P1", "category": "Consistency", "check_name": "SQL and Python penalty models agree (max difference per hospital)",
         "expected": "< $1", "actual": f"${diff:.6f}", "status": "PASS" if diff < 1 else "FAIL",
         "detail": "two independent implementations of the HRRP formula"},
        {"check_id": "P2", "category": "Known numbers", "check_name": "Estimated penalized hospitals vs CMS FY2026 (2,304)",
         "expected": f"within ±5% of {kn['fy2026_hospitals_penalized']:,}", "actual": f"{n_pen:,} ({n_pen / kn['fy2026_hospitals_penalized'] - 1:+.1%})",
         "status": "PASS" if abs(n_pen / kn["fy2026_hospitals_penalized"] - 1) <= 0.05 else "FAIL",
         "detail": "CMS Table 15 / FY2026 IPPS final rule impact analysis"},
        {"check_id": "P3", "category": "Known numbers", "check_name": "Estimated national penalty $ vs nearest CMS published totals ($316M-$361M)",
         "expected": "same order of magnitude", "actual": f"${ph['penalty_est_annual'].sum() / 1e6:,.0f}M",
         "status": "PASS" if 0.6 * kn["fy2026_total_penalty_reference_low"] <= ph["penalty_est_annual"].sum() <= 1.4 * kn["fy2026_total_penalty_reference_high"] else "WARN",
         "detail": "CMS did not publish an FY2026 dollar total; our payment assumptions are conservative (see assumptions A4)"},
        {"check_id": "P4", "category": "Reproducibility", "check_name": "Client group draw reproduces config.yaml (seed 42)",
         "expected": "True", "actual": str(client.check_client_group(dim)), "status": "PASS" if client.check_client_group(dim) else "FAIL",
         "detail": "8 hospitals, stratified by size"},
        {"check_id": "P5", "category": "Reproducibility", "check_name": "Monte Carlo with fixed seed gives identical results on re-run",
         "expected": "True", "actual": str(reproducible), "status": "PASS" if reproducible else "FAIL", "detail": f"seed {seed}"},
        {"check_id": "P6", "category": "Known numbers", "check_name": "Fitted shrinkage matches published measure reliability (HF pass-through at 1,019 cases ≈ 0.70)",
         "expected": "0.65-0.80", "actual": f"{1019 / (1019 + float(k.set_index('condition_code').loc['HF', 'k'])):.2f}",
         "status": "PASS" if 0.65 <= 1019 / (1019 + float(k.set_index('condition_code').loc['HF', 'k'])) <= 0.80 else "WARN",
         "detail": "Thompson et al. 2016: HF needs ~1,019 cases for 0.70 reliability"},
    ])
    dq_all = pd.concat([dq, py_checks], ignore_index=True)
    data.save_table(dq_all, "dq_checks_all")

    # --- key metrics -----------------------------------------------------------------------
    nat_seg = seg[(seg["segment_dimension"] == "National") & (seg["condition_code"] == "ALL")].iloc[0]
    elig = dim[dim["is_payment_eligible"]]
    pen_h = ph[ph["is_penalized"]]
    bt = bench.set_index("condition_code")
    by_dim = {}
    for d in ["Census region", "Ownership", "Volume", "Star rating", "Spending (MSPB)", "Emergency services"]:
        st = drivers.segment_table(seg, d)
        by_dim[d] = {r.segment_value: {"n_hospitals": int(r.n_hospitals), "mean_err": _r(r.mean_err),
                                       "ci_low": _r(r.mean_err_ci_low), "ci_high": _r(r.mean_err_ci_high),
                                       "share_penalized": _r(r.share_hospitals_penalized),
                                       "share_discharges": _r(r.share_discharges),
                                       "share_excess_readmissions": _r(r.share_excess_readmissions),
                                       "share_penalty": _r(r.share_penalty),
                                       "penalty_per_discharge": _r(r.penalty_per_discharge, 2)} for r in st.itertuples()}
    states = drivers.segment_table(seg, "State").sort_values("mean_err", ascending=False)
    sc = scen.set_index("scenario")
    metrics = {
        "data": {
            "hrrp_rows": int(len(fct)), "hrrp_hospitals": int(dim["facility_id"].nunique()),
            "matched_hospital_info": int(dim["in_hospital_info"].sum()),
            "unmatched": int((~dim["in_hospital_info"]).sum()), "maryland_hospitals": int(dim["is_maryland"].sum()),
            "payment_eligible_hospitals": int(len(elig)),
            "eligible_with_err": int((elig["n_conditions_with_err"] > 0).sum()),
            "hospital_condition_rows_with_err": int(fct["has_err"].sum()),
            "suppressed_count_rows": int((fct["reporting_status"] == "counts_suppressed").sum()),
            "imputed_share_of_discharges": _r(fct.loc[fct["discharges_imputed"], "discharges_est"].sum()
                                              / fct.loc[fct["has_err"], "discharges_est"].sum()),
            "imputed_share_hip_knee": _r(fct.loc[fct["discharges_imputed"] & (fct["condition_code"] == "HIP_KNEE"), "discharges_est"].sum()
                                         / fct.loc[fct["has_err"] & (fct["condition_code"] == "HIP_KNEE"), "discharges_est"].sum()),
            "dq_checks": dq_all["status"].value_counts().to_dict(),
        },
        "national": {
            "hospitals_penalized": n_pen,
            "share_penalized_of_scored": _r(n_pen / int((elig["n_conditions_with_err"] > 0).sum())),
            "total_penalty": _r(ph["penalty_est_annual"].sum(), 0),
            "mean_penalty_penalized": _r(pen_h["penalty_est_annual"].mean(), 0),
            "median_penalty_penalized": _r(pen_h["penalty_est_annual"].median(), 0),
            "median_reduction_pct_penalized": _r(pen_h["payment_reduction_pct"].median(), 5),
            "mean_reduction_pct_penalized": _r(pen_h["payment_reduction_pct"].mean(), 5),
            "hospitals_at_cap": int(ph["hits_cap"].sum()),
            "top10_share_of_penalty": _r(drivers.top_share(curve, 0.10)),
            "top20_share_of_penalty": _r(drivers.top_share(curve, 0.20)),
            "excess_readmissions_per_year": _r(nat_seg["excess_readmissions_annual_pos"], 0),
            "eligible_discharges_per_year": _r(nat_seg["discharges_annual"], 0),
            "mean_err": _r(nat_seg["mean_err"]),
            "conditions": {c: {k_: _r(v) for k_, v in row.items()} for c, row in cond.iterrows()},
            "hf_pn_share_excess_readmissions": _r(cond.loc[["HF", "PN"], "share_excess_readmissions"].sum()),
            "hf_pn_share_penalty": _r(cond.loc[["HF", "PN"], "share_penalty"].sum()),
            "surgical_share_penalty": _r(cond.loc[["CABG", "HIP_KNEE"], "share_penalty"].sum()),
            "surgical_share_discharges": _r(cond.loc[["CABG", "HIP_KNEE"], "share_discharges"].sum()),
            "segments": by_dim,
            "top_states_by_mean_err": [{"state": r.segment_value, "mean_err": _r(r.mean_err), "n_hospitals": int(r.n_hospitals),
                                        "share_penalized": _r(r.share_hospitals_penalized)} for r in states.head(5).itertuples()],
            "bottom_states_by_mean_err": [{"state": r.segment_value, "mean_err": _r(r.mean_err), "n_hospitals": int(r.n_hospitals)}
                                          for r in states.tail(5).itertuples()],
            "regression": {"info": reg_info, "coefficients": coefs.round(4).to_dict(orient="records")},
            "penalty_sensitivity": pen_sens.round(0).to_dict(orient="records"),
        },
        "shrinkage": {r.condition_code: {"k": _r(r.k, 1), "pass_through_at_100": _r(r.pass_through_at_100, 3),
                                         "pass_through_at_500": _r(r.pass_through_at_500, 3),
                                         "pass_through_at_1500": _r(r.pass_through_at_1500, 3),
                                         "r_squared": _r(r.r_squared, 3)} for r in k.itertuples()},
        "client": {
            "name": client.client_config()["name"], "facility_ids": ids, "target_hospital": target,
            "target_hospital_name": names[target],
            "total_penalty": _r(client_h["penalty_est_annual"].sum(), 0),
            "hospitals_penalized": int(client_h["is_penalized"].sum()),
            "hospitals": [{"facility_id": r.facility_id, "name": r.facility_name, "size_band": r.size_band,
                           "penalty": _r(r.penalty_est_annual, 0), "reduction_pct": _r(r.payment_reduction_pct, 5),
                           "readmission_index": _r(r.readmission_index)} for r in client_h.itertuples()],
            "penalty_by_condition": client_pen.groupby("condition_code")["penalty_contribution_annual"].sum().round(0).to_dict(),
            "top2_share": _r(client_h["penalty_est_annual"].head(2).sum() / client_h["penalty_est_annual"].sum()),
            "pilot_hospitals": pilot, "pilot_hospital_names": [names[x] for x in pilot],
            "target_penalty_by_condition": client_pen[client_pen["facility_id"] == target]
                .set_index("condition_code")["penalty_contribution_annual"].round(0).to_dict(),
            "peer_percentiles": client_peer_grid(hc, dim, ph),
            "benchmark_target": {c: {"err": _r(r.target_err), "peer_median": _r(r.peer_median), "percentile": _r(r.percentile_vs_peers, 1),
                                     "n_peers": int(r.n_peers), "status": r.status,
                                     "readmissions_vs_peer_median": _r(r.readmissions_vs_peer_median, 1)}
                                 for c, r in bt.iterrows()},
            "peer_summary_target": {k_: _r(v) for k_, v in peer_sum.items()},
        },
        "business_case": {
            "scenarios": {k_: {kk: _r(vv, 2) if not isinstance(vv, str) else vv for kk, vv in row.items()}
                          for k_, row in sc.to_dict(orient="index").items()},
            "break_even": {k_: _r(v) for k_, v in be.items()},
            "pilot_unit_economics": pilot_unit_economics(m_pilot, p_tgt),
            "pilot_power": pilot_power(m_pilot, p_tgt, be["pilot_relative_reduction"]),
            "monte_carlo": {"runs": int(len(mc)), "seed": seed,
                            "p_hospital_net_positive": _r((mc["hospital_net"] > 0).mean(), 3),
                            "p_combined_net_positive": _r((mc["combined_net"] > 0).mean(), 3),
                            "hospital_net_p5": _r(mc["hospital_net"].quantile(0.05), 0),
                            "hospital_net_p50": _r(mc["hospital_net"].quantile(0.50), 0),
                            "hospital_net_p95": _r(mc["hospital_net"].quantile(0.95), 0)},
            "sensitivity_pilot": {"any_hospital_sign_flip": bool(sens["hospital_sign_flips"].any()),
                                  "any_combined_sign_flip": bool(sens["combined_sign_flips"].any()),
                                  "hospital_flips": sens.loc[sens["hospital_sign_flips"], ["label", "change"]].to_dict(orient="records")},
            "sensitivity_broad": {"any_hospital_sign_flip": bool(sens_broad["hospital_sign_flips"].any()),
                                  "any_combined_sign_flip": bool(sens_broad["combined_sign_flips"].any())},
            "national": nat,
            "params_broad": p_broad.to_dict(), "params_targeted": p_tgt.to_dict(),
        },
        "known_numbers": cfg["known_numbers"],
    }
    metrics["validation"] = validation_metrics()
    METRICS_PATH.parent.mkdir(parents=True, exist_ok=True)
    METRICS_PATH.write_text(json.dumps(metrics, indent=2, default=lambda o: _r(o) if not isinstance(o, (list, dict)) else o))
    return metrics


def validation_metrics() -> dict | None:
    """Summary of the optional CMS check (reports/tables/cms_validation_*.csv), if it has been run."""
    tdir = ROOT / "reports" / "tables"
    path = tdir / "cms_validation_summary.csv"
    if not path.exists():
        return None
    v = pd.read_csv(path).set_index("metric")
    imp = pd.read_csv(tdir / "cms_validation_imputation.csv").set_index("condition_code")
    peers = pd.read_csv(tdir / "cms_validation_peer_groups.csv")
    cl = pd.read_csv(tdir / "cms_validation_client.csv", dtype={"facility_id": str})
    pers_path = tdir / "cms_validation_persistence.csv"
    pers = pd.read_csv(pers_path).set_index("metric")["value"].to_dict() if pers_path.exists() else {}
    pw_path = tdir / "cms_payment_weights.csv"
    pw = pd.read_csv(pw_path).round(3).to_dict(orient="records") if pw_path.exists() else []
    return {
        "persistence": {k: _r(v, 4) for k, v in pers.items()},
        "payment_weights": pw,
        "agreement": _r(v.loc["classification_agreement", "ours"]),
        "confusion": v.loc["classification_agreement", "note"],
        "hospitals_compared": int(v.loc["hospitals_in_both_files", "ours"]),
        "ours_penalized": int(v.loc["hospitals_penalized", "ours"]),
        "cms_penalized": int(v.loc["hospitals_penalized", "cms"]),
        "r_pearson": _r(v.loc["reduction_pct_correlation_pearson", "ours"], 3),
        "r_spearman": _r(v.loc["reduction_pct_correlation_spearman", "ours"], 3),
        "mean_reduction_ours": _r(v.loc["mean_reduction_pct_among_penalized", "ours"], 5),
        "mean_reduction_cms": _r(v.loc["mean_reduction_pct_among_penalized", "cms"], 5),
        "median_reduction_ours": _r(v.loc["median_reduction_pct_among_penalized", "ours"], 5),
        "median_reduction_cms": _r(v.loc["median_reduction_pct_among_penalized", "cms"], 5),
        "at_cap_ours": int(v.loc["hospitals_at_3pct_cap", "ours"]), "at_cap_cms": int(v.loc["hospitals_at_3pct_cap", "cms"]),
        "condition_flag_agreement": _r(v.loc["condition_flag_agreement", "ours"]),
        "err_max_abs_difference": _r(v.loc["err_max_abs_difference", "ours"], 6),
        "imputation_mid_vs_actual": {c: _r(r.mid_vs_actual, 3) for c, r in imp.iterrows()},
        "imputation_within_bounds": _r(imp.loc["ALL", "share_within_bounds"], 3),
        "peer_groups": peers.round(4).to_dict(orient="records"),
        "client": cl.round(5).to_dict(orient="records"),
    }


def load_metrics() -> dict:
    return json.loads(METRICS_PATH.read_text())


if __name__ == "__main__":
    m = build()
    print(json.dumps({k: m[k] for k in ("data",)}, indent=1))
