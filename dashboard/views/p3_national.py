import streamlit as st

from dashboard.common import (md, CONDITION_LABELS, chart, charts, how_to_read, kpis, metrics, money, page, pct, show_data,
                              table)
from src import drivers

m = metrics()
nat = m["national"]
seg = table("mart_segment_summary")

page("National Picture",
     "Across US hospitals, which conditions, states and types of hospital account for most excess readmissions "
     "and penalty dollars?")

kpis([
    ("Excess readmissions per year", f"{nat['excess_readmissions_per_year']:,.0f}",
     f"above expected, at hospitals with ERR > 1 · {nat['eligible_discharges_per_year']:,.0f} eligible discharges/yr"),
    ("Estimated penalties per year", money(nat["total_penalty"]),
     f"{nat['hospitals_penalized']:,} hospitals · median {money(nat['median_penalty_penalized'])}"),
    ("Top 10% of hospitals carry", pct(nat["top10_share_of_penalty"]), "of penalty dollars"),
    ("Median payment cut (penalized)", pct(nat["median_reduction_pct_penalized"], 2), "of base Medicare inpatient payments"),
])

# ---------------------------------------------------------------- filter row
f1, f2, f3 = st.columns([2, 2, 2])
cond_opts = ["ALL"] + charts.CONDITION_ORDER
cond = f1.selectbox("Condition", cond_opts, format_func=lambda c: "All six conditions" if c == "ALL" else CONDITION_LABELS[c])
metric_label = f2.selectbox("Map shows", ["Average ERR", "Share of hospitals above the penalty threshold",
                                          "Penalty dollars per eligible discharge"])
dim_label = f3.selectbox("Compare hospitals by", ["Ownership", "Size", "Census region", "Star rating",
                                                  "Spending (MSPB)", "Emergency services"])
cond_name = "all six conditions" if cond == "ALL" else CONDITION_LABELS[cond].lower()

# ---------------------------------------------------------------- map
md("## By state")
states = seg[(seg["segment_dimension"] == "State") & (seg["condition_code"] == cond)].rename(columns={"segment_value": "state"})
if metric_label == "Average ERR":
    col, fmt, mid, cb = "mean_err", ".3f", 1.0, "Average ERR"
elif metric_label.startswith("Share"):
    col, fmt, mid, cb = "share_above_threshold", ".0%", None, "Share above threshold"
else:
    col, fmt, mid, cb = "penalty_per_discharge", ",.0f", None, "Penalty $ per discharge"
states = states.assign(hospitals=states["n_hospitals"].map("{:,}".format),
                       sample_note=states["small_sample_flag"].map({True: "small sample (<30 results)", False: "ok"}))
top = states.sort_values(col, ascending=False).head(3)
top_txt = ", ".join(f"{r.state} ({format(r[col], fmt)})" for _, r in top.iterrows())
chart(charts.state_tile_map(
    states, col, f"Highest {metric_label.lower()} for {cond_name}: {top_txt}",
    f"{metric_label} by state, payment-eligible hospitals, FY2026 program (Jul 2021–Jun 2024). Maryland is exempt.",
    cb, diverging_mid=mid, fmt=fmt, hover_cols={"hospitals": "Hospitals", "sample_note": "Sample"}), key="map")
show_data(states[["state", "n_hospitals", "n_results", "mean_err", "mean_err_ci_low", "mean_err_ci_high",
                  "share_above_threshold", "penalty_annual", "penalty_per_discharge", "small_sample_flag"]]
          .sort_values(col, ascending=False).round(4))

# ---------------------------------------------------------------- condition mix
md("## By condition")
mix = drivers.condition_mix(seg)
chart(charts.condition_mix(
    mix, f"Heart failure and pneumonia drive {pct(nat['hf_pn_share_excess_readmissions'])} of excess readmissions; "
         f"surgery drives {pct(nat['surgical_share_penalty'])} of penalty dollars",
    "Share of national total by condition: eligible discharges, excess readmissions, estimated penalty $"), key="mix")
cs = table("condition_summary")
cs_view = cs.assign(condition=cs["condition_code"].map(CONDITION_LABELS))[
    ["condition", "payment_per_discharge", "expected_rate_pct", "penalty_per_excess_readmission", "share_discharges",
     "share_excess_readmissions", "share_penalty"]].round(3)
