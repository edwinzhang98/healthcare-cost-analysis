from dataclasses import replace

import numpy as np
import pandas as pd
import streamlit as st

from dashboard.common import (md, CONDITION_LABELS, all_model_inputs, chart, charts, config, hospital_names, how_to_read, kpis,
                              metrics, money, page, pct, preset_params, short_name, show_data)
from src import analysis, client, cost_model as cm

cfg = config()
iv = cfg["intervention"]
m = metrics()
page("Intervention Business Case",
     "If we fund a post-discharge follow-up program, what does it cost, what does it recover, when, and under which "
     "assumptions does it pay for itself?")

names = {k: short_name(v) for k, v in hospital_names().items()}
ids_all = client.client_ids()
pilot = analysis.pilot_hospitals()
PRESETS = {"broad": "Broad program (all medical conditions, all 8 hospitals)",
           "targeted": "Targeted pilot (heart failure + pneumonia, 2 best-placed hospitals)"}
PCT_FIELDS = ("reach", "relative_reduction", "hospital_share_of_savings", "ma_share", "persistence",
              "variable_cost_share")
FIELDS = ["reach", "risk_multiplier", "relative_reduction", "cost_per_enrollee", "fixed_cost_per_hospital",
          "cost_per_readmission", "hospital_share_of_savings", "variable_cost_share", "ma_share", "persistence"]


def load_preset(name: str) -> None:
    p = preset_params(name)
    st.session_state["bc_conditions"] = list(p.target_conditions)
    st.session_state["bc_targeting"] = p.targeting
    st.session_state["bc_hospitals"] = ids_all if name == "broad" else pilot
    st.session_state["bc_pass"] = p.pass_through_mode
    st.session_state["bc_payment_scale"] = 100
    st.session_state["bc_beds_refilled"] = p.beds_refilled
    for f in FIELDS:
        v = getattr(p, f)
        st.session_state[f"bc_{f}"] = int(round(v * 100)) if f in PCT_FIELDS else v


if "bc_reach" not in st.session_state:
    load_preset("targeted")
    st.session_state["bc_preset"] = "targeted"


def on_preset():
    load_preset(st.session_state["bc_preset"])


# ---------------------------------------------------------------- controls
c1, c2 = st.columns([2, 3])
c1.radio("Start from", list(PRESETS), format_func=PRESETS.get, key="bc_preset", on_change=on_preset,
         help="Loads a set of assumptions; you can change any of them below.")
c2.multiselect("Hospitals in the program", ids_all, key="bc_hospitals", format_func=lambda f: names[f])

with st.expander("Program design and assumptions (sources: docs/assumptions.md)", expanded=True):
    d1, d2, d3 = st.columns(3)
    with d1:
        md("**Who is enrolled**")
        st.multiselect("Conditions", charts.CONDITION_ORDER, key="bc_conditions", format_func=lambda c: CONDITION_LABELS[c])
        st.radio("Which hospital-conditions", ["above_threshold", "all"], key="bc_targeting",
                 format_func={"above_threshold": "Only where we are above the penalty threshold",
                              "all": "All, regardless of score"}.get)
        st.slider("Share of eligible Medicare patients enrolled", 10, 90, key="bc_reach", step=5, format="%d%%")
        st.slider("Readmission risk of enrolled patients vs average (×)", 1.0, 2.0, key="bc_risk_multiplier", step=0.1,
                  help="1.0 = enroll a random sample; 1.5 = enroll higher-risk patients first (top ~30% by a risk score).")
    with d2:
        md("**What the program achieves and costs**")
        st.slider("Readmission reduction among enrolled patients", 0, 30, key="bc_relative_reduction", step=1, format="%d%%",
                  help="Base for pneumonia / heart attack (recent trials: about 11%). Applied ×1.2 for heart failure, "
                       "×0.5 for COPD, ×0.3 for surgery, following the strength of the trial evidence.")
        st.slider("Cost per enrolled patient", 100, 1000, key="bc_cost_per_enrollee", step=25, format="$%d")
        st.slider("Fixed cost per hospital per year", 0, 150_000, key="bc_fixed_cost_per_hospital", step=5_000, format="$%d")
        st.radio("How much of a real change reaches the CMS score", ["volume", "full"], key="bc_pass",
                 format_func={"volume": "Depends on hospital volume (measured)", "full": "All of it (naive)"}.get)
        st.slider("How much of today's excess would persist anyway", 30, 100, key="bc_persistence", step=5, format="%d%%",
                  help="Penalties drift back toward the average: across hospitals, the actual FY2027 cut was about 0.58 x the FY2026 cut plus a small constant "
                       "(0.16 points), so big cuts shrank and small ones grew. 100% = assume today's penalty simply continues.")
    with d3:
        md("**Money and rules**")
        st.slider("Medicare Advantage share of patients", 0, 80, key="bc_ma_share", step=5, format="%d%%",
                  help="From FY2027, CMS's score counts MA patients, but the penalty applies only to traditional "
                       "Medicare payments. Set to 0 to see a cohort with no MA patients (the two-year scoring window stays).")
        st.slider("Share of payer savings returned to the hospital", 0, 100, key="bc_hospital_share_of_savings", format="%d%%",
                  step=5, help="Shared-savings / ACO contracts: payers save about the Medicare payment on each "
                               "avoided readmission; this is the share they give back.")
        st.slider("Cost of one readmission to the hospital", 10_000, 30_000, key="bc_cost_per_readmission", step=500, format="$%d")
        st.slider("Share of that cost that is variable", 50, 95, key="bc_variable_cost_share", step=5, format="%d%%",
                  help="MedPAC: 75-85% of hospital costs vary with volume. The rest (buildings, most salaries in the "
                       "short run) stays when a readmission is avoided.")
        st.checkbox("Freed beds get refilled (no lost margin)", key="bc_beds_refilled")
        st.slider("Medicare payment per discharge, vs base estimate", 70, 130, key="bc_payment_scale", step=5, format="%d%%")

