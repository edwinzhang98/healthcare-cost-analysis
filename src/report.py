"""Build reports/report.html: the full analysis as one standalone file.

Same chart builders (src/charts.py) and base-case settings as the Streamlit app,
plotly.js embedded once, so the file opens offline with a double-click.
"""
from __future__ import annotations

import html
from datetime import date

import pandas as pd
import plotly.offline
from jinja2 import Template

from src import analysis, benchmarking, charts, client, cost_model as cm, data, drivers, recommendations
from src.charts import CONDITION_LABELS, money, pct
from src.config import ROOT, load_config

OUT = ROOT / "reports" / "report.html"


def _fig(fig) -> str:
    return fig.to_html(full_html=False, include_plotlyjs=False,
                       config={"displaylogo": False, "responsive": True})


def _md(text: str) -> str:
    """Tiny markdown: **bold** and line breaks (findings / recommendations text)."""
    import re
    t = html.escape(text)
    t = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", t)
    return t


def _table(df: pd.DataFrame, fmt: dict | None = None, cls: str = "") -> str:
    fmt = fmt or {}
    d = df.copy()
    for c, f in fmt.items():
        if c in d.columns:
            d[c] = d[c].map(lambda v, f=f: "–" if pd.isna(v) else f(v))
    return d.to_html(index=False, classes=f"tbl {cls}", border=0, escape=True, na_rep="–")


