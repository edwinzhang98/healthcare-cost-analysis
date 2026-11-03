import pandas as pd
import streamlit as st

import pandas as pd

from dashboard.common import md, esc, chart, charts, how_to_read, metrics, money, page, pct
from src import recommendations

m = metrics()
page("Recommendations",
     "What should the group do, who owns each step, what impact should we expect, how will we measure it, and what "
     "could go wrong?")

sc = m["business_case"]["scenarios"]
opts = pd.DataFrame([
    {"option": "Broad program, all 8 hospitals", **sc["broad_all"]},
    {"option": "Targeted program, all 8 hospitals", **sc["targeted_all"]},
    {"option": "Pilot at the 2 best-placed hospitals", **sc["targeted_pilot"]},
    {"option": "Pilot + 30% of payer savings shared back", **sc["targeted_pilot_risk30"]},
])
chart(charts.options_chart(
    opts, "Only the pilot with payer co-funding breaks even for the hospital",
    "Net value per year once the program is fully counted (FY2031+), base-case assumptions; blue = hospital P&L, "
    "aqua = patients, payers and hospital together"), key="opts")

recs = recommendations.build(m)
for i, r in enumerate(recs, 1):
    with st.container(border=True):
        md(f"**{i}. {r['what']}**")
        c1, c2 = st.columns(2)
        c1.markdown(esc(f"**Owner:** {r['who']}  \n**Expected impact:** {r['impact']}"), unsafe_allow_html=True)
        c2.markdown(esc(f"**How we measure it:** {r['measure']}  \n**Risk:** {r['risk']}"), unsafe_allow_html=True)

md("## How we will know the pilot worked")
md(
    """
- **Compare against a control group, not against last year.** Hospitals with high readmissions tend to look better
  the next year anyway (regression to the mean explains most of the improvement at penalized hospitals in published
  research). Compare enrolled patients with similar patients who were not enrolled, or stagger the start across units.
- **Track the patient outcome monthly, the penalty yearly.** Readmission rates respond within months; CMS penalties
  respond only after the two-year scoring window rolls forward.
- **Watch for unintended effects.** Fewer readmissions should not come from more observation stays or ED visits
  (CMS tracks these separately), or from higher mortality among heart failure patients (a concern raised in published
  research).
"""
)

md("## Limitations to keep in mind")
md(
    """
- **Hospital-level public data.** We see each hospital's scores, not its patients, so we can say *where* readmissions
  are high, not *why*. Differences between hospital groups are associations, not causes.
- **Penalty dollars are estimates.** CMS does not publish them; we rebuild them from the published scores with CMS's
  formula and national average payments. The count of penalized hospitals matches CMS within about 1%, but dollars for
  one hospital can be off by ±30% or more (actual payments depend on wage index and case mix).
- **Peer groups are missing.** CMS compares each hospital with hospitals serving a similar share of low-income
  (dual-eligible) patients. Using one national threshold overstates penalties for safety-net hospitals.
- **The rules changed in FY2027.** The score now uses 2 years of data and includes Medicare Advantage patients; our
  scores are from the FY2026 program (Jul 2021–Jun 2024). The business case applies the new rules, but the starting
  scores are a year older than the penalties now in effect.
- **Program effects come from trials.** Real-world programs usually do worse than trials; the base case already uses
  the more conservative recent-trial estimate (about a 10% reduction).
"""
)

md("## With more data we would")
md(
    """
- Use the hospitals' own CMS Hospital-Specific Reports (exact payments, peer group, patient-level readmissions) instead
  of estimates.
- Add claims data to see causes of readmission and which patients to enroll (risk scores), and the hospitals' cost
  accounting data to replace the national lost-margin assumption.
- Add the share of each hospital's patients in Medicare Advantage, which drives how much the FY2027 rules dilute the
  penalty benefit.
"""
)

how_to_read(
    """
- **Chart:** each pair of bars is one way to run the program. Blue is what the hospital's books see each year once the
  program is fully counted; aqua is the value to patients, payers and the hospital together. Bars to the left of the
  line lose money. The broad program loses money in both views; the pilot is close to break-even and turns positive
  for the hospital only if payers share part of their savings.
- **Cards:** each card is one recommendation in a standard format: **what** to do, **who** owns it, the **expected
  impact** in numbers from this analysis, **how** we will measure it, and the main **risk**. The numbers come from the
  same model as pages 5 and 6 (base-case assumptions), so they update when the analysis is rerun.
"""
)