ss = st.session_state
if not ss["bc_hospitals"] or not ss["bc_conditions"]:
    st.warning("Pick at least one hospital and one condition.")
    st.stop()
p = replace(preset_params(ss["bc_preset"]),
            target_conditions=tuple(ss["bc_conditions"]), targeting=ss["bc_targeting"],
            reach=ss["bc_reach"] / 100, risk_multiplier=float(ss["bc_risk_multiplier"]),
            relative_reduction=ss["bc_relative_reduction"] / 100, cost_per_enrollee=float(ss["bc_cost_per_enrollee"]),
            fixed_cost_per_hospital=float(ss["bc_fixed_cost_per_hospital"]),
            cost_per_readmission=float(ss["bc_cost_per_readmission"]),
            hospital_share_of_savings=ss["bc_hospital_share_of_savings"] / 100,
            variable_cost_share=ss["bc_variable_cost_share"] / 100, beds_refilled=bool(ss["bc_beds_refilled"]),
            persistence=ss["bc_persistence"] / 100,
            ma_share=ss["bc_ma_share"] / 100, pass_through_mode=ss["bc_pass"], payment_scale=ss["bc_payment_scale"] / 100)
M = all_model_inputs().subset(ss["bc_hospitals"])
res = cm.evaluate(M, p)
t = res["totals"]
ph = analysis.phase_in(M, p)
payback = analysis.years_to_payback(ph)

kpis([
    ("Program cost per year", money(t["program_cost"]), f"{t['enrollees']:,.0f} patients enrolled · {t['n_hospitals_running']} hospitals"),
    ("Penalty avoided per year", money(t["avoided_penalty"]),
     f"full strength (FY2032+) · expected penalty without program {money(t['penalty_before'])} (FY2026 est. {money(t['penalty_today'])})"),
    ("Readmissions avoided per year", f"{t['readmissions_avoided']:,.0f}", f"program cost per readmission avoided {money(t['cost_per_readmission_avoided'])}"),
    ("Hospital net per year", money(t["hospital_net"]), f"payback: {payback}"),
    ("Whole-system net per year", money(t["combined_net"]), "payers and hospital together"),
])

st.caption(f"Per avoided readmission: payers save about {money(p.payment_per_readmission)} (Medicare payment); the hospital "
           f"loses that payment but saves {money(p.variable_cost_per_readmission)} of variable cost, so it loses "
           f"{money(p.lost_margin_per_readmission)} of margin; payers and hospital together save "
           f"{money(p.variable_cost_per_readmission)}.".replace("$", "&#36;"), unsafe_allow_html=True)
chart(charts.waterfall(
    t, p.hospital_share_of_savings,
    f"Each $1 of program cost returns ${t['benefit_cost_ratio']:.2f} to the hospital" if t["program_cost"] else "No program",
    "Hospital view, US$ per year at steady state: avoided penalty + payer savings shared back − lost margin − program cost"),
    key="wf")
chart(charts.phase_in_chart(
    ph, p.hospital_share_of_savings,
    "Penalty relief arrives two years after the program starts" if t["avoided_penalty"] > 0 else "No penalty relief",
    f"Hospital view by fiscal year; program starts {iv['program_start']} at half strength for 12 months; "
    "CMS scores a 2-year window that ends 15 months before each fiscal year"), key="phase")
show_data(ph[["fiscal_year", "cms_window", "program_share_of_cms_window", "program_cost", "avoided_penalty",
              "savings_shared_with_hospital", "lost_margin", "system_savings", "hospital_net", "hospital_net_cum",
              "combined_net", "combined_net_cum"]].round(2),
          "Show the year-by-year numbers")

md("## Which assumptions matter most")
tor = cm.tornado(M, p)
flips = tor[tor["sign_flips"]]["label"].tolist()
chart(charts.tornado_chart(
    tor, t["hospital_net"],
    ("Conclusion holds under every ±30% change" if not flips else
     f"{len(flips)} of {len(tor)} inputs can flip the result at ±30%"),
    "Hospital net per year when one input moves 30% down (orange) or up (blue); red line = break-even"), key="tor")