def build() -> None:
    cfg = load_config()
    m = analysis.load_metrics()
    nat, cl, bc, dq_meta = m["national"], m["client"], m["business_case"], m["data"]
    v = m.get("validation") or {}
    fct = data.table("fct_hospital_condition")
    dim = data.table("dim_hospital")
    seg = data.table("mart_segment_summary")
    hn = dim.set_index("facility_id")["facility_name"].map(lambda s: s.title().replace(" Of ", " of ").replace(" At ", " at ")).to_dict()
    short = {k: (s if len(s) <= 34 else s[:33] + "…") for k, s in hn.items()}
    short.update(client.display_names())
    figs, tables = {}, {}

    # ---------------- data & sanity
    steps = pd.DataFrame([
        ("Hospitals in HRRP file", dq_meta["hrrp_hospitals"]),
        ("Found in Hospital General Info", dq_meta["matched_hospital_info"]),
        ("Payment-eligible (excl. Maryland)", dq_meta["payment_eligible_hospitals"]),
        ("With ≥1 scored condition", dq_meta["eligible_with_err"]),
        ("Estimated penalized", nat["hospitals_penalized"]),
    ], columns=["step", "n"])
    figs["funnel"] = _fig(charts.join_funnel(steps, "20 hospitals drop out at the join; 43 Maryland hospitals are exempt",
                                             "Hospitals at each step, HRRP file joined to Hospital General Information"))
    figs["status"] = _fig(charts.reporting_status(fct, "Hip/knee and bypass results are often hidden or unscored",
                                                  "Share of hospitals by what CMS published, per condition"))
    dq = data.table("dq_checks_all")
    tables["dq"] = _table(dq[["check_id", "status", "category", "check_name", "actual", "detail"]]
                          .rename(columns={"check_id": "ID", "status": "Status", "category": "Category",
                                           "check_name": "Check", "actual": "Result", "detail": "Note"}), cls="dq")
    dq_counts = dq["status"].value_counts().to_dict()
    vh = ROOT / "data" / "processed" / "cms_validation_hospital.parquet"
    if v and vh.exists():
        figs["validation"] = _fig(charts.validation_scatter(
            pd.read_parquet(vh), f"Our estimates track CMS's actual cuts closely (r = {v['r_pearson']:.2f})",
            "Payment cut per hospital, FY2026: our estimate vs CMS Table 15; diagonal = perfect match"))
    if v:
        thr = pd.read_csv(ROOT / "reports" / "tables" / "cms_validation_thresholds.csv")
        thr.insert(0, "Condition", thr.pop("condition_code").map(CONDITION_LABELS))
        tables["thresholds"] = _table(thr.round(4))
        imp = pd.read_csv(ROOT / "reports" / "tables" / "cms_validation_imputation.csv")
        imp["condition_code"] = imp["condition_code"].map(lambda c: CONDITION_LABELS.get(c, "All conditions"))
        tables["imputation"] = _table(
            imp[["condition_code", "rows", "actual", "estimate_mid", "mid_vs_actual", "share_within_bounds"]]
            .rename(columns={"condition_code": "Condition", "rows": "Hidden rows", "actual": "CMS actual discharges",
                             "estimate_mid": "Our estimate", "mid_vs_actual": "Estimate / actual",
                             "share_within_bounds": "Actual inside our range"}),
            {"CMS actual discharges": lambda x: f"{x:,.0f}", "Our estimate": lambda x: f"{x:,.0f}",
             "Estimate / actual": lambda x: f"{x:.2f}", "Actual inside our range": lambda x: f"{x:.0%}",
             "Hidden rows": lambda x: f"{x:,.0f}"})
        pw = pd.read_csv(ROOT / "reports" / "tables" / "cms_payment_weights.csv")
        pw.insert(0, "Condition", pw.pop("condition_code").map(CONDITION_LABELS))
        tables["payment_weights"] = _table(pw.rename(columns={
            "cms_median_rel_to_hf": "CMS median (vs heart failure)", "cms_p25": "25th pct", "cms_p75": "75th pct",
            "hospitals": "Hospitals", "seed_rel_to_hf": "Used in model", "drg_only_rel_to_hf": "DRG weights only"}))
    k = data.table("shrinkage_k")
    figs["shrink"] = _fig(charts.shrinkage_curves(
        data.table("shrinkage_bins"), k,
        "At small hospitals, only a fraction of a real change in readmissions reaches the CMS score",
        "Share of the actual (observed − expected) readmission gap that shows up in the published score, by volume; "
        "dots = measured in volume bands, lines = fitted n / (n + k)"))

    # ---------------- national picture
    states = seg[(seg["segment_dimension"] == "State") & (seg["condition_code"] == "ALL")].rename(columns={"segment_value": "state"})
    states = states.assign(hospitals=states["n_hospitals"].map("{:,}".format))
    top3 = ", ".join(f"{s['state']} ({s['mean_err']:.3f})" for s in nat["top_states_by_mean_err"][:3])
    figs["map"] = _fig(charts.state_tile_map(
        states, "mean_err", f"Highest average ERR: {top3}",
        "Average excess readmission ratio by state, payment-eligible hospitals, FY2026 program. Maryland is exempt.",
        "Average ERR", diverging_mid=1.0, fmt=".3f", hover_cols={"hospitals": "Hospitals"}))
    mix = drivers.condition_mix(seg)
    figs["mix"] = _fig(charts.condition_mix(
        mix, f"Heart failure and pneumonia drive {pct(nat['hf_pn_share_excess_readmissions'])} of excess readmissions; "
             f"surgery drives {pct(nat['surgical_share_penalty'])} of penalty dollars",
        "Share of national total by condition: eligible discharges, excess readmissions, estimated penalty $"))
    cs = data.table("condition_summary")
    tables["per_readmission"] = _table(
        cs.assign(Condition=cs["condition_code"].map(CONDITION_LABELS))[
            ["Condition", "payment_per_discharge", "expected_rate_pct", "penalty_per_excess_readmission",
             "share_discharges", "share_excess_readmissions", "share_penalty"]]
        .sort_values("penalty_per_excess_readmission", ascending=False)
        .rename(columns={"payment_per_discharge": "Medicare payment per case", "expected_rate_pct": "Typical readmission rate",
                         "penalty_per_excess_readmission": "Penalty per readmission above threshold",
                         "share_discharges": "Share of discharges", "share_excess_readmissions": "Share of excess readmissions",
                         "share_penalty": "Share of penalty $"}),
        {"Medicare payment per case": lambda x: f"${x:,.0f}", "Typical readmission rate": lambda x: f"{x:.1f}%",
         "Penalty per readmission above threshold": lambda x: f"${x:,.0f}", "Share of discharges": lambda x: f"{x:.0%}",
         "Share of excess readmissions": lambda x: f"{x:.0%}", "Share of penalty $": lambda x: f"{x:.0%}"})
    orders = {"Volume": ["Low volume", "Mid volume", "High volume"], "Census region": ["Northeast", "Midwest", "South", "West"],
              "Ownership": ["Non-profit", "For-profit", "Government"],
              "Star rating": ["1 star", "2 star", "3 star", "4 star", "5 star", "Not rated"]}
    nat_err = nat["mean_err"]
    for dim_name in ["Ownership", "Census region", "Volume", "Star rating"]:
        st = drivers.segment_table(seg, dim_name)
        hi, lo = st.sort_values("mean_err").iloc[-1], st.sort_values("mean_err").iloc[0]
        figs[f"seg_{dim_name}"] = _fig(charts.segment_dots(
            st, f"{hi['segment_value']} hospitals average ERR {hi['mean_err']:.3f} vs {lo['mean_err']:.3f} for {lo['segment_value']}",
            "Average ERR with 95% interval, all six conditions; hollow marker = fewer than 30 results",
            reference=nat_err, order=orders.get(dim_name)))
    figs["conc"] = _fig(charts.concentration(
        data.table("concentration_curve"), f"The top 10% of hospitals carry {pct(nat['top10_share_of_penalty'])} of penalty dollars",
        "Cumulative share of estimated penalty $, hospitals ranked from highest to lowest penalty"))
    coefs = data.table("regression_coefs")
    info = nat["regression"]["info"]
    figs["coef"] = _fig(charts.coefficient_plot(
        coefs, "Ownership and region stay associated with ERR after adjusting for the others",
        f"Adjusted difference in ERR points; one model with all factors plus condition; {info['n_rows']:,} results from "
        f"{info['n_hospitals']:,} hospitals; hollow = not significant; R² = {info['r_squared']:.3f}"))

    # ---------------- benchmarking (target hospital)
    hc = data.hospital_conditions()
    target = client.target_hospital_id()
    bench = data.table("benchmark_target")
    peers = benchmarking.peer_ids(dim, target)
    tname = short[target]
    worst = bench[bench["has_err"]].sort_values("percentile_vs_peers", ascending=False).iloc[0]
    figs["bench"] = _fig(charts.benchmark_strip(
        bench, hc[hc["facility_id"].isin(peers) & hc["has_err"]], tname,
        f"{tname} is worst on {worst['condition_label'].lower()}: higher ERR than {worst['percentile_vs_peers']:.0f}% of peers",
        "ERR by condition: gray = peer hospitals (same ownership and HRRP volume), blue diamond = this hospital, red "
        "tick = national penalty threshold; right is worse"))
    tables["bench"] = _table(
        bench.assign(Condition=bench["condition_code"].map(CONDITION_LABELS))[
            ["Condition", "status", "target_err", "peer_median", "percentile_vs_peers", "national_threshold",
             "readmissions_vs_peer_median", "n_peers"]]
        .rename(columns={"status": "Status", "target_err": "ERR", "peer_median": "Peer median",
                         "percentile_vs_peers": "Higher than % of peers", "national_threshold": "Threshold",
                         "readmissions_vs_peer_median": "Readmissions/yr vs peer median", "n_peers": "Peers"}),
        {"ERR": lambda x: f"{x:.3f}", "Peer median": lambda x: f"{x:.3f}", "Higher than % of peers": lambda x: f"{x:.0f}%",
         "Threshold": lambda x: f"{x:.3f}", "Readmissions/yr vs peer median": lambda x: f"{x:+.1f}"})
    grid = pd.DataFrame(cl["peer_percentiles"])
    grid["Hospital"] = grid["facility_id"].map(short)
    tables["peer_grid"] = _table(
        grid[["Hospital", "index", "index_percentile", "HF", "PN", "COPD", "AMI", "CABG", "HIP_KNEE"]]
        .rename(columns={"index": "Readmission index", "index_percentile": "Index percentile",
                         **{c: CONDITION_LABELS[c] for c in ["HF", "PN", "COPD", "AMI", "CABG", "HIP_KNEE"]}}),
        {"Readmission index": lambda x: f"{x:.3f}", **{c: (lambda x: f"{x:.0f}") for c in
         ["Index percentile"] + [CONDITION_LABELS[c] for c in ["HF", "PN", "COPD", "AMI", "CABG", "HIP_KNEE"]]}})

    # ---------------- penalty exposure (client)
    pc = data.table("mart_penalty_condition")
    cpc = pc[pc["facility_id"].isin(cl["facility_ids"])].rename(columns={"penalty_contribution_annual": "penalty"})
    figs["pen_client"] = _fig(charts.penalty_by_hospital(
        cpc, short, f"Two hospitals carry {pct(cl['top2_share'])} of the group's estimated penalty",
        "Estimated HRRP penalty per year by hospital and condition, US$ (FY2026 program, illustrative 8-hospital NJ group)"))
    thr_rows = fct[fct["facility_id"].isin(cl["facility_ids"]) & fct["has_err"]].rename(
        columns={"penalty_threshold_err": "threshold"})
    figs["heat"] = _fig(charts.threshold_heatmap(
        thr_rows, short, "Red cells are the conditions being penalized; the number is the gap above the threshold",
        "ERR minus penalty threshold by hospital and condition (blue = below threshold, no penalty; blank = too few cases)"))
    pers = (v.get("persistence") or {})
    ppath = ROOT / "data" / "processed" / "cms_persistence_hospital.parquet"
    if pers and ppath.exists():
        figs["persist"] = _fig(charts.persistence_scatter(
            pd.read_parquet(ppath), pers["slope_fy2027_on_fy2026"],
            "Penalties drift back toward the average: big FY2026 cuts shrank in FY2027, small ones grew",
            "CMS actual payment cut by hospital, FY2026 vs FY2027 (Table 15). Red line: FY2027 cut ≈ 0.58 × FY2026 cut + 0.16 points"))
    ps = pd.DataFrame(nat["penalty_sensitivity"])
    tables["pen_sens"] = _table(ps.rename(columns={"scenario": "Assumption", "n_hospitals_penalized": "Hospitals penalized",
                                                   "total_penalty": "National penalty $/yr", "client_penalty": "Client group $/yr"}),
                                {"Hospitals penalized": lambda x: f"{x:,.0f}", "National penalty $/yr": lambda x: money(x),
                                 "Client group $/yr": lambda x: money(x)})

    # ---------------- business case (pilot, base case)
    pilot_ids = cl["pilot_hospitals"]
    m_pilot = analysis.model_inputs(pilot_ids)
    p_tgt = analysis.program_params("targeted")
    res = cm.evaluate(m_pilot, p_tgt)
    tt = res["totals"]
    ph_df = data.table("bc_phase_in")
    ph_p = ph_df[ph_df["scenario"] == "targeted_pilot"]
    figs["waterfall"] = _fig(charts.waterfall(
        tt, 0.0, f"Each $1 of pilot cost returns ${tt['benefit_cost_ratio']:.2f} to the hospital",
        f"Pilot at {' and '.join(short[x] for x in pilot_ids)}: hospital view, US$ per year at steady state"))
    figs["phase"] = _fig(charts.phase_in_chart(
        ph_p, 0.0, "Penalty relief arrives two years after the program starts",
        "Pilot, hospital view by fiscal year; program starts Jan 2027 at half strength for 12 months; CMS scores a "
        "2-year window that ends 15 months before each fiscal year"))
    tor = data.table("bc_tornado")
    figs["tornado"] = _fig(charts.tornado_chart(
        tor, tt["hospital_net"], "Effect size, MA share and payment level move the answer most",
        "Pilot hospital net per year when one input moves 30% down (orange) or up (blue); red line = break-even"))
    g = data.table("bc_grid")
    be = bc["break_even"]
    figs["grid"] = _fig(charts.breakeven_heatmap(
        g, "relative_reduction", "cost_per_enrollee", "hospital_net", (p_tgt.relative_reduction, p_tgt.cost_per_enrollee),
        f"Break-even needs about a {pct(be['pilot_relative_reduction'])} readmission reduction at $400 per patient",
        "Pilot hospital net per year for combinations of effect size and cost per patient; black line = break-even",
        "Readmission reduction among enrolled (base condition)", "Cost per enrolled patient"))
    mc = data.table("bc_monte_carlo")
    figs["mc"] = _fig(charts.monte_carlo_hist(
        mc, "hospital_net", f"The pilot pays off for the hospital in {pct((mc['hospital_net'] > 0).mean())} of runs "
                            f"(whole system: {pct((mc['combined_net'] > 0).mean())})",
        f"Pilot hospital net per year across {len(mc):,} simulation runs (fixed seed {cfg['random_seed']}), US$"))
    sc = pd.DataFrame(bc["scenarios"]).T.reset_index(drop=True)
    tables["scenarios"] = _table(
        sc[["label", "program_cost", "penalty_today", "penalty_before", "avoided_penalty", "readmissions_avoided",
            "hospital_net", "combined_net", "benefit_cost_ratio"]]
        .rename(columns={"label": "Scenario", "program_cost": "Cost/yr", "penalty_today": "FY2026 penalty (est.)",
                         "penalty_before": "Expected penalty without program", "avoided_penalty": "Penalty avoided/yr",
                         "readmissions_avoided": "Readmissions avoided/yr", "hospital_net": "Hospital net/yr",
                         "combined_net": "Whole-system net/yr", "benefit_cost_ratio": "Return per $1"}),
        {"Cost/yr": money, "FY2026 penalty (est.)": money, "Expected penalty without program": money,
         "Penalty avoided/yr": money, "Readmissions avoided/yr": lambda x: f"{x:.1f}", "Hospital net/yr": money,
         "Whole-system net/yr": money, "Return per $1": lambda x: f"${x:.2f}"})
    sens = data.table("bc_sensitivity")
    sv = sens.pivot_table(index="label", columns="change", values=["hospital_net", "combined_net"])
    sv.columns = [f"{'Hospital' if a == 'hospital_net' else 'Whole system'} {b}" for a, b in sv.columns]
    sv["Hospital result flips?"] = sens.groupby("label")["hospital_sign_flips"].any().map({True: "yes", False: "no"})
    sv["System result flips?"] = sens.groupby("label")["combined_sign_flips"].any().map({True: "yes", False: "no"})
    tables["sens"] = _table(sv.reset_index().rename(columns={"label": "Input (±30%)"}),
                            {c: money for c in sv.columns if c.endswith("%")})
    params = p_tgt.to_dict()
    assumptions = [
        ("Patients enrolled", f"{params['reach']:.0%} of eligible Medicare patients in targeted conditions (highest-risk first)"),
        ("Risk of enrolled patients", f"{params['risk_multiplier']:.1f}× the condition average (HOSPITAL score validation)"),
        ("Readmission reduction among enrolled", f"{params['relative_reduction']:.0%} base; ×1.2 heart failure, ×0.5 COPD, ×0.3 surgery (Cochrane 2022, Leppin 2014, PACT-HF 2019)"),
        ("Cost per enrolled patient", f"${params['cost_per_enrollee']:,.0f} (2024 $; Nuckols 2017, CTI, CCTP anchors)"),
        ("Fixed cost per hospital", f"${params['fixed_cost_per_hospital']:,.0f}/yr (program oversight and reporting)"),
        ("Medicare Advantage share", f"{params['ma_share']:.0%} (New Jersey 2025); counts in the score from FY2027, not in the penalty base"),
        ("Persistence of today's excess", f"{params['persistence']:.0%} (regression to the mean; CMS FY2026→FY2027 slope 0.58)"),
        ("Cost of a readmission", f"${params['cost_per_readmission']:,.0f} (2025 $; between HCUP's Medicare readmission costs by condition, "
                                  "$16K–$19K, and its all-condition 2020 average, about $21K)"),
        ("Money per avoided readmission", f"payers save ${p_tgt.payment_per_readmission:,.0f}; hospital loses ${p_tgt.lost_margin_per_readmission:,.0f} of margin; system saves ${p_tgt.variable_cost_per_readmission:,.0f} (MedPAC)"),
        ("Program start / horizon", f"{cfg['intervention']['program_start']}, half strength in year 1; FY2027–FY2032; 7% discount rate"),
    ]
    tables["assumptions"] = _table(pd.DataFrame(assumptions, columns=["Assumption", "Base case and source"]))

    scn = bc["scenarios"]
    opts = pd.DataFrame([
        {"option": "Broad program, all 8 hospitals", **scn["broad_all"]},
        {"option": "Targeted program, all 8 hospitals", **scn["targeted_all"]},
        {"option": "Pilot at the 2 best-placed hospitals", **scn["targeted_pilot"]},
        {"option": "Pilot + 30% of payer savings shared back", **scn["targeted_pilot_risk30"]},
    ])
    figs["options"] = _fig(charts.options_chart(
        opts, "Only the pilot with payer co-funding breaks even for the hospital",
        "Net value per year once the program is at full strength (FY2032+), base-case assumptions; blue = hospital P&L, "
        "aqua = payers and hospital together"))

    recs = recommendations.build(m)
    finds = recommendations.findings(m)
    tpl = Template(TEMPLATE)
    out = tpl.render(
        today=date.today().isoformat(), m=m, nat=nat, cl=cl, bc=bc, v=v, figs=figs, tables=tables, recs=recs,
        finds=[_md(f) for f in finds], md=_md, money=money, pct=pct, dq_counts=dq_counts, pers=pers,
        pilot=bc["scenarios"]["targeted_pilot"], broad=bc["scenarios"]["broad_all"], be=be, tt=tt,
        pilot_names=" and ".join(hn[x] for x in pilot_ids), target_name=hn[target], k=k.set_index("condition_code"),
        plotly_js=plotly.offline.get_plotlyjs(), info=info, kn=m["known_numbers"])
    OUT.write_text(out, encoding="utf-8")
    print(f"    wrote {OUT.relative_to(ROOT)} ({OUT.stat().st_size / 1e6:.1f} MB)")


