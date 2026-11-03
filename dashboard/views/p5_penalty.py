import pandas as pd
import streamlit as st

from dashboard.common import (md, CONDITION_LABELS, ROOT, chart, charts, config, hospital_label, hospital_names, hospital_options,
                              how_to_read, kpis, metrics, money, page, payments, pct, short_name, table)
from src import client, penalty as pen

m = metrics()
cfg = config()
page("Penalty Exposure",
     "How much did each hospital lose to the readmission penalty in the FY2026 payment year (our estimate), which "
     "conditions drove it, and how much would better scores save?")

fct = table("fct_hospital_condition")
dim = table("dim_hospital")
names = {k: short_name(v) for k, v in hospital_names().items()}

# ---------------------------------------------------------------- scope + assumptions (filter row)
f1, f2 = st.columns([2, 3])
scope = f1.radio("Scope", ["Client group (8 hospitals)", "One hospital", "One state"], horizontal=False)
if scope.startswith("Client"):
    ids = client.client_ids()
    scope_name = "the client group"
elif scope == "One hospital":
    fid = f2.selectbox("Hospital", hospital_options(), format_func=hospital_label)
    ids = [fid]
    scope_name = names[fid]
else:
    st_list = sorted(dim.loc[dim["is_payment_eligible"], "state"].unique())
    stt = f2.selectbox("State", st_list, index=st_list.index("NJ"))
    ids = dim.loc[(dim["state"] == stt) & dim["is_payment_eligible"], "facility_id"].tolist()
    scope_name = f"hospitals in {stt}"

with st.expander("Assumptions behind the dollar estimate (change them to see how much they matter)", expanded=False):
    a1, a2, a3 = st.columns(3)
    thr_method = a1.radio("Penalty threshold", ["National median ERR (base)", "1.00"],
                          help="CMS compares each hospital with the median of its peer group (by share of "
                               "low-income patients). Peer groups are not in our files, so we use the national median.")
    disc_case = a2.radio("Hidden discharge counts", ["Middle of the possible range (base)", "Minimum (25)", "Maximum"],
                         help="CMS hides counts when a hospital had 1-10 readmissions.")
    scale = a3.slider("Medicare payment per discharge, % of base estimate", 70, 130, 100, 5,
                      help="Base: FY2026 national standardized amount × FY2026 DRG weights.") / 100
pp = pen.PenaltyParams(
    penalty_cap_pct=cfg["penalty_model"]["penalty_cap_pct"], hrrp_payment_share=cfg["penalty_model"]["hrrp_payment_share"],
    neutrality_modifier=cfg["penalty_model"]["neutrality_modifier"],
    threshold_method="one" if thr_method == "1.00" else "national_median", payment_scale=scale,
    discharges_case={"Minimum (25)": "low", "Maximum": "high"}.get(disc_case, "base"))
thresholds = pen.penalty_thresholds(fct, pp.threshold_method)

md("## What if our scores improved?")
w1, w2 = st.columns([2, 3])
cut = w1.slider("Lower every selected ERR by", 0, 15, 5, 1, format="%d%%",
                help="A 5% lower ERR means 5% fewer readmissions than today relative to expected.") / 100
conds = w2.multiselect("For these conditions", charts.CONDITION_ORDER, default=charts.CONDITION_ORDER,
                       format_func=lambda c: CONDITION_LABELS[c])

sub = fct[fct["facility_id"].isin(ids)].copy()
cond_now, hosp_now = pen.estimate(sub, payments(), pp, thresholds=thresholds)
new_err = sub["err"].where(~sub["condition_code"].isin(conds), sub["err"] * (1 - cut))
cond_new, hosp_new = pen.estimate(sub, payments(), pp, err=new_err, thresholds=thresholds)
now, new = hosp_now["penalty"].sum(), hosp_new["penalty"].sum()

