"""Optional external check: compare our penalty estimate with CMS's actual FY2026
HRRP results.

Our model is built only from the three Care Compare files. CMS separately
publishes, with the IPPS final rule, (1) Table 15 (each hospital's payment
adjustment factor) and (2) a supplemental file with each hospital's peer group,
peer-group median ERRs, DRG payment ratios and *unsuppressed* discharge counts.
These are used here only to test our method, never as model inputs:
  * do we flag the same hospitals as penalized?
  * how close is our estimated payment cut to CMS's actual cut?
  * how good is our imputation of the discharge counts Care Compare hides?
  * how far is our national-median threshold from CMS's peer-group medians?

Files live in data/external/ (gitignored). Run:
    python -m src.validate_cms              # uses files if present, else skips
    python -m src.validate_cms --download   # fetch the official CMS zips first
Outputs: reports/tables/cms_validation_*.csv (aggregate results, committed) and
data/processed/cms_validation_hospital.parquet (hospital-level, for charts).
"""
from __future__ import annotations

import io
import sys
import urllib.request
import zipfile
from pathlib import Path

import numpy as np
import pandas as pd

from src import client, data
from src.config import ROOT, load_config

CONDITION_MAP = {"AMI": "AMI", "COPD": "COPD", "HF": "HF", "pneumonia": "PN", "CABG": "CABG",
                 "THA/TKA": "HIP_KNEE"}
TABLES_DIR = ROOT / "reports" / "tables"


def _cfg() -> dict:
    return load_config()["validation"]


def _path(key: str) -> Path:
    return ROOT / _cfg()["files"][key]["path"]


def download(force: bool = False) -> None:
    for key, spec in _cfg()["files"].items():
        dest = ROOT / spec["path"]
        if dest.exists() and not force:
            continue
        dest.parent.mkdir(parents=True, exist_ok=True)
        print(f"downloading {spec['url']}")
        req = urllib.request.Request(spec["url"], headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=60) as r:
            dest.write_bytes(r.read())


def available() -> bool:
    return all(_path(k).exists() for k in _cfg()["files"])


def _read_member(zpath: Path, suffix: str, contains: str = "") -> str:
    with zipfile.ZipFile(zpath) as z:
        name = next(n for n in z.namelist() if n.endswith(suffix) and contains in n)
        return z.read(name).decode("latin-1")


def load_supplemental() -> tuple[pd.DataFrame, pd.DataFrame]:
    raw = _read_member(_path("supplemental_fy2026"), ".txt", "FR FY 2026.txt")
    s = pd.read_csv(io.StringIO(raw), sep="\t", skiprows=1, dtype=str)
    s.columns = [c.strip() for c in s.columns]
    s = s[s["Hospital CCN"].str.strip().str.fullmatch(r"\d{6}", na=False)].copy()
    s["Hospital CCN"] = s["Hospital CCN"].str.strip()
    num = lambda col: pd.to_numeric(s[col], errors="coerce")
    hosp = pd.DataFrame({
        "facility_id": s["Hospital CCN"], "cms_paf": num("Payment adjustment factor"),
        "cms_dual_proportion": num("Dual proportion"),
        "cms_peer_group": pd.to_numeric(s["Peer group assignment"], errors="coerce"),
        "cms_neutrality_modifier": num("Neutrality modifier"),
    })
    hosp["cms_reduction_pct"] = 1 - hosp["cms_paf"]
    hosp["cms_penalized"] = hosp["cms_paf"] < 1
    long = []
    for k, code in CONDITION_MAP.items():
        long.append(pd.DataFrame({
            "facility_id": s["Hospital CCN"], "condition_code": code,
            "cms_discharges": num(f"Number of eligible discharges for {k}"),
            "cms_err": num(f"ERR for {k}"), "cms_peer_median": num(f"Peer group median ERR for {k}"),
            "cms_penalty_flag": s[f"Penalty indicator for {k}"].str.strip().str.upper().eq("Y"),
            "cms_drg_ratio": num(f"DRG payment ratio for {k}"),
        }))
    return hosp, pd.concat(long, ignore_index=True)


