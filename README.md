# Hospital Readmission Penalties: Benchmarking & Business Case

Which hospitals and conditions drive Medicare's readmission penalties, how a hospital compares with similar hospitals, and whether a post-discharge follow-up program pays for itself. Built on CMS public data for 3,055 US hospitals (FY2026 Hospital Readmissions Reduction Program, discharges July 2021 – June 2024), with SQL (DuckDB), Python and a Streamlit dashboard.

**Role played:** healthcare analyst reporting to the VP of Quality of a multi-hospital group. **Deliverables:** a 7-page [Streamlit app](dashboard/app.py), a standalone [HTML report](reports/report.html), a [one-page memo](docs/readout.md), and the [business case](docs/business_case.md), [benchmarking](docs/benchmarking.md), [metric definitions](docs/02_metric_definitions.md), [assumptions log](docs/assumptions.md) and [data-quality checks](docs/03_data_quality_checks.md) a hospital analytics team would produce.

![Dashboard overview](docs/img/01_overview.png)

## The business problem

> *"Several of our hospitals are about to be hit with CMS readmission penalties again. Which hospitals and which conditions are dragging us down? Where do we fall short compared with similar hospitals? If we invest in a post-discharge follow-up program, how much could we recover?"* (VP of Quality)

**Decision:** whether to fund a post-discharge follow-up program, and if so where, before the next budget cycle. The analysis uses CMS's public data to show which hospitals and conditions drive the group's penalties, how each hospital compares with peers, how much is at stake each year, and under which assumptions a program pays for itself. CMS data has no health-system membership, so "our group" is an **illustrative group of 8 New Jersey hospitals** drawn by a fixed, seeded rule. It is not an actual health system.

## Three findings

