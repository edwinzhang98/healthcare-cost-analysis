import pandas as pd
import streamlit as st

from dashboard.common import (md, ROOT, chart, charts, how_to_read, kpis, metrics, page, pct, show_data, status_badge, table)

m = metrics()
d = m["data"]
v = m.get("validation")

page("Data & Sanity Checks",
     "Can we trust these numbers? What is missing from the CMS files, and how did we check the estimates?")

md("## The three CMS files")
md("""
| File | Grain | Rows | Period | Used for |
|---|---|---|---|---|
| Hospital Readmissions Reduction Program (HRRP) | hospital × 6 conditions | 18,330 (3,055 hospitals) | Jul 2021 – Jun 2024 (FY2026 program) | ERR, predicted / expected rates, discharges, readmissions |
| Medicare Spending Per Beneficiary (MSPB-1) | hospital | 4,626 | Calendar 2024 | spending index (segment only) |
| Hospital General Information | hospital | 5,419 | 2025 release | ownership, type, emergency services, star rating |
""")
st.caption("Joined on Facility ID (CMS Certification Number, read as text to keep leading zeros). "
           "Source: CMS Provider Data Catalog (Care Compare). Raw files are not stored in the repo.")

steps = pd.DataFrame([
    ("Hospitals in HRRP file", d["hrrp_hospitals"]),
    ("Found in Hospital General Info", d["matched_hospital_info"]),
    ("Payment-eligible (excl. Maryland)", d["payment_eligible_hospitals"]),
    ("With ≥1 scored condition", d["eligible_with_err"]),
    ("Estimated penalized", m["national"]["hospitals_penalized"]),
], columns=["step", "n"])
chart(charts.join_funnel(
    steps, "20 hospitals drop out at the join; 43 Maryland hospitals are exempt",
    "Hospitals at each step, HRRP file joined to Hospital General Information"), key="funnel")
chart(charts.reporting_status(
    table("fct_hospital_condition"),
    "Hip/knee and bypass results are often hidden or unscored",
    "Share of hospitals by what CMS published, per condition"), key="status")

md(
    f"""
- **20 hospitals don't match** Hospital General Information: they closed, merged, or converted to critical access
  hospitals since the performance period (4 confirmed by exact name match, e.g., Crenshaw Community Hospital is now a critical
  access hospital under a new ID). They are kept in counts but excluded from penalty estimates.
- **{d['maryland_hospitals']} Maryland hospitals** have scores but are exempt from HRRP payment cuts (state all-payer
  model). They are kept for benchmarking only.
- **Hidden counts:** when a hospital had 1–10 readmissions, CMS hides both counts but still publishes the score
  ({d['suppressed_count_rows']:,} rows). We estimate the hidden discharges at the middle of the range the score
  allows. This affects {pct(d['imputed_share_of_discharges'])} of eligible discharges overall but
  {pct(d['imputed_share_hip_knee'])} for hip/knee.
"""
)

md("## Automated checks (run on every build)")
dq = table("dq_checks_all")
counts = dq["status"].value_counts()
kpis([("Checks passed", f"{counts.get('PASS', 0)}", "as expected"),
      ("Warnings", f"{counts.get('WARN', 0)}", "known limitation, documented"),
      ("Failures", f"{counts.get('FAIL', 0)}", "needs investigation before results are used")])
cats = sorted(dq["category"].unique())
f1, f2 = st.columns([3, 2])
pick = f1.pills("Category", cats, selection_mode="multi", default=cats) or cats
stat = f2.pills("Status", ["PASS", "WARN", "FAIL"], selection_mode="multi", default=["PASS", "WARN", "FAIL"]) \
    or ["PASS", "WARN", "FAIL"]
view = dq[dq["category"].isin(pick) & dq["status"].isin(stat)].sort_values(["status", "check_id"],
                                                                           key=lambda s: s.map({"FAIL": 0, "WARN": 1, "PASS": 2}) if s.name == "status" else s)
rows = "".join(
    f"<tr><td>{r.check_id}</td><td>{status_badge(r.status)}</td><td>{r.check_name}</td>"
    f"<td style='white-space:nowrap'>{r.actual}</td><td class='note'>{r.detail}</td></tr>"
    for r in view.itertuples())
md(
    "<table style='width:100%;font-size:0.86rem;border-collapse:collapse'>"
    "<thead><tr style='text-align:left;border-bottom:1px solid #c3c2b7'><th>ID</th><th>Status</th><th>Check</th>"
    f"<th>Result</th><th>Note</th></tr></thead><tbody>{rows}</tbody></table>", unsafe_allow_html=True)

