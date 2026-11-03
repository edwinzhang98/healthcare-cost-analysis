
from src import recommendations
from dashboard.common import (md, charts, chart, how_to_read, kpis, metrics, money, page, pct, short_name, table, hospital_names,
                              show_data)

m = metrics()
nat, cl, bc = m["national"], m["client"], m["business_case"]
sc = bc["scenarios"]
pilot, broad = sc["targeted_pilot"], sc["broad_all"]
kn = m["known_numbers"]

page("Readmission penalties: where they come from and what a follow-up program can recover",
     "What decision is this analysis for, and what does the VP of Quality need to know first?")

md(
    f"""
**The decision.** The VP of Quality of a multi-hospital group (with the CFO) has to decide, before the next
budget cycle, whether to fund a post-discharge follow-up program, and at which hospitals and for which conditions.
**What this analysis does.** It uses CMS's public data on {m['data']['hrrp_hospitals']:,} hospitals to show which
hospitals and conditions drive the group's Medicare readmission penalties, how each hospital compares with similar
hospitals, how much is at stake each year, and under which assumptions a follow-up program pays for itself.
"""
)

be = bc["break_even"]
v27 = (m.get("validation") or {}).get("client_cms_dollars_fy2027")
kpis([
    ("Hospitals penalized nationally (FY2026, our estimate)", f"{nat['hospitals_penalized']:,}",
     f"CMS actual: {kn['fy2026_hospitals_penalized']:,} · {pct(nat['share_penalized_of_scored'])} of scored hospitals"),
    ("Our group's estimated penalty (FY2026)", f"{money(cl['total_penalty'])}/yr",
     f"{cl['hospitals_penalized']} of {len(cl['facility_ids'])} penalized"
     + (f" · CMS's FY2027 cuts: about {money(v27)}" if v27 else "")),
    ("Carried by 2 hospitals", pct(cl["top2_share"]),
     " + ".join(hospital_names()[h['facility_id']] for h in cl["hospitals"][:2])),
    ("Best-placed pilot (base case)", f"${pilot['benefit_cost_ratio']:.2f} per $1",
     f"returned in avoided penalties; break-even needs about {pct(bc['pooled_break_even_reduction'])} fewer "
     "readmissions among enrolled patients"),
])

md("## Three things to know")
for i, f in enumerate(recommendations.findings(m), 1):
    md(f"{i}. {f}")

md("## Where our group's penalty comes from")
cp = table("mart_penalty_condition")
cp = cp[cp["facility_id"].isin(cl["facility_ids"])].rename(columns={"penalty_contribution_annual": "penalty"})
names = {k: short_name(v) for k, v in hospital_names().items()}
chart(charts.penalty_by_hospital(
    cp, names, f"Two hospitals carry {pct(cl['top2_share'])} of the group's estimated penalty",
    "Estimated HRRP penalty per year by hospital and condition, US$ (FY2026 program, illustrative 8-hospital NJ group)"),
    key="ov_pen")
show_data(cp.assign(hospital=cp["facility_id"].map(names))[["hospital", "condition_code", "penalty"]]
          .pivot_table(index="hospital", columns="condition_code", values="penalty", aggfunc="sum").round(0)
          .reset_index())

md("## How the app is organised")
md(
    """
| Page | Question it answers |
|---|---|
| 2 · Data & Sanity Checks | Can we trust these numbers? What is missing, and how did we check it? |
| 3 · National Picture | Which conditions, states and types of hospital have the most excess readmissions and penalties? |
| 4 · Hospital Benchmarking | How does one of our hospitals compare with similar hospitals, condition by condition? |
| 5 · Penalty Exposure | How much does each hospital lose, which conditions drive it, and what if scores improved? |
| 6 · Intervention Business Case | Does a post-discharge follow-up program pay back, when, and under which assumptions? |
| 7 · Recommendations | Who should do what, what impact to expect, how to measure it, and the risks |
"""
)

how_to_read(
    f"""
- **Readmission** = a patient comes back to any hospital within 30 days of discharge. Medicare's Hospital
  Readmissions Reduction Program (HRRP) tracks six conditions: heart failure, pneumonia, COPD, heart attack,
  bypass surgery and hip/knee replacement.
- **Excess readmission ratio (ERR)** = a hospital's readmission rate divided by the rate an average hospital would
  have with the same patients. 1.00 = as expected; 1.05 = 5% more readmissions than expected.
- **Penalty** = if a hospital's ERR for a condition is above the typical hospital's (the median), Medicare cuts *all*
  of its regular Medicare inpatient payments for the year by a small percentage (at most 3%). This app turns that
  percentage into dollars.
- **Estimates, not invoices.** CMS does not publish penalty dollars by hospital. We rebuild them from the public
  scores with CMS's own formula. Checked against CMS's actual FY2026 decisions, we classify
  {pct((m.get('validation') or {}).get('agreement'), 0)} of hospitals the same way (page 2).
- **"Our group"** is an illustrative set of 8 New Jersey hospitals drawn by a fixed rule, not a real health system.
  Every page can be switched to any hospital.
"""
)