kpis([
    (f"Estimated penalty, {scope_name}", f"{money(now)}/yr",
     f"{int(hosp_now['is_penalized'].sum())} of {len(hosp_now)} hospitals penalized"),
    ("After the what-if improvement", f"{money(new)}/yr",
     f"saves {money(now - new)} per year ({pct((now - new) / now if now else 0)})"),
    ("Average payment cut (penalized)", pct(hosp_now.loc[hosp_now["is_penalized"], "reduction_pct"].mean(), 2),
     "of base Medicare inpatient payments"),
    ("Hospitals at the 3% cap", f"{int(hosp_now['hits_cap'].sum())}", "cap rarely binds"),
])

# ---------------------------------------------------------------- charts
top_ids = hosp_now.sort_values("penalty", ascending=False)["facility_id"].head(15).tolist()
c_show = cond_now[cond_now["facility_id"].isin(top_ids)]
lead = hosp_now.sort_values("penalty", ascending=False).iloc[0]
share_lead = lead["penalty"] / now if now else 0
chart(charts.penalty_by_hospital(
    c_show, names,
    f"{names[lead['facility_id']]} carries {pct(share_lead)} of {scope_name}'s estimated penalty" if len(ids) > 1
    else f"{names[lead['facility_id']]}: {money(lead['penalty'])} per year",
    "Estimated HRRP penalty per year by hospital and condition, US$" + (" (15 largest shown)" if len(ids) > 15 else "")),
    key="penbar")

rows = sub[sub["facility_id"].isin(top_ids) & sub["has_err"]].assign(threshold=lambda d: d["condition_code"].map(thresholds))
chart(charts.threshold_heatmap(
    rows, names, "Red cells are the conditions being penalized; the number is the gap above the threshold",
    "ERR minus penalty threshold by hospital and condition (blue = below threshold, no penalty; blank = no CMS score (too few cases or not available))"),
    key="heat")

md("## Penalties are a moving target")
pers_path = ROOT / "data" / "processed" / "cms_persistence_hospital.parquet"
v = metrics().get("validation") or {}
pers = v.get("persistence") or {}
if pers_path.exists() and pers:
    chart(charts.persistence_scatter(
        pd.read_parquet(pers_path), pers["slope_fy2027_on_fy2026"],
        "Penalties drift back toward the average: big FY2026 cuts shrank in FY2027, small ones grew",
        "CMS actual payment cut by hospital, FY2026 vs FY2027 (Table 15). FY2027 also switched to a 2-year window that "
        "includes Medicare Advantage patients."), key="pers")
    md(f"""
Hospitals with the biggest FY2026 cuts saw them shrink the next year (top tenth: from
{pct(pers['top_decile_mean_cut_fy2026'], 2)} to {pct(pers['top_decile_mean_cut_fy2027'], 2)} on average;
{pct(pers['top_decile_share_losing_half'])} lost more than half). Part of that is the FY2027 rule change and part is
regression to the mean: an unusually bad window tends to be followed by a more normal one. **So we do not plan a program
around last year's penalty:** the business case (page 6) forecasts the penalty that would remain without a program,
keeping 50% of today's excess.
""")
else:
    st.info("The FY2026 vs FY2027 comparison appears after `python -m src.validate_cms --download`.")

md("## What one extra readmission costs in penalties")
cs = table("condition_summary").assign(condition=lambda d: d["condition_code"].map(CONDITION_LABELS))
st.dataframe(cs[["condition", "payment_per_discharge", "expected_rate_pct", "penalty_per_excess_readmission",
                 "penalty_per_excess_vs_readmission_cost"]].sort_values("penalty_per_excess_readmission", ascending=False),
             hide_index=True, width="stretch",
             column_config={"payment_per_discharge": st.column_config.NumberColumn("Medicare payment per case", format="$%d"),
                            "expected_rate_pct": st.column_config.NumberColumn("Typical readmission rate", format="%.1f%%"),
                            "penalty_per_excess_readmission": st.column_config.NumberColumn("Penalty per readmission above threshold", format="$%d"),
                            "penalty_per_excess_vs_readmission_cost": st.column_config.NumberColumn("× the cost of the readmission itself", format="%.1f×")})