def load_table15(key: str, fy: int) -> pd.DataFrame:
    raw = _read_member(_path(key), ".txt")
    rows = [ln.split("\t") for ln in raw.splitlines()]
    rows = [r for r in rows if r and r[0].strip().isdigit() and len(r[0].strip()) == 6]
    return pd.DataFrame({"facility_id": [r[0].strip() for r in rows],
                         f"cms_paf_fy{fy}": [float(r[1]) for r in rows]})


def run() -> dict | None:
    if not available():
        print("CMS validation files not found in data/external/ - skipping "
              "(run `python -m src.validate_cms --download` to fetch them).")
        return None
    TABLES_DIR.mkdir(parents=True, exist_ok=True)
    hosp, long = load_supplemental()
    fct = data.table("fct_hospital_condition")
    ph = data.table("mart_penalty_hospital")
    dim = data.table("dim_hospital")

    # ---- hospital-level penalty agreement
    h = ph.merge(hosp, on="facility_id", how="inner")
    h["payment_reduction_pct"] = h["payment_reduction_pct"].fillna(0.0)
    conf = pd.crosstab(h["is_penalized"], h["cms_penalized"])
    tp, tn = int(conf.loc[True, True]), int(conf.loc[False, False])
    fp, fn = int(conf.loc[True, False]), int(conf.loc[False, True])
    pen_cms = h["cms_penalized"]
    summary = [
        ("hospitals_in_both_files", len(h), len(hosp), "CMS file excludes Maryland and closed hospitals"),
        ("hospitals_penalized", int(h["is_penalized"].sum()), int(pen_cms.sum()), "within hospitals in both files"),
        ("classification_agreement", (tp + tn) / len(h), 1.0, f"TP {tp}, TN {tn}, FP {fp}, FN {fn}"),
        ("reduction_pct_correlation_pearson", float(np.corrcoef(h["payment_reduction_pct"], h["cms_reduction_pct"])[0, 1]), 1.0, ""),
        ("reduction_pct_correlation_spearman", float(h[["payment_reduction_pct", "cms_reduction_pct"]].corr("spearman").iloc[0, 1]), 1.0, ""),
        ("mean_reduction_pct_among_penalized", float(h.loc[h["is_penalized"], "payment_reduction_pct"].mean()),
         float(h.loc[pen_cms, "cms_reduction_pct"].mean()), "each side's own penalized hospitals"),
        ("median_reduction_pct_among_penalized", float(h.loc[h["is_penalized"], "payment_reduction_pct"].median()),
         float(h.loc[pen_cms, "cms_reduction_pct"].median()), ""),
        ("hospitals_at_3pct_cap", int(h["hits_cap"].sum()), int((h["cms_paf"] <= 0.97).sum()), ""),
        ("neutrality_modifier", load_config()["penalty_model"]["neutrality_modifier"],
         float(hosp["cms_neutrality_modifier"].iloc[0]), ""),
        ("median_sum_drg_payment_ratios", load_config()["penalty_model"]["hrrp_payment_share"],
         float(long.groupby("facility_id")["cms_drg_ratio"].sum(min_count=1).median()), "used only for the 3% cap and %"),
    ]

    # ---- condition-level flags and ERR identity
    m = fct.merge(long, on=["facility_id", "condition_code"], how="inner")
    both = m[m["has_err"] & m["cms_err"].notna()]
    summary.append(("err_max_abs_difference", float((both["err"] - both["cms_err"]).abs().max()), 0.0,
                    "Care Compare ERR vs CMS supplemental ERR"))
    pc = data.table("mart_penalty_condition").merge(long, on=["facility_id", "condition_code"], how="inner")
    pc = pc[pc["has_err"] & pc["is_payment_eligible"]]
    summary.append(("condition_flag_agreement", float(((pc["excess_ratio_over_threshold"] > 0) == pc["cms_penalty_flag"]).mean()),
                    1.0, "hospital x condition: above threshold vs CMS penalty indicator"))
    pd.DataFrame(summary, columns=["metric", "ours", "cms", "note"]).to_csv(
        TABLES_DIR / "cms_validation_summary.csv", index=False)

    # ---- imputation of suppressed discharges
    sup = m[(m["reporting_status"] == "counts_suppressed") & m["cms_discharges"].notna()]
    imp = sup.groupby("condition_code").agg(
        rows=("cms_discharges", "size"), actual=("cms_discharges", "sum"), estimate_mid=("discharges_est", "sum"),
        estimate_low=("discharges_est_low", "sum"), estimate_high=("discharges_est_high", "sum"),
        actual_median=("cms_discharges", "median"), estimate_median=("discharges_est", "median"))
    imp["mid_vs_actual"] = imp["estimate_mid"] / imp["actual"]
    imp["share_within_bounds"] = sup.assign(
        inb=(sup["cms_discharges"] >= sup["discharges_est_low"]) & (sup["cms_discharges"] <= sup["discharges_est_high"])
    ).groupby("condition_code")["inb"].mean()
    tot = imp[["rows", "actual", "estimate_mid", "estimate_low", "estimate_high"]].sum()
    imp.loc["ALL", ["rows", "actual", "estimate_mid", "estimate_low", "estimate_high"]] = tot.values
    imp.loc["ALL", "mid_vs_actual"] = tot["estimate_mid"] / tot["actual"]
    imp.loc["ALL", "share_within_bounds"] = float(
        ((sup["cms_discharges"] >= sup["discharges_est_low"]) & (sup["cms_discharges"] <= sup["discharges_est_high"])).mean())
    imp.reset_index().to_csv(TABLES_DIR / "cms_validation_imputation.csv", index=False)

    # ---- threshold: national median vs CMS peer-group medians; flag rates by peer group
    pg = long.merge(hosp[["facility_id", "cms_peer_group"]], on="facility_id")
    med = pg.dropna(subset=["cms_peer_median"]).groupby(["condition_code", "cms_peer_group"])["cms_peer_median"].first().unstack()
    med.columns = [f"peer_group_{int(c)}" for c in med.columns]
    med["national_median_used"] = fct[fct["has_err"] & fct["is_payment_eligible"]].groupby("condition_code")["err"].median()
    med.reset_index().to_csv(TABLES_DIR / "cms_validation_thresholds.csv", index=False)
    x = pc.merge(hosp[["facility_id", "cms_peer_group"]], on="facility_id")
    rates = x.groupby("cms_peer_group").agg(
        results=("cms_penalty_flag", "size"),
        ours_share_above_threshold=("excess_ratio_over_threshold", lambda s: float((s > 0).mean())),
        cms_share_penalized=("cms_penalty_flag", "mean"))
    rates.reset_index().to_csv(TABLES_DIR / "cms_validation_peer_groups.csv", index=False)

    # ---- client group: our FY2026 estimate vs CMS actual FY2026 and FY2027 cuts
    t26 = load_table15("table15_fy2026", 2026)
    t27 = load_table15("table15_fy2027", 2027)
    cg = (dim[dim["facility_id"].isin(client.client_ids())][["facility_id", "facility_name", "size_band"]]
          .merge(ph[["facility_id", "payment_reduction_pct", "penalty_est_annual"]], on="facility_id", how="left")
          .merge(t26, on="facility_id", how="left").merge(t27, on="facility_id", how="left"))
    cg["cms_reduction_fy2026"] = 1 - cg["cms_paf_fy2026"]
    cg["cms_reduction_fy2027"] = 1 - cg["cms_paf_fy2027"]
    cg = cg.sort_values("facility_id")
    cg.rename(columns={"payment_reduction_pct": "our_estimated_reduction_fy2026"}).drop(
        columns=["cms_paf_fy2026", "cms_paf_fy2027"]).to_csv(TABLES_DIR / "cms_validation_client.csv", index=False)

    # ---- persistence: how much of a hospital's FY2026 cut is still there in FY2027 (CMS actuals)
    pers = t26.merge(t27, on="facility_id", how="inner")
    pers["cut_fy2026"], pers["cut_fy2027"] = 1 - pers["cms_paf_fy2026"], 1 - pers["cms_paf_fy2027"]
    slope = float(np.polyfit(pers["cut_fy2026"], pers["cut_fy2027"], 1)[0])
    top = pers[pers["cut_fy2026"] >= pers["cut_fy2026"].quantile(0.9)]
    pd.DataFrame([
        ("hospitals_in_both_years", len(pers)),
        ("correlation_fy2026_fy2027", float(pers[["cut_fy2026", "cut_fy2027"]].corr().iloc[0, 1])),
        ("slope_fy2027_on_fy2026", slope),
        ("top_decile_mean_cut_fy2026", float(top["cut_fy2026"].mean())),
        ("top_decile_mean_cut_fy2027", float(top["cut_fy2027"].mean())),
        ("top_decile_share_losing_half", float((top["cut_fy2027"] < 0.5 * top["cut_fy2026"]).mean())),
        ("share_penalized_fy2026", float((pers["cut_fy2026"] > 0).mean())),
        ("share_penalized_both_years", float(((pers["cut_fy2026"] > 0) & (pers["cut_fy2027"] > 0)).mean())),
    ], columns=["metric", "value"]).to_csv(TABLES_DIR / "cms_validation_persistence.csv", index=False)
    data.save_table(pers[["facility_id", "cut_fy2026", "cut_fy2027"]], "cms_persistence_hospital")

    # ---- relative payment per case by condition implied by CMS's DRG payment ratios
    #      (median within-hospital ratio vs heart failure; documents the seed values)
    L = long[(long["cms_discharges"] >= 25) & (long["cms_drg_ratio"] > 0)].copy()
    L["pay_idx"] = L["cms_drg_ratio"] / L["cms_discharges"]
    piv = L.pivot_table(index="facility_id", columns="condition_code", values="pay_idx")
    rel = piv.div(piv["HF"], axis=0)
    seed = data.condition_params()
    pd.DataFrame({
        "cms_median_rel_to_hf": rel.median(), "cms_p25": rel.quantile(0.25), "cms_p75": rel.quantile(0.75),
        "hospitals": rel.notna().sum(),
        "seed_rel_to_hf": seed["base_payment_per_discharge"] / seed.loc["HF", "base_payment_per_discharge"],
        "drg_only_rel_to_hf": seed["drg_only_payment"] / seed.loc["HF", "drg_only_payment"],
    }).round(3).reset_index().to_csv(TABLES_DIR / "cms_payment_weights.csv", index=False)

    # ---- hospital-level frame for charts (not committed)
    out = h[["facility_id", "is_penalized", "payment_reduction_pct", "cms_penalized", "cms_reduction_pct",
             "cms_peer_group", "cms_dual_proportion"]]
    data.save_table(out, "cms_validation_hospital")
    res = {r[0]: {"ours": r[1], "cms": r[2]} for r in summary}
    print(f"CMS validation: agreement {res['classification_agreement']['ours']:.1%}, "
          f"penalized ours {res['hospitals_penalized']['ours']} vs CMS {res['hospitals_penalized']['cms']}, "
          f"r = {res['reduction_pct_correlation_pearson']['ours']:.2f}")
    return res


if __name__ == "__main__":
    if "--download" in sys.argv:
        download(force="--force" in sys.argv)
    run()