1. **The penalty is concentrated.** The group loses an estimated **$1.2M a year**; **two hospitals carry 62%**. Heart failure ($511K) and hip/knee replacement ($327K) are the largest drivers. Nationally we estimate **2,336 hospitals penalized** (CMS's actual count: 2,304) and **$296M a year** in penalties. The top 10% of hospitals carry 55%. Heart failure and pneumonia produce 74% of excess readmissions, while bypass and hip/knee surgery generate 29% of penalty dollars from 13% of discharges: CMS charges about **$217K per extra hip/knee readmission vs $42K for heart failure**.
2. **The gaps are hospital- and condition-specific.** **7 of 8** client hospitals readmit more than their typical peer (same ownership and Medicare volume), and **5 sit in the worst fifth**. Heart failure at three hospitals is worse than 90%+ of peers, and one hospital's hip/knee ratio (1.38) is worse than 99% of peers.
3. **A follow-up program would not pay for itself through penalties.** Group-wide it would cost about **$1.1M a year** and avoid about **$0.29M** in penalties once fully counted (FY2031): **$0.19 per $1**. At the two best-placed hospitals it returns **$0.75 per $1**. It breaks even only with a **≥14%** readmission reduction (recent trials: about 10%), a cost **≤ $236 per patient**, or about **30% of payer savings shared back**. Penalties are also a moving target: CMS's FY2027 cuts kept only about **58%** of each hospital's FY2026 cut.

## Recommendations

| Who | What | Expected impact | How we measure it | Risk |
|---|---|---|---|---|
| VP of Quality, CFO | Don't fund a group-wide program on financial grounds | Avoids ~$1.1M/yr of spend for ~$0.29M/yr of penalty relief | Revisit after the pilot | Fewer patients helped this year |
| CNOs at Inspira Mullica Hill and Palisades | 12-month pilot for higher-risk heart failure and pneumonia patients: medication review, nurse contact ≤72 h, clinic visit ≤7 days (not phone-only) | ~7 fewer readmissions/yr; ~$110K/yr less penalty once fully counted; cost ~$130K/yr | Enrolled vs similar non-enrolled patients, monthly; expand only at ≥14% reduction or ≤$236/patient | Effects shrink outside trials; CMS scores lag two years |
| CFO, managed-care contracting | Ask Medicare Advantage plans and the ACO to share savings | Pilot breaks even at 30% shared back | Terms signed before launch | Plans may decline |
| Orthopedics chair | Review recent hip/knee readmissions at Princeton (Plainsboro) before spending | Protects ~$250K/yr of estimated exposure | Quarterly case review; re-check with FY2027 data | Problem may already be easing (FY2027 cut fell to 0.04%) |
| Quality analytics | Track readmissions monthly; refresh when CMS posts FY2027 data (early 2027) | Early warning; FY2030 adds sepsis | Monthly dashboard | Rule changes break year-to-year comparability |

## The dashboard

`streamlit run dashboard/app.py`. The pages follow the storyline. Each opens with the question it answers and ends with a plain-language "How to read this". Pages 4–6 recalculate live as you change the peer definition, assumptions or program design.

| | |
|---|---|
| **2 · Data & Sanity Checks:** join funnel, missing-value reasons, 37 automated checks, validation against CMS's actual penalties, measured shrinkage ![](docs/img/02_data_checks.png) | **3 · National Picture:** state tile map, condition mix, segments with 95% intervals, concentration, adjusted associations ![](docs/img/03_national.png) |
| **4 · Hospital Benchmarking:** any hospital vs peers you define, by condition ![](docs/img/04_benchmarking.png) | **5 · Penalty Exposure:** dollars by hospital and condition, threshold heatmap, what-if, volatility ![](docs/img/05_penalty.png) |
| **6 · Intervention Business Case:** presets and sliders, waterfall, year-by-year cash, tornado, break-even map, Monte Carlo ![](docs/img/06_business_case.png) | **7 · Recommendations:** owner, impact, measure, risk; evaluation design; limitations ![](docs/img/07_recommendations.png) |

## How the numbers were built

- **Data.** Three CMS Care Compare files joined on the CMS Certification Number: the HRRP file (18,330 rows = 3,055 hospitals × 6 conditions), Medicare Spending per Beneficiary (CY2024) and Hospital General Information. SQL models (`sql/01–09`, DuckDB) land, type and join them. Every blank value carries a reason (CMS footnote or small-cell suppression). **30 checks pass, 7 are documented warnings, 0 fail** ([details](docs/03_data_quality_checks.md)).
- **Penalty estimate.** CMS's payment formula: 0.9627 × Σ condition payments × max(ERR − threshold, 0), capped at 3%. The threshold is the national median ERR, standing in for CMS's dual-eligible peer groups. Payment per case comes from FY2026 IPPS rates and CMS's published cohort payment ratios. Implemented in SQL and in Python, and the two agree to the cent. **Validated against CMS's actual FY2026 decisions:** the same penalized / not-penalized call for **97.1%** of hospitals, and **r = 0.92** on the payment cut.
- **Shrinkage.** CMS's model pulls small hospitals toward average. We measured how much from the published data (R² ≥ 0.99): for heart failure, only about 20% of a real improvement reaches the score at 100 discharges, vs about 80% at 1,500. The business case gives small hospitals this partial credit.
- **Benchmarking and drivers.** Peers share ownership and HRRP volume band. Segment averages carry 95% intervals; a regression with hospital-clustered errors gives adjusted associations, not causes.
- **Business case.** Applies the FY2027 rules: a 2-year window, and Medicare Advantage patients counted in the score but not in the penalty base. The baseline forecasts regression to the mean. One consistent set of money flows covers payer, hospital and whole-system views. The program effect and cost are anchored on trials and economic reviews (Cochrane 2022, Leppin 2014, PACT-HF 2019, Nuckols 2017). Includes a ±30% sensitivity table, tornado, break-even map and a 2,000-run Monte Carlo with a fixed seed ([business case](docs/business_case.md), [assumptions](docs/assumptions.md)).

## Assumptions and limitations

- Hospital-level public data show **where** readmissions are high, not **why**; group differences are associations.
- Penalty dollars are estimates: exact payments are not public, and single-hospital dollars carry roughly ±30% uncertainty. The national total ($296M) sits below CMS's nearest published totals ($316M–$361M).
- A single national threshold overstates penalties at safety-net hospitals, because CMS compares them with peers serving more low-income patients.
- Scores are from the FY2026 program; FY2027 (in effect now) counts Medicare Advantage patients over two years. Refresh when CMS posts FY2027 hospital data.
- Program effects come from trials and usually shrink in practice; the base case uses the conservative recent-trial estimate.

## How to run

Requires Python 3.12 and the three CMS CSV extracts (CMS Provider Data Catalog: *Hospital Readmissions Reduction Program* (dataset 9n3s-kdb3), *Medicare Spending Per Beneficiary – Hospital*, *Hospital General Information*). Raw data are never committed.

```bash
git clone https://github.com/edwinzhang98/healthcare-cost-analysis.git
```
```bash
cd healthcare-cost-analysis && uv venv --python 3.12 && uv pip install -r requirements.txt
```
```bash
.venv/bin/python run.py
```
```bash
.venv/bin/streamlit run dashboard/app.py
```

- **Data location:** `config.yaml` → `data.raw_dir` (default `~/projects/data-projects/datasets/p4-cms-2025`). To change it without editing the file, copy `.env.example` to `.env` and set `CMS_RAW_DIR`.
- `python run.py` runs everything in about 20 seconds: SQL models → cached tables (`data/processed/*.parquet`) → analysis (`reports/key_metrics.json`) → `reports/report.html` and `reports/memo.html` → executed notebooks exported to `reports/*.html`. Use `--skip-notebooks` for a faster run, or `make all` / `make quick`.
- **Optional external check** against CMS's actual penalties: `python run.py --validate` downloads CMS's FY2026/FY2027 penalty files to `data/external/`. These are used only for testing; summary results are committed in `reports/tables/`.
- Each SQL file runs on its own against the warehouse (`python -m src.sql_runner sql/05_fct_hospital_condition.sql`). Inputs and outputs are listed in each file's header.
- Screenshots: `uv pip install -r requirements-dev.txt && playwright install chromium && python scripts/screenshots.py`.

## Repository

```
sql/          DuckDB models: raw -> staging -> fact/dim -> penalty & segment marts -> data-quality checks
src/          config, SQL runner, penalty model, shrinkage, benchmarking, drivers, cost model, charts,
              analysis build, CMS validation, report and memo builders
dashboard/    Streamlit app (app.py + views/p1..p7)
notebooks/    01_data_quality, 02_analysis, 03_cost_model (executed, with outputs)
reports/      report.html, memo.html, notebook HTML exports, key_metrics.json, tables/
docs/         plan, request & scope, metric definitions, data-quality checks, assumptions,
              benchmarking, business case, readout memo, img/ (screenshots)
seeds/        condition parameters (labels, payment per case)
run.py        one-command pipeline       config.yaml  paths and every model parameter
```

## About this project

Independent portfolio project: an illustrative hospital group built from CMS public data, worked the way a hospital quality or healthcare consulting team would. All data are public; no patient-level data are used.