st.caption("Under CMS's formula the penalty for one readmission above the threshold is about payment per case ÷ "
           "readmission rate × 0.9627 (the neutrality modifier). National averages; FY2026 rates.")

md("## Hospital detail")
det = hosp_now.merge(hosp_new[["facility_id", "penalty"]].rename(columns={"penalty": "penalty_after_whatif"}),
                     on="facility_id").merge(dim[["facility_id", "facility_name", "size_band"]], on="facility_id")
vpath = ROOT / "reports" / "tables" / "cms_validation_client.csv"
if vpath.exists():
    vcl = pd.read_csv(vpath, dtype={"facility_id": str})[["facility_id", "cms_reduction_fy2026", "cms_reduction_fy2027"]]
    det = det.merge(vcl, on="facility_id", how="left")
cols = ["facility_name", "size_band", "est_total_payments", "penalty", "reduction_pct", "penalty_after_whatif"] + \
       [c for c in ("cms_reduction_fy2026", "cms_reduction_fy2027") if c in det.columns]
for c in ("reduction_pct", "cms_reduction_fy2026", "cms_reduction_fy2027"):
    if c in det.columns:
        det[c] = det[c] * 100            # show as percentage points
st.dataframe(det[cols].sort_values("penalty", ascending=False), hide_index=True, width="stretch",
             column_config={"facility_name": "Hospital", "size_band": "HRRP volume",
                            "est_total_payments": st.column_config.NumberColumn("Est. base Medicare payments/yr", format="$%d"),
                            "penalty": st.column_config.NumberColumn("Est. penalty/yr", format="$%d"),
                            "reduction_pct": st.column_config.NumberColumn("Est. payment cut", format="%.2f%%"),
                            "penalty_after_whatif": st.column_config.NumberColumn("After what-if", format="$%d"),
                            "cms_reduction_fy2026": st.column_config.NumberColumn("CMS actual cut FY2026", format="%.2f%%"),
                            "cms_reduction_fy2027": st.column_config.NumberColumn("CMS actual cut FY2027", format="%.2f%%")})
if "cms_reduction_fy2027" in det.columns and scope.startswith("Client"):
    st.caption("CMS's actual cuts come from Table 15 (validation only, not a model input). "
               "FY2027 cuts (in effect now) use a newer 2-year window that also counts Medicare Advantage patients; "
               "they moved a lot for several hospitals, a reminder that penalties are volatile from year to year.")

how_to_read(
    """
- **Estimated penalty:** CMS cuts a hospital's regular Medicare inpatient payments by
  *payment share of the condition × how far its ERR is above the threshold*, summed over conditions and multiplied by
  0.9627 (a national adjustment), at most 3%. We turn that into dollars using each hospital's eligible discharges and
  the average Medicare payment per case. Exact payments are not public, so treat dollars as estimates (±30% is tested
  on page 6).
- **Stacked bars:** one bar per hospital, split by condition. The longest colored piece tells you where to focus.
- **Heatmap:** each cell is how far the hospital's score sits above (red) or below (blue) the penalty threshold. Only
  red cells cost money. A big red number on a low-volume condition can still matter little in dollars, so read it
  together with the bars.
- **What-if slider:** lowers the selected scores by the chosen percentage and recomputes the penalty with the same
  formula. It answers "what is a given improvement worth?", not "how do we get it?" (that is page 6). Because only
  scores above the threshold are penalized, the first few percent of improvement are worth the most for hospitals just
  above the line.
- **Assumptions box:** switching to the most extreme options shows how sensitive the dollars are. The ranking of
  hospitals and conditions barely changes. Hospital-level dollars carry roughly ±30% uncertainty (payments differ by
  wage index and case mix); compare hospitals on the payment-cut percentage when in doubt.
- **Safety-net hospitals:** CMS sets each hospital's threshold from peers with a similar share of low-income patients.
  We use one national threshold, which overstates penalties for hospitals serving many low-income patients
  (e.g., our estimate for Palisades is 0.82% vs CMS's actual 0.61% in FY2026).
"""
)