xs = np.round(np.arange(0.02, 0.305, 0.02), 3)
ys = np.arange(100, 1001, 50)
grid = cm.grid(M, p, "relative_reduction", xs, "cost_per_enrollee", ys)
be = cm.break_even(M, p, "relative_reduction", lo=0.0, hi=0.6)
chart(charts.breakeven_heatmap(
    grid, "relative_reduction", "cost_per_enrollee", "hospital_net", (p.relative_reduction, p.cost_per_enrollee),
    (f"Break-even needs at least a {pct(be, 1)} base-condition reduction at this cost (heart failure counts 1.2×)"
     if be is not None
     else "No break-even within a 0-60% effect at this cost"),
    "Hospital net per year for combinations of effect size and cost per patient; black line = break-even",
    "Readmission reduction among enrolled (base condition)", "Cost per enrolled patient"), key="grid")

sens = analysis.sensitivity_table(M, p)
sv = sens.pivot_table(index="label", columns="change", values=["hospital_net", "combined_net"]).round(0)
sv.columns = [f"{a.replace('_', ' ')} ({b})" for a, b in sv.columns]
flip_h = sens.groupby("label")["hospital_sign_flips"].any()
flip_c = sens.groupby("label")["combined_sign_flips"].any()
sv["hospital result flips?"] = flip_h.map({True: "yes", False: "no"})
sv["system result flips?"] = flip_c.map({True: "yes", False: "no"})
md("**±30% sensitivity table**: does the sign of the result change?")
st.dataframe(sv.reset_index().rename(columns={"label": "Input"}), hide_index=True, width="stretch")

md("## How likely is it to pay off? (Monte Carlo)")
mc_c1, mc_c2 = st.columns([3, 2])
ranges = {k: tuple(v) for k, v in iv["ranges"].items()}
with mc_c2:
    md("Each run draws every uncertain input at random within its low–high range (triangular "
                "distributions, fixed seed so results are reproducible):")
    st.dataframe(pd.DataFrame([{"input": k, "low": v[0], "base": v[1], "high": v[2]} for k, v in ranges.items()]),
                 hide_index=True, width="stretch")
    runs = st.select_slider("Runs", options=[200, 500, 1000], value=500)
with mc_c1:
    mc = cm.monte_carlo(M, p, ranges, n=runs, seed=cfg["random_seed"])
    chart(charts.monte_carlo_hist(
        mc, "hospital_net", f"The hospital comes out ahead in {pct((mc['hospital_net'] > 0).mean())} of runs "
                            f"(whole system: {pct((mc['combined_net'] > 0).mean())})",
        "Distribution of hospital net per year across simulation runs, US$"), key="mc")

md("## By hospital")
hh = res["hospitals"].assign(hospital=lambda d: d["facility_id"].map(names))
st.dataframe(hh[["hospital", "enrollees", "program_cost", "penalty_today", "penalty_before", "avoided_penalty",
                 "readmissions_avoided", "lost_margin", "system_savings", "hospital_net", "combined_net"]].round(0)
             .sort_values("hospital_net", ascending=False), hide_index=True, width="stretch")

how_to_read(
    """
- **Two views of the same program.** *Hospital net* is what the hospital's P&L sees: avoided penalties, plus any
  readmission savings it keeps under risk contracts, minus the margin it loses when a fee-for-service readmission
  doesn't happen, minus program cost. *Whole-system net* asks whether the program is a good use of money for
  payers and the hospital together: readmission costs avoided minus program cost (patients' health gains are real but not counted in dollars). (The penalty is money
  moving from the hospital to Medicare, so it cancels out in the whole-system view.)
- **Expected penalty without the program:** penalties regress toward the mean (page 5), so the starting point is a
  forecast that keeps half of today's excess above average, not today's penalty. That is why the expected penalty is
  smaller than the FY2026 estimate. Move "How much of today's excess would persist" to 100% to see the naive version.
- **Waterfall:** blue bars add value, red bars cost money, the gray bar is what's left each year once the program is
  fully running. "Each $1 returns $X" is the benefit-cost ratio: below $1.00 the program loses money for the hospital.
- **Year-by-year chart:** costs start on day one, but CMS scores hospitals on a rolling 2-year window that ends 15
  months before each payment year. So a program that starts in January 2027 first touches penalties in FY2029
  (October 2028), and reaches full strength only in FY2032 (FY2031 already gets about 88%). The black line is the running total.
- **Tornado:** each bar shows how far the yearly result moves when one input is 30% lower (orange) or higher (blue).
  Long bars are the assumptions worth pinning down in a pilot. If a bar crosses the red line, that input alone can
  flip the answer.
- **Break-even map:** blue squares make money, red lose money, the black line is break-even. The cross marks the
  current settings. If the cross sits close to the line, the decision depends on how well the program performs, which
  argues for a measured pilot before scaling.
- **Monte Carlo:** instead of one best guess, it re-runs the model many times with all inputs varied together. The
  share of runs above zero is a plain-English "chance it pays off" under our ranges.
- **Why small hospitals gain little:** CMS's scoring gives small hospitals only partial credit for improvement
  (page 2). Switch "How much of a real change reaches the CMS score" to *All of it* to see how much a naive model would
  overstate penalty savings.
"""
)