md(
    f"""
Why surgery is expensive: CMS's formula charges a hospital roughly **(payment per case) ÷ (expected readmission rate)**
for each readmission above the threshold. Hip/knee replacement has a high payment and a low readmission rate (≈5%),
so one extra readmission costs about **{money(nat['conditions']['HIP_KNEE']['penalty_per_excess_readmission'])}** in
penalties, versus **{money(nat['conditions']['HF']['penalty_per_excess_readmission'])}** for heart failure.
"""
)
show_data(cs_view, "Show penalty per extra readmission by condition")

# ---------------------------------------------------------------- segments
md(f"## By {dim_label.lower()}")
orders = {
    "Size": ["Small", "Medium", "Large"],
    "Star rating": ["1 star", "2 star", "3 star", "4 star", "5 star", "Not rated"],
    "Spending (MSPB)": ["Below 0.95", "0.95-0.99", "1.00-1.04", "1.05 and above", "Not available"],
    "Census region": ["Northeast", "Midwest", "South", "West"],
    "Ownership": ["Non-profit", "For-profit", "Government"],
    "Emergency services": ["Has emergency dept", "No emergency dept"],
}
st_tab = drivers.segment_table(seg, dim_label, cond)
nat_row = seg[(seg["segment_dimension"] == "National") & (seg["condition_code"] == cond)].iloc[0]
hi = st_tab.sort_values("mean_err", ascending=False).iloc[0]
lo = st_tab.sort_values("mean_err").iloc[0]
chart(charts.segment_dots(
    st_tab, f"{hi['segment_value']} hospitals average ERR {hi['mean_err']:.3f} vs {lo['mean_err']:.3f} for "
            f"{lo['segment_value'].lower() if dim_label != 'Census region' else lo['segment_value']}",
    f"Average ERR with 95% interval, {cond_name}; hollow marker = fewer than 30 results",
    reference=float(nat_row["mean_err"]), order=orders.get(dim_label)), key="seg")
if dim_label in ("Star rating", "Spending (MSPB)"):
    st.warning(
        "Read with care: this comparison is partly circular. The overall star rating includes readmission measures, "
        "and the spending index counts the cost of readmissions within 30 days. They move with ERR partly by "
        "construction, so they describe readmission performance rather than explain it.", icon="⚠️")
show_data(st_tab[["segment_value", "n_hospitals", "n_results", "mean_err", "mean_err_ci_low", "mean_err_ci_high",
                  "share_above_threshold", "share_discharges", "share_excess_readmissions", "share_penalty",
                  "penalty_per_discharge", "small_sample_flag"]].round(4))

if True:
    curve = table("concentration_curve")
    chart(charts.concentration(
        curve, f"The top 10% of hospitals carry {pct(nat['top10_share_of_penalty'])} of penalty dollars",
        "Cumulative share of estimated penalty $, hospitals ranked from highest to lowest penalty"), key="conc")
if True:
    coefs = table("regression_coefs")
    info = nat["regression"]["info"]
    chart(charts.coefficient_plot(
        coefs, "Ownership and region stay associated with ERR after adjusting for the others",
        f"Adjusted difference in ERR points, one model with all factors plus condition; "
        f"{info['n_rows']:,} results from {info['n_hospitals']:,} hospitals; hollow = not significant"), key="coef")
    show_data(coefs.round(3), "Show the model estimates")

how_to_read(
    """
- **Map:** every state is the same size, so small states are as visible as large ones. In "Average ERR" mode, blue
  states readmit fewer patients than expected and red states more (1.00 = as expected). Hover a tile for the number of
  hospitals; states with few hospitals are flagged as small samples, so treat their colors as rough.
- **Condition bars:** gray = how much of the patient volume a condition represents, blue = its share of readmissions
  above expectation, orange = its share of penalty dollars. When orange is much longer than gray (bypass, hip/knee),
  that condition is expensive per patient under the penalty formula.
- **Segment dots:** each dot is the average ERR of a group of hospitals; the line through it is the 95% interval (the
  range the true average plausibly sits in). If two groups' intervals don't overlap, the difference is unlikely to be
  chance.
- **Concentration curve:** if every hospital paid the same penalty, the line would follow the diagonal. The more it
  bows upward, the more the penalty is concentrated in a few hospitals.
- **Adjusted differences (right):** compares, for example, for-profit and non-profit hospitals *of the same size, region
  and emergency-department status, for the same condition*. One ERR point = 1% more readmissions than expected.
  These are associations, not causes: ownership does not *cause* readmissions; it travels with patient mix, markets
  and practices we cannot see in these files.
"""
)
