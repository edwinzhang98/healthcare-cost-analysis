# 00 · Project plan (one page)

**Project:** HRRP readmission penalties: benchmarking, penalty exposure and a business case for post-discharge follow-up
**Role played:** Healthcare Analyst at a hospital group (or consulting analyst), reporting to the VP of Quality
**Direction:** **A, cost-benefit analysis at the hospital level** (prompt default). Why A: the CMS files are the newest (performance period to mid-2024, published 2025). The request is a hospital-group decision, which hospital-level data answers directly. And there is almost no public work translating HRRP results into dollars, peer benchmarks and an intervention business case. Direction B (patient-level BRFSS risk model) answers a different question, about population health outreach rather than penalties.

## Data (CMS Care Compare, read in place; never committed)
| File | Grain | Rows | Period | Used for |
|---|---|---|---|---|
| `hrrp_readmissions.csv` | hospital × 6 conditions | 18,330 (3,055 hospitals) | 2021-07 to 2024-06 (FY2026 program) | ERR, predicted/expected rates, discharges, readmissions |
| `medicare_spending_per_beneficiary.csv` | hospital | 4,626 | CY2024 | spending index (MSPB) as a segment |
| `hospital_general_information.csv` | hospital | 5,419 | 2025 release | ownership, type, emergency services, star rating |

Joined on Facility ID (CMS Certification Number): 3,035 of 3,055 HRRP hospitals match (`docs/03_data_quality_checks.md`).

## Analysis outline
1. **Scope and metric definitions first** (`01_`, `02_`): ERR, excess readmissions, penalty threshold, penalty dollars, MSPB.
2. **Data quality** (`03_`, notebook 01): row reconciliation, keys, suppression patterns, ranges, time windows, join funnel, comparison with published CMS totals.
3. **National picture and drivers** (notebook 02): excess readmissions and penalty dollars by condition, state, region, ownership, size, star rating and spending. Adjusted associations (regression with hospital-clustered errors), clearly labeled as associations rather than causes.
4. **Benchmarking** (`benchmarking.md`): target hospital vs peers with the same ownership and size, by condition, with percentiles.
5. **Penalty exposure:** the HRRP payment formula applied to each hospital (dollars per year, the 3% cap, distance to threshold), plus what-if ERR reductions.
6. **Business case** (`business_case.md`, notebook 03): program cost vs avoided penalties and readmission costs, from the hospital's and from Medicare's view. Includes a year-by-year phase-in (CMS's 3-year window delays penalty relief), break-even, ±30% sensitivity table, tornado chart, and a Monte Carlo run with a fixed seed.
7. **Deliverables:** Streamlit app (7 pages in storyline order), standalone `reports/report.html`, 1-page memo (`docs/readout.md`, `reports/memo.html`), README.

## "Our group": illustrative client group
CMS data has no system membership. Client group = **8 New Jersey hospitals**, drawn at random (seed 42) from payment-eligible NJ hospitals with ≥ 3 reported conditions, stratified 3 large / 3 medium / 2 small (`src/client.py`, `config.yaml`). NJ was chosen because it has the 2nd-highest average ERR among 51 states, and 93% of its hospitals are penalized, which is a realistic setting for the VP's problem. Massachusetts ranks 1st but has no small hospitals that qualify. **Not an actual health system.** The dashboard works for any hospital or group.

## Design decisions made from the data (details in `docs/assumptions.md`)
- **Suppressed counts:** CMS hides discharges when readmissions are 1-10 (3,683 rows; 55% of hip/knee volume). Discharges are imputed at the midpoint of the feasible range [25, 10 ÷ predicted rate], with low/high cases kept for sensitivity analysis.
- **Penalty threshold:** CMS compares each hospital with the median ERR of its dual-eligible peer group, which is not in our data. The national median ERR per condition is used instead, and tested against a threshold of 1.0.
- **Maryland** (43 hospitals) is exempt from HRRP payment cuts. It is kept for benchmarking but excluded from penalty totals.
- **Shrinkage:** CMS pulls small hospitals' scores toward average. Measured from the data, only ~20% of a real improvement reaches the score at 100 discharges, vs ~80% at 1,500. The business case uses this pass-through instead of assuming 100%.

## What we borrow vs what we add
- **Borrow:** the CMS/QualityNet HRRP methodology (payment formula, peer median, 25-case minimum, 3% cap). KFF's annual HRRP analyses, for the counting conventions (share of hospitals penalized, average penalty) and as published totals to check against. Academic HRRP literature (safety-net penalties, coding, mortality debates, small-hospital shrinkage) for the limitations section.
- **Add (what public analyses don't do):** penalty dollars per hospital and per condition, peer benchmarking for a chosen hospital, a business case with explicit assumptions and sensitivity, the timing lag created by the 3-year window, shrinkage-aware savings, and a memo for a non-technical audience.

## Risks and how they are handled
Penalty dollars depend on payment-per-discharge assumptions → every assumption is sourced, varied ±30%, and the national total is compared with CMS's published estimate. Hospital-level data cannot show causes → association language only. Intervention effects in trials shrink at scale → conservative base case, with break-even shown explicitly.