TEMPLATE = r"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>HRRP Readmission Penalties: Analysis Report</title>
<style>
:root{--ink:#0b0b0b;--ink2:#52514e;--muted:#898781;--line:#e1e0d9;--bg:#fcfcfb;--panel:#f3f2ee;--blue:#2a78d6}
*{box-sizing:border-box} body{margin:0;background:var(--bg);color:var(--ink);font:15px/1.55 system-ui,-apple-system,"Segoe UI",Roboto,Helvetica,Arial,sans-serif}
.wrap{max-width:1080px;margin:0 auto;padding:32px 20px 80px}
h1{font-size:28px;line-height:1.25;margin:0 0 6px} h2{font-size:21px;margin:44px 0 10px;padding-top:10px;border-top:1px solid var(--line)}
h3{font-size:16px;margin:26px 0 6px} p{margin:8px 0} .sub{color:var(--ink2);margin-bottom:18px}
.note{color:var(--ink2);font-size:13.5px} .box{background:var(--panel);border-left:3px solid var(--blue);padding:12px 16px;border-radius:0 6px 6px 0;margin:14px 0}
.kpis{display:grid;grid-template-columns:repeat(auto-fit,minmax(200px,1fr));gap:10px;margin:16px 0}
.kpi{border:1px solid rgba(11,11,11,.1);border-radius:6px;padding:10px 12px;background:#fff}
.kpi .l{font-size:12.5px;color:var(--ink2)} .kpi .v{font-size:24px;font-weight:620} .kpi .s{font-size:12px;color:var(--muted)}
.tbl{border-collapse:collapse;width:100%;font-size:13px;margin:10px 0 4px;font-variant-numeric:tabular-nums}
.tbl th{text-align:left;border-bottom:1px solid #c3c2b7;padding:6px 8px;color:var(--ink2);font-weight:600}
.tbl td{border-bottom:1px solid var(--line);padding:6px 8px;vertical-align:top}
.toc{columns:2;font-size:14px;background:var(--panel);padding:12px 18px;border-radius:6px} .toc a{color:var(--ink);text-decoration:none}
.chart{margin:10px 0 2px} details{margin:8px 0} summary{cursor:pointer;color:var(--ink2);font-weight:600}
.rec{border:1px solid rgba(11,11,11,.1);border-radius:6px;padding:12px 14px;margin:10px 0;background:#fff}
.rec .t{font-weight:640;margin-bottom:6px} .rec .g{display:grid;grid-template-columns:1fr 1fr;gap:6px 18px;font-size:13.5px}
@media (max-width:720px){.toc{columns:1}.rec .g{grid-template-columns:1fr}}
code{background:var(--panel);padding:1px 4px;border-radius:3px;font-size:13px}
</style>
<script>{{ plotly_js }}</script>
</head><body><div class="wrap">
<h1>Hospital readmission penalties: where they come from and what a follow-up program can recover</h1>
<div class="sub">CMS Hospital Readmissions Reduction Program (HRRP), FY2026 program data (performance period Jul 2021–Jun 2024) ·
{{ m.data.hrrp_hospitals | string }} hospitals · report generated {{ today }}. Penalty dollars are estimates; the client group is an
illustrative set of 8 New Jersey hospitals, not an actual health system.</div>

<div class="toc"><a href="#summary">1. Summary</a><br><a href="#question">2. The question</a><br><a href="#data">3. Data & sanity checks</a><br>
<a href="#national">4. National picture</a><br><a href="#bench">5. Benchmarking</a><br><a href="#penalty">6. Penalty exposure</a><br>
<a href="#business">7. Business case</a><br><a href="#recs">8. Recommendations</a><br><a href="#limits">9. Limitations & next steps</a><br>
<a href="#methods">Appendix: methods</a></div>

<h2 id="summary">1. Summary</h2>
<div class="box"><strong>Decision.</strong> The VP of Quality (with the CFO) must decide before the next budget cycle whether to fund a
post-discharge follow-up program, and where. <strong>Answer in one line:</strong> a follow-up program will not pay for itself through avoided
penalties. A group-wide version would return about ${{ "%.2f"|format(broad.benefit_cost_ratio) }} per $1. If the group wants to act on readmissions,
start with a measured pilot at {{ pilot_names }} and ask payers to share savings.</div>
<div class="kpis">
<div class="kpi"><div class="l">Hospitals penalized nationally (our estimate)</div><div class="v">{{ "{:,}".format(nat.hospitals_penalized) }}</div><div class="s">CMS actual {{ "{:,}".format(kn.fy2026_hospitals_penalized) }}</div></div>
<div class="kpi"><div class="l">Group's estimated penalty (FY2026)</div><div class="v">{{ money(cl.total_penalty) }}/yr</div><div class="s">{{ cl.hospitals_penalized }} of 8 hospitals penalized</div></div>
<div class="kpi"><div class="l">Group-wide program</div><div class="v">{{ money(broad.hospital_net) }}/yr</div><div class="s">hospital net; costs {{ money(broad.program_cost) }}</div></div>
<div class="kpi"><div class="l">Best-placed pilot</div><div class="v">${{ "%.2f"|format(pilot.benefit_cost_ratio) }} per $1</div><div class="s">break-even needs ≥{{ pct(be.pilot_relative_reduction) }} fewer readmissions</div></div>
</div>
<h3>Three findings</h3>
<ol>{% for f in finds %}<li><p>{{ f }}</p></li>{% endfor %}</ol>

<h2 id="question">2. The question</h2>
<p>The VP of Quality asked: <em>"Several of our hospitals are about to be hit with CMS readmission penalties again. Which hospitals and conditions are
dragging us down? Where do we fall short compared with similar hospitals? If we invest in a post-discharge follow-up program, how much could we recover?"</em></p>
<p>We turned that into five questions the data can answer: (1) where excess readmissions and penalty dollars concentrate nationally; (2) how each of our
hospitals compares with peers of the same ownership and Medicare volume, condition by condition; (3) how much each hospital loses per year and why;
(4) whether a follow-up program pays back, when, and under which assumptions; (5) who should do what next. Hospital-level public data cannot
explain <em>why</em> a hospital readmits more, so differences between groups are reported as associations, not causes.</p>

<h2 id="data">3. Data & sanity checks</h2>
<p>Three CMS Care Compare files, joined on the CMS Certification Number: the HRRP file (18,330 rows = 3,055 hospitals × 6 conditions), Medicare
Spending per Beneficiary (calendar 2024) and Hospital General Information. {{ dq_counts.get('PASS', 0) }} automated checks pass,
{{ dq_counts.get('WARN', 0) }} are documented limitations, {{ dq_counts.get('FAIL', 0) }} fail.</p>
<div class="chart">{{ figs.funnel }}</div>
<div class="chart">{{ figs.status }}</div>
<p>CMS hides counts between 1 and 10. When readmissions are hidden, discharges are hidden too, although the score is still shown
({{ "{:,}".format(m.data.suppressed_count_rows) }} rows). We estimate those discharges at the middle of the range the score allows. That affects
{{ pct(m.data.imputed_share_of_discharges) }} of eligible discharges overall but {{ pct(m.data.imputed_share_hip_knee) }} for hip/knee.</p>
<details><summary>All automated checks</summary>{{ tables.dq }}</details>
{% if v %}
<h3>Validation against CMS's actual FY2026 penalties</h3>
<p>CMS publishes each hospital's actual payment cut (Table 15) and a supplemental file with peer groups, payment shares and the hidden counts. We used
these only to test the method. We classify <strong>{{ pct(v.agreement, 1) }}</strong> of hospitals the same way as CMS (penalized: ours
{{ "{:,}".format(v.ours_penalized) }} vs CMS {{ "{:,}".format(v.cms_penalized) }}), and our estimated cut correlates <strong>r = {{ "%.2f"|format(v.r_pearson) }}</strong>
with CMS's actual cut (average among penalized hospitals: ours {{ pct(v.mean_reduction_ours, 2) }} vs CMS {{ pct(v.mean_reduction_cms, 2) }}).
The relative payment per case by condition comes from the same CMS release (table below), so the cut correlation partly reflects that calibration.
The penalized/not-penalized agreement does not depend on payments at all.</p>
{% if figs.validation %}<div class="chart">{{ figs.validation }}</div>{% endif %}
<details><summary>Hidden discharge counts: our estimate vs CMS's actual counts</summary>{{ tables.imputation }}
<p class="note">The midpoint rule is close for most conditions but overstates hip/knee by about a third, where readmissions are rare and the allowed range is wide.</p></details>
<details><summary>Penalty thresholds: CMS peer groups vs the national median we use</summary>{{ tables.thresholds }}
<p class="note">CMS compares each hospital with peers serving a similar share of dual-eligible (low-income) patients. Peer group 5 has higher
thresholds, so a single national threshold overstates penalties at safety-net hospitals.</p></details>
<details><summary>Relative payment per case by condition</summary>{{ tables.payment_weights }}
<p class="note">Base payment for heart failure = FY2026 standardized amount ($6,752.61) × FY2026 heart-failure DRG weights = $8,523. Other conditions are scaled by CMS's
median within-hospital payment ratio. Using DRG weights alone would overweight surgery and underweight heart attack and pneumonia, whose cohorts include
PCI and sepsis cases.</p></details>
{% endif %}
<h3>CMS's scoring gives small hospitals only partial credit</h3>
<div class="chart">{{ figs.shrink }}</div>
<p>For heart failure, a hospital with 100 eligible discharges over three years sees only {{ pct(k.loc['HF','pass_through_at_100']) }} of a real
improvement in its score; at 1,500 discharges it sees {{ pct(k.loc['HF','pass_through_at_1500']) }}. The business case uses this measured pass-through.</p>

<h2 id="national">4. National picture</h2>
<div class="chart">{{ figs.map }}</div>
<div class="chart">{{ figs.mix }}</div>
<p>CMS's formula charges roughly <em>(payment per case ÷ expected readmission rate)</em> for each readmission above the threshold. That is why surgery
is expensive per patient:</p>{{ tables.per_readmission }}
<div class="chart">{{ figs['seg_Ownership'] }}</div>
<div class="chart">{{ figs['seg_Census region'] }}</div>
<div class="chart">{{ figs['seg_Volume'] }}</div>
<p class="note">Low-volume hospitals look closest to average partly because CMS shrinks their scores toward 1.00 (section 3).</p>
<div class="chart">{{ figs['seg_Star rating'] }}</div>
<p class="note">Read with care: the overall star rating includes readmission measures, so it tracks ERR partly by construction (circular). The same
applies to the spending index, which counts readmission costs.</p>
<div class="chart">{{ figs.conc }}</div>
<div class="chart">{{ figs.coef }}</div>
<p class="note">The model explains little of the variation (R² = {{ "%.3f"|format(info.r_squared) }}): most differences are between hospitals within the
same group. Coefficients are associations, not causes.</p>

<h2 id="bench">5. Benchmarking: {{ target_name }}</h2>
<p>Peers = payment-eligible hospitals with the same ownership type and Medicare HRRP volume band ({{ cl.peer_summary_target.n_peers }} hospitals).</p>
<div class="chart">{{ figs.bench }}</div>
{{ tables.bench }}
<h3>All client hospitals: percentile among peers, by condition</h3>
{{ tables.peer_grid }}
<p class="note">50 = typical peer; higher = more readmissions than peers. Peers are national, and New Jersey readmits more than average overall.</p>

<h2 id="penalty">6. Penalty exposure</h2>
<div class="chart">{{ figs.pen_client }}</div>
<div class="chart">{{ figs.heat }}</div>
<h3>How sensitive are the dollar estimates?</h3>{{ tables.pen_sens }}
{% if figs.persist %}<h3>Penalties are a moving target</h3><div class="chart">{{ figs.persist }}</div>
<p>Hospitals with the biggest FY2026 cuts saw them shrink the next year (top tenth: {{ pct(pers.top_decile_mean_cut_fy2026, 2) }} →
{{ pct(pers.top_decile_mean_cut_fy2027, 2) }}; {{ pct(pers.top_decile_share_losing_half) }} lost more than half). Part of this is the FY2027 rule change,
part is regression to the mean. The business case therefore forecasts the penalty that would remain without a program instead of assuming
today's penalty continues.</p>{% endif %}

<h2 id="business">7. Business case: post-discharge follow-up</h2>
<p>The program enrolls higher-risk heart failure and pneumonia patients for a pharmacist medication review, a nurse contact within 72 hours and a
clinic visit within 7 days. It applies the FY2027 rules: a 2-year CMS window, Medicare Advantage patients counted in the score but not in the
penalty base. There are two views. <strong>Hospital net</strong> = avoided penalty + payer savings shared back − lost fee-for-service margin
− program cost. <strong>Whole-system net</strong> = variable cost of readmissions avoided − program cost; penalty and payments are transfers
between Medicare and the hospital, so they cancel out.</p>
{{ tables.assumptions }}
<h3>Scenarios</h3>{{ tables.scenarios }}
<div class="chart">{{ figs.waterfall }}</div>
<div class="chart">{{ figs.phase }}</div>
<div class="chart">{{ figs.tornado }}</div>
<h3>±30% sensitivity: does the answer change?</h3>{{ tables.sens }}
<div class="chart">{{ figs.grid }}</div>
<div class="chart">{{ figs.mc }}</div>

<h2 id="recs">8. Recommendations</h2>
<div class="chart">{{ figs.options }}</div>
{% for r in recs %}<div class="rec"><div class="t">{{ loop.index }}. {{ md(r.what) }}</div><div class="g">
<div><strong>Owner:</strong> {{ md(r.who) }}</div><div><strong>Expected impact:</strong> {{ md(r.impact) }}</div>
<div><strong>How we measure it:</strong> {{ md(r.measure) }}</div><div><strong>Risk:</strong> {{ md(r.risk) }}</div></div></div>{% endfor %}
<p class="note">Owners are illustrative roles: the eight hospitals are an illustrative group, not an actual health system, and no existing staff or contracts are implied.</p>

<h2 id="limits">9. Limitations and next steps</h2>
<ul>
<li><strong>Hospital-level public data:</strong> shows where readmissions are high, not why; group differences are associations.</li>
<li><strong>Estimated dollars:</strong> exact payments are not public. Our national total is {{ money(nat.total_penalty) }} vs CMS's nearest published
totals of $316M–$361M. Single-hospital dollars carry roughly ±30% uncertainty (wage index, case mix).</li>
<li><strong>Thresholds:</strong> a national median replaces CMS's dual-eligible peer-group medians, which overstates penalties at safety-net hospitals.</li>
<li><strong>Rule change:</strong> FY2027 counts Medicare Advantage patients over 2 years. Our scores are from the FY2026 program; refresh when CMS posts FY2027 data (early 2027).</li>
<li><strong>Program effects</strong> come from trials and usually shrink in practice; the base case uses the conservative recent-trial estimate.</li>
<li><strong>Next:</strong> evaluate any pilot against a comparison group, not a before-and-after (regression to the mean); track readmissions monthly; plan for sepsis (FY2030).</li>
</ul>

<h2 id="methods">Appendix: methods in brief</h2>
<p><strong>ERR</strong> = predicted ÷ expected readmission rate (CMS hierarchical model). <strong>Excess readmissions</strong> = discharges ×
(predicted − expected rate). <strong>Penalty</strong>: payment cut = 0.9627 × Σ<sub>conditions</sub> (condition payments ÷ total payments) ×
max(ERR − threshold, 0), capped at 3%; dollars = cut × total base operating payments = 0.9627 × Σ condition payments × max(ERR − threshold, 0).
Condition payments = eligible discharges per year × payment per case. Total payments = HRRP-condition payments ÷ 0.133 (CMS median share), used for
the cap and percentages only. The same formula runs in SQL (<code>sql/07</code>) and Python (<code>src/penalty.py</code>); a check confirms they agree.
<strong>Shrinkage</strong>: published (predicted − expected) ≈ n/(n + k) × (observed − expected), with k fitted per condition (R² ≥ 0.99).
<strong>Business case</strong>: <code>src/cost_model.py</code>. Full metric definitions are in <code>docs/02_metric_definitions.md</code>, every
assumption with its source in <code>docs/assumptions.md</code>, and code and notebooks in the repository.</p>
</div></body></html>
"""

if __name__ == "__main__":
    build()