md("## Do our penalty estimates match what CMS actually charged?")
if v:
    kpis([
        ("Hospitals classified the same way", pct(v["agreement"], 1),
         f"penalized: ours {v['ours_penalized']:,} vs CMS {v['cms_penalized']:,} among the {v['hospitals_compared']:,} "
     f"hospitals we could compare (CMS's published total: {m['known_numbers']['fy2026_hospitals_penalized']:,})"),
        ("Correlation with CMS's actual cut", f"{v['r_pearson']:.2f}", f"rank correlation {v['r_spearman']:.2f}"),
        ("Average cut among penalized", f"{pct(v['mean_reduction_ours'], 2)}", f"CMS actual {pct(v['mean_reduction_cms'], 2)}"),
        ("Hidden discharge counts", f"{pct(v['imputation_within_bounds'])}", "of true values inside our low–high range"),
    ])
    md(
        """
CMS publishes each hospital's actual FY2026 payment cut (Table 15) and a supplemental file with the information our
files lack (peer groups, payment shares, hidden counts). We used them **only to test** our method; nothing in the
model is fitted to them.
"""
    )
    vpath = ROOT / "data" / "processed" / "cms_validation_hospital.parquet"
    c1, c2 = st.columns([3, 2])
    with c1:
        if vpath.exists():
            chart(charts.validation_scatter(
                pd.read_parquet(vpath), f"Our estimates track CMS's actual cuts closely (r = {v['r_pearson']:.2f})",
                "Payment cut per hospital, FY2026: our estimate vs CMS Table 15; diagonal = perfect match"), key="val")
        else:
            st.info("Hospital-level comparison chart appears after `python -m src.validate_cms --download`.")
    with c2:
        thr = pd.read_csv(ROOT / "reports" / "tables" / "cms_validation_thresholds.csv")
        thr["condition"] = thr["condition_code"].map(charts.CONDITION_LABELS)
        md("**Penalty thresholds: CMS peer groups vs the national median we use**")
        st.dataframe(thr[["condition"] + [c for c in thr.columns if c.startswith("peer_group")] + ["national_median_used"]]
                     .round(4), hide_index=True, width="stretch")
        st.caption("Peer group 1 = fewest dual-eligible (low-income) patients, 5 = most. Using one national "
                   "threshold over-flags high-dual hospitals: our flag rate in group 5 is "
                   f"{pct(v['peer_groups'][-1]['ours_share_above_threshold'])} vs CMS's "
                   f"{pct(v['peer_groups'][-1]['cms_share_penalized'])}.")
else:
    st.info("The optional comparison with CMS's actual penalties has not been run "
            "(`python -m src.validate_cms --download`).")

md("## Why small hospitals' scores barely move")
k = table("shrinkage_k")
chart(charts.shrinkage_curves(
    table("shrinkage_bins"), k,
    "At small hospitals, only a fraction of a real change in readmissions reaches the CMS score",
    "Share of a hospital's actual (observed − expected) readmission gap that shows up in its published score, "
    "by volume; dots = measured in volume bands, lines = fitted n / (n + k)"), key="shrink")
hf = k.set_index("condition_code").loc["HF"]
md(
    f"""
CMS's statistical model pulls each hospital's result toward the national average, more strongly when the hospital has
few cases. Measured directly from the published data (fit R² ≥ {k['r_squared'].min():.2f}): for heart failure, a hospital
with 100 eligible discharges over three years sees only **{pct(hf['pass_through_at_100'])}** of a real improvement in its
score; at 1,500 discharges it sees **{pct(hf['pass_through_at_1500'])}**. This matches published reliability studies
and matters for the business case: the same program buys less penalty relief at a small hospital.
"""
)
show_data(k.round(3), "Show the fitted values")

how_to_read(
    """
- **Join funnel (first chart):** each bar is how many hospitals remain after a step. Among the data steps, the biggest
  drop (215) is hospitals with no condition scored (too few patients), which can never be penalized. The last bar shows
  how many of the remaining hospitals our estimate penalizes (2,336 of 2,777).
- **Stacked bars (second chart):** for each condition, the share of hospitals where CMS published a full result (dark
  blue), only the score with hidden counts (light blue), or no score at all (grays). Hip/knee is mostly light blue:
  readmissions after joint replacement are rare (≈5%), so counts are often below CMS's privacy threshold.
- **Checks table:** PASS = matches what we expected; WARN = a known limitation we work around and document; FAIL =
  needs investigation before results are used (there are none). "Known numbers" checks compare our results with figures CMS has published.
- **Validation:** each dot is a hospital. If our estimate equalled CMS's actual payment cut, every dot would sit on
  the diagonal. Most cluster near it; misses come mainly from CMS's peer-group thresholds, which our files lack.
- **Shrinkage chart:** read across the bottom (hospital size) and up (how much of a real change "counts"). The curve
  rises with volume: big hospitals are judged on their own record, small ones mostly on the national average.
"""
)
