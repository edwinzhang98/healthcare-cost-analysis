# 03 · Data quality and sanity checks

**What this is:** the record of what was checked in the CMS files before any number was used, what the checks found, and what changed because of them. The penalty estimates, benchmarks and business case all rest on these files.

**Scope:** three CMS Care Compare extracts for the FY2026 HRRP program (performance period 2021-07-01 to 2024-06-30), plus a test of the penalty method against CMS's actual FY2026 and FY2027 payment cuts.

**Status (build of 2026-11-03):** 37 automated checks: 30 PASS, 7 WARN, 0 FAIL. PASS means as expected. WARN means a known limitation, documented here. FAIL means the result must be investigated before any number is used. The pipeline records the status but does not stop on a FAIL, so the counts are shown on the dashboard's Data & Sanity Checks page and in notebook 01.

**Reproduce:** `python run.py` runs the 31 SQL checks in `sql/09_dq_checks.sql` and the 6 model checks (P1–P6) in `src/analysis.py`, and writes `data/processed/dq_checks_all.parquet`. The CMS comparison is optional (`python run.py --validate`, or `python -m src.validate_cms --download`) and writes `reports/tables/cms_validation_*.csv`.

---

## 1. Summary

The three files are complete, correctly keyed and internally consistent, and every missing value has a CMS reason. They are fit for ranking hospitals and conditions and for estimating HRRP penalties. The dollar figures carry three known biases, sized in Sections 10 and 13.

- **Complete.** The HRRP file has 18,330 rows: 3,055 hospitals × 6 conditions, with no duplicate keys and a single 36-month window. The spending (MSPB) and Hospital General Information files match their published sizes (4,626 and 5,419 rows).
- **Consistent.** The excess readmission ratio (ERR) equals predicted ÷ expected readmission rate on all 11,720 scored rows (largest difference 0.000065). No published readmission count is below 11, consistent with CMS hiding counts of 1–10.
- **Every blank explained.** 36% of hospital × condition rows have no ERR (CMS footnotes 1, 5 and 7). Of the 11,720 rows with an ERR, 3,683 (31%; 83% for hip/knee replacement) hide the discharge and readmission counts. We impute discharges for those rows.
- **Join.** 3,035 of 3,055 hospitals match the other two files. The 20 that do not are no longer listed by CMS. Four of them are now critical access hospitals under a new ID (exact name match).
- **Test against CMS's actual FY2026 penalties.** The method classifies 97.1% of 2,937 hospitals the same way as CMS (penalized or not). Estimated and actual payment cuts correlate at 0.92, and our ERRs are identical to CMS's. These CMS files are used only to test the method, with one disclosed exception (Section 10.1).
- **Known biases in the dollars.** (1) A single national penalty threshold over-flags hospitals with many dual-eligible patients. In CMS peer group 5, 61% of results are flagged against 54% penalized by CMS. For the illustrative client group, our FY2026 estimate (\$1.23M) is 19% above what CMS's actual cuts imply (\$1.04M). (2) Imputed discharge counts overstate hip/knee volume by a third, which adds about 3% to the national estimate. (3) Payment per discharge is a national average. Our national total (\$296M) is below the nearest CMS totals (\$316M and \$361M) because our payment base is smaller, not because the penalty rate differs. Payment level is also the one input that, raised 30%, brings the two-hospital targeted pilot to break-even.

---

## 2. Files and pipeline

**Table 1.** The three CMS files as landed. Rows = rows in the file; period = the data window the file describes.

| File | Grain | Rows | Period | Used for |
|---|---|---:|---|---|
| HRRP (`hrrp_readmissions.csv`) | hospital × HRRP condition | 18,330 (3,055 hospitals) | 2021-07-01 to 2024-06-30 | ERR, predicted and expected rates, eligible discharges, readmissions |
| Medicare Spending Per Beneficiary, MSPB-1 (`medicare_spending_per_beneficiary.csv`) | hospital | 4,626 | calendar 2024 | spending segment (descriptive only) |
| Hospital General Information (`hospital_general_information.csv`) | hospital | 5,419 | current snapshot | hospital type, ownership, emergency services, star rating; whether a hospital is still listed |

`sql/01_raw_load.sql` lands each file exactly as published, with every column as text. `sql/02`–`04` type the columns and label why each value is missing. `sql/05`–`08` build the hospital × condition fact table, the hospital dimension and the penalty marts. `sql/09_dq_checks.sql` then runs 31 checks on these tables, and `src/analysis.py` adds 6 checks that need the Python models (P1–P6). Raw files are read in place and never committed.

Five of the seven warnings (N2, N3, N4, J5, S1) are informational by design: they always report WARN so the number stays visible on every build. J1 and J2 warn because 20 hospitals do not join (Section 8).

The same results appear as charts on the dashboard's Data & Sanity Checks page and in `reports/01_data_quality.html`: the join funnel (hospitals at each step), reporting status by condition (share of hospitals), estimated vs actual FY2026 cut per hospital, and pass-through by volume.

---

## 3. Row counts

All three files landed with the expected number of rows (R1–R4).

**Table 2.** Row-count reconciliation. Unit: rows. Expected = the published dataset size recorded at download.

| File | Expected | Landed | How it reconciles |
|---|---:|---:|---|
| HRRP | 18,330 | 18,330 | 3,055 hospitals × 6 conditions, a complete grid (R4); the same size as CMS's published FY2026 file ([CMS Provider Data Catalog][pdc-hrrp]) |
| MSPB-1 | 4,626 | 4,626 | one row for each Hospital General Information facility of four types: 3,107 acute care + 1,382 critical access + 94 children's + 43 rural emergency hospitals[^types] |
| Hospital General Information | 5,419 | 5,419 | 3,107 acute care, 1,382 critical access, 624 psychiatric, 132 VA, 94 children's, 43 rural emergency, 32 Department of Defense and 5 long-term care facilities[^types] |

The expected counts are pinned in the checks. A refreshed CMS file will change them and turn R1–R3 to FAIL, which forces a review before new numbers are used.

---

## 4. Keys and identifiers

- **Unique keys.** (facility ID, condition) in HRRP and facility ID in MSPB and Hospital General Information have no duplicates (K1–K3).
- **Measures map cleanly.** All 18,330 HRRP measure names map to one of the six conditions (K4).
- **IDs are text.** Facility IDs are 6-digit CMS Certification Numbers (CCNs). They are read as text, so leading zeros survive (F1). Read as numbers, Alabama's 010008 would become 10008 and fail to join.
- **Right type of hospital.** Every HRRP ID ends in 0001–0899, the CCN range for short-term hospitals. No critical access (1300–1399) or other ranges outside the inpatient prospective payment system (IPPS) appear (F2) ([CMS State Operations Manual][som]).

---

## 5. Missing values: every blank has a reason

No HRRP value is missing without a CMS reason (N1: 0 unexplained rows). Coverage varies sharply by condition: 86–89% of hospitals have a heart failure or pneumonia ERR, but only 29% have a bypass surgery ERR.

**Table 3.** HRRP rows by reporting status and condition. Unit: hospital × condition rows. Scope: all 3,055 hospitals in the file, including Maryland and the 20 unmatched hospitals. Source: `reporting_status` in `data/processed/fct_hospital_condition.parquet`.[^status]

| What CMS published (`reporting_status`) | Footnote | Heart failure | Pneumonia | COPD | Heart attack (AMI) | Bypass (CABG) | Hip/knee | All |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| ERR, discharges and readmissions (`reported`) | blank or 29 | 2,316 | 2,320 | 1,545 | 1,240 | 363 | 253 | 8,037 |
| ERR only; readmissions were 1–10, so both counts are hidden (`counts_suppressed`) | blank or 29 | 305 | 395 | 778 | 496 | 515 | 1,194 | 3,683 |
| No ERR: fewer than 25 eligible discharges (`too_few_cases`) | 1 | 230 | 163 | 526 | 933 | 184 | 1,114 | 3,150 |
| No ERR: results not available (`not_available`) | 5 | 196 | 169 | 199 | 319 | 1,975 | 397 | 3,255 |
| No ERR: no cases met the criteria (`no_cases`) | 7 | 8 | 8 | 7 | 67 | 18 | 97 | 205 |
| **Total** | | 3,055 | 3,055 | 3,055 | 3,055 | 3,055 | 3,055 | 18,330 |
| Share of hospitals with an ERR | | 85.8% | 88.9% | 76.0% | 56.8% | 28.7% | 47.4% | 63.9% |
| Share of ERR rows with hidden counts | | 11.6% | 14.5% | 33.5% | 28.6% | 58.7% | 82.5% | 31.4% |

Footnote meanings, from CMS's [Footnote Crosswalk][footnotes]:

- **1**: number of cases too few to report. For HRRP this means fewer than 25 eligible discharges, the minimum for publishing results ([HRRP HSR User Guide][hsr-guide]).
- **5**: results not available for this reporting period. 1,975 of the 3,255 rows are bypass surgery.
- **7**: no cases met the criteria for this measure.
- **29**: calculated on partial performance-period data after a CMS-approved exception. 377 rows at 85 hospitals carry it. All have an ERR (239 reported, 138 with hidden counts), and they are used like any other row.
- **Hidden counts** (footnote blank or 29, readmissions shown as "Too Few to Report"): readmissions were 1–10, so CMS hides both readmissions and discharges but still publishes the ERR. This matches CMS's cell-size policy, which bars publishing any count of 1–10 or a value from which one could be derived ([ResDAC][resdac]).

**CMS's own file confirms the labels.** The FY2026 HRRP supplemental file ([CMS][supp-26]) is not suppressed, so it shows what lies behind each blank:[^cmsrows]

- For the 3,122 footnote-1 rows it covers, it records 1 to 24 eligible discharges, all below the 25-case minimum.
- For 2,777 of the 2,778 footnote-5 rows and all 199 footnote-7 rows it covers, the eligible-discharge field is empty. The remaining footnote-5 row shows 12 discharges. 1,869 of the empty rows are bypass surgery.
- None of these 6,099 rows carries a CMS penalty flag. Treating a row without an ERR as contributing no penalty therefore matches CMS.
- For 3,635 of the 3,683 rows with hidden counts, it gives the actual discharge count (25 to 637). The other 48 are 46 Maryland rows and 2 rows at a hospital that is not in CMS's file. Section 10.4 tests our imputation against these counts.

**How hidden discharges are filled.** CMS needs at least 25 discharges to publish an ERR. More than about 10 ÷ predicted rate discharges would usually have produced 11 or more readmissions. Each hidden count is therefore imputed at the midpoint of [25, ⌊10 ÷ predicted rate⌋] (`sql/05_fct_hospital_condition.sql`), and both ends are kept for sensitivity analysis. Imputed rows make up 9.7% of eligible discharges overall but 54.6% for hip/knee replacement, where readmissions are rare (median expected rate 5.4%).

---

## 6. Value ranges and internal consistency

The published fields agree with each other to rounding, and every value is in a plausible range (V1–V7).

**Table 4.** Range and consistency checks on the HRRP file. Scope: all rows where the field is published.

| Check | Result | What it tells us |
|---|---|---|
| ERR within 0.3–2.0 (V1) | 0.4698 to 1.6297 on 11,720 scored rows; 48.1% above 1.00 | no implausible values; ERR centers near 1.00 by design |
| Predicted and expected rates within 0–100% (V2) | 0 rows outside | rates are on the percent scale |
| ERR = predicted ÷ expected rate (V3) | largest difference 0.000065 | the three published fields follow CMS's definition ([HRRP HSR User Guide][hsr-guide]) |
| Smallest published discharge count where an ERR is shown (V4) | 27 | the 25-case minimum holds |
| Smallest published readmission count (V5) | 11 | counts of 1–10 are hidden, as the cell-size policy requires |
| Readmissions never exceed discharges (V6) | 0 rows | counts are coherent |
| Correlation of observed rate (readmissions ÷ discharges) with CMS's predicted rate (V7) | 0.861 on 8,037 rows with published counts, pooled across conditions | close but not exact, because CMS shrinks predicted rates toward the national average |

V7 matters for the business case. CMS's hierarchical model pulls low-volume hospitals toward the average ([COPSS-CMS white paper][copss]), so only part of an actual change in readmissions reaches the ERR. We measure this **pass-through** (the share of an actual change that reaches the CMS score) from the published rows. Fitting (predicted − expected) = n ÷ (n + k) × (observed − expected) by condition gives R² of 0.994 to 0.998 (`src/shrinkage.py`). At 100 eligible discharges over three years, 20–34% of an actual change reaches the ERR; at 1,500, 78–89%. Check P6 compares the fit with a published reliability study (Section 9).

---

## 7. Time windows

The HRRP data cover one 36-month window; the other files do not line up with it.

**Table 5.** Time window of each file and what follows from it.

| File | Window | Check | Consequence |
|---|---|---|---|
| HRRP | 2021-07-01 to 2024-06-30, the same on every row | T1 PASS | describes the FY2026 program, which cut payments for discharges from Oct 2025 to Sep 2026 ([FY2026 IPPS final rule][fr-2026]) |
| MSPB-1 | calendar 2024, the same on every row ([MSPB FAQ][mspb-faq]) | T2 PASS | overlaps the HRRP window for only 6 of its 36 months (Jan–Jun 2024) |
| Hospital General Information | current snapshot, no performance period | none | hospitals that closed or converted after the window drop out (Section 8) |
| CMS test files | FY2026 supplemental file and Table 15; FY2027 Table 15 | test only | FY2027 uses Jul 2023 to Jun 2025, adds Medicare Advantage patients and drops the COVID-19 exclusion ([FY2027 fact sheet][fact-27], [FY2026 IPPS final rule][fr-2026]); it shares 12 months with the FY2026 window |

**Spending is used only descriptively.** MSPB covers a different period, and its episodes include 30-day readmission spending ([MSPB measure information form][mspb-mif]), so it partly contains the outcome we study. It appears as a segment in the national picture and as one covariate in the association regression. It is never an input to the penalty estimate or the business case.

---

## 8. Joining the three files

3,035 of 3,055 HRRP hospitals (99.3%) join to both other files on CCN. The 20 that do not are no longer listed by CMS. At least four have become critical access hospitals, which HRRP does not cover ([42 U.S.C. 1395ww(q)][ssa-q]).

**Table 6.** Join funnel. Unit: hospitals. Scope: HRRP file joined to Hospital General Information and MSPB on CCN.

| Step | Hospitals | Removed | Why |
|---|---:|---:|---|
| In the HRRP file | 3,055 | | |
| Found in Hospital General Information and MSPB (J1, J2) | 3,035 | 20 | no longer listed by CMS (Table 7) |
| Payment-eligible (S2) | 2,992 | 43 | Maryland is exempt from HRRP payment cuts |
| With at least one ERR (S2) | 2,777 | 215 | no condition with a published ERR |
| Estimated penalized under FY2026 rules | 2,336 | 441 | no condition above the penalty threshold |

**Checks on the 3,035 matched hospitals:**

- All are "Acute Care Hospitals" in Hospital General Information (J3), as expected for a program that covers IPPS hospitals. Another 72 acute care hospitals in Hospital General Information have no HRRP rows and are outside the analysis.[^types]
- The state agrees for every one (J4).
- 52 have a different name in the two files (J5). Some are rebrands after an ownership or system change (for example, Tennova Healthcare-Clarksville is now Vanderbilt Clarksville Hospital). Others differ only in formatting: punctuation, legal suffixes or truncation. The CCN matches, so the current name is shown. None of the eight hospitals in the illustrative client group is affected.

**Table 7.** The 20 HRRP hospitals missing from Hospital General Information and MSPB. Scored conditions = conditions with a published ERR. Eligible discharges = Medicare fee-for-service discharges for the six conditions, Jul 2021 to Jun 2024, including imputed counts. CMS FY2026 cut = 1 − payment adjustment factor in CMS's FY2026 supplemental file; "not listed" = absent from that file.[^unmatched]

| CCN | Name in HRRP file | State | Scored conditions | Eligible discharges | CMS FY2026 cut | Finding |
|---|---|---|---:|---:|---:|---|
| 010008 | Crenshaw Community Hospital | AL | 1 | 50 | 0.04% | now a critical access hospital, CCN 011308 (exact name) |
| 010018 | Callahan Eye Hospital | AL | 0 | 0 | not listed | no match |
| 010059 | Lawrence Medical Center | AL | 1 | 43 | 0.24% | no match |
| 010120 | Monroe County Hospital | AL | 2 | 95 | 0.45% | no same-state match (the name exists in GA and IA) |
| 040067 | Magnolia Regional Medical Hospital | AR | 2 | 99 | 0.10% | no match |
| 050125 | Regional Medical Center of San Jose | CA | 5 | 1,166 | 2.18% | no match |
| 050589 | UCI Health - Placentia Linda | CA | 2 | 257 | 0.20% | no match |
| 070012 | Rockville General Hospital | CT | 0 | 0 | 0.00% | no match |
| 100047 | ShorePoint Health Punta Gorda | FL | 3 | 497 | 1.03% | no match |
| 100092 | Orlando Health Rockledge Hospital | FL | 5 | 818 | 0.23% | no match |
| 240052 | Lake Region Healthcare Corporation | MN | 3 | 258 | 1.24% | no match |
| 260176 | St Luke's Des Peres Hospital | MO | 3 | 282 | 1.41% | no match |
| 330060 | Carthage Area Hospital, Inc | NY | 0 | 0 | not listed | now critical access hospitals, CCNs 331318 and 331324 (exact name) |
| 390326 | St Luke's Hospital - Anderson Campus | PA | 4 | 1,344 | 0.11% | no match |
| 390337 | Geisinger Medical Center Muncy | PA | 2 | 86 | 0.31% | possibly UPMC Muncy, CCN 391301, a critical access hospital in Muncy, PA (name differs; not counted) |
| 450143 | Ascension Seton Smithville | TX | 0 | 0 | 0.00% | now a critical access hospital, CCN 671304 (exact name) |
| 450271 | Medical City Decatur | TX | 4 | 677 | 0.98% | no match |
| 450411 | Eastland Memorial Hospital | TX | 1 | 52 | 0.00% | now a critical access hospital, CCN 671303 (exact name) |
| 450827 | Kell West Regional Hospital | TX | 1 | 55 | 0.00% | no match |
| 520215 | Marshfield Medical Center - River Region | WI | 0 | 0 | 0.00% | no match |

What Table 7 shows:

- **Four confirmed conversions.** Crenshaw Community Hospital (AL, now 011308), Carthage Area Hospital (NY, now 331318 and 331324), Eastland Memorial Hospital (TX, now 671303) and Ascension Seton Smithville (TX, now 671304) reappear under the same name, in the same state, as critical access hospitals.[^names] Geisinger Medical Center Muncy may be a fifth, but the names differ, so it is not counted.
- **The other 15 are unverified.** None has a same-state name match. They are most likely closures, mergers into another CCN or conversions under a new name. We did not check them one by one.
- **Their status changed recently.** 18 of the 20 are still in CMS's FY2026 supplemental file, which excludes closed hospitals and was published with the FY2026 final rule in August 2025. CMS cut payments at 13 of them in FY2026.
- **Treatment.** They are treated as not payment-eligible, because they are not active IPPS hospitals going forward. Together they hold 39 scored results (0.3% of 11,720), and none is in the client group. The cost of this choice shows up in the FY2026 test: these 13 hospitals are half of our false negatives (Section 10.3).

**Maryland.** The file has 43 Maryland hospitals (258 rows, 195 with an ERR). Maryland hospitals receive ERRs and are publicly reported, but they get no HRRP payment cut; CMS Table 15 lists none of them ([CMS Table 15, FY2026][t15-26]). They are flagged (S1) and stay in the hospital and condition tables, but they are excluded from the penalty threshold, every peer set and segment statistic, and all penalty totals.

**MSPB coverage.** All 3,035 matched hospitals are in the MSPB file, and 2,872 have a score (N4). The 163 without a score carry CMS footnotes: 5 (78 hospitals), 1 (58), "1, 29" (14) and 19 (13). Footnote 19 means results are shown only for hospitals in CMS's inpatient and outpatient quality reporting programs. Among the 2,777 payment-eligible hospitals with an ERR, 2,751 (99.1%) have a score. Those hospitals, with 11,415 hospital × condition rows, are the sample for the association regression.[^mspb]

---

## 9. Checks against published numbers

Where CMS has published a comparable figure, our estimate lands close to it. The national dollar total is lower, and the gap traces to the payment base, not the penalty rate.

**Table 8.** Our FY2026 estimates against published CMS figures. Scope: payment-eligible hospitals, FY2026 program year unless stated.

| Measure | Our estimate | Published reference | Read |
|---|---|---|---|
| National median ERR per condition (V8) | 0.991 to 1.0008 | about 1.00 by construction ([HRRP HSR User Guide][hsr-guide]) | PASS |
| Hospitals penalized (P2) | 2,336 | 2,304 ([CMS Table 15, FY2026][t15-26]) | +1.4%; PASS (band ±5%, 2,189 to 2,419) |
| Hospitals with at least one scored condition | 2,777 | 2,797 penalty-eligible ([FY2026 IPPS final rule][fr-2026]) | reconciles hospital by hospital[^elig] |
| Share of scored hospitals penalized | 84.1% | 82.4% ([FY2026 IPPS final rule][fr-2026]) | close |
| Aggregate penalty ÷ base operating DRG payments | 0.44% | 0.44% ([FY2026 IPPS final rule][fr-2026]) | same[^base] |
| National penalty, \$ per year (P3) | \$296M | no FY2026 total published; nearest CMS totals are \$316M (FY2025 method, in the FY2026 rule) and \$361M (FY2027 rule) ([FY2026 rule][fr-2026], [FY2027 rule][fr-2027]) | 6% to 18% lower; PASS (coarse) |
| Heart failure pass-through at 1,019 eligible discharges (P6) | 0.73 | heart failure reaches 0.70 reliability at about 1,019 cases ([Thompson et al. 2016][thompson]) | PASS |
| SQL vs Python penalty, largest difference per hospital (P1) | \$0.000000 | identical by design | PASS |
| Client-group draw with seed 42 (P4) | reproduces the 8 IDs in `config.yaml` | not applicable | PASS |
| Monte Carlo, 2,000 runs, rerun with seed 42 (P5) | identical results | not applicable | PASS |

Notes on Table 8:

- **Dollar total.** P3 is a coarse check: it passes anywhere from \$190M to \$506M (0.6 × \$316M to 1.4 × \$361M). The rate is the more useful comparison. Our aggregate penalty is 0.44% of our estimated base operating payments, the same share CMS reports. The shortfall is in the base. Our implied base operating DRG payments total \$66.9B, against about \$86.7B in an approximation we built from CMS's FY2026 IPPS impact file ([CMS impact file][impact]; not a CMS figure). The median hospital is about \$16M in both, so the gap sits in larger hospitals. The sensitivity analysis varies payment per discharge ±30%, which gives \$207M to \$385M nationally.
- **Pass-through against reliability.** n ÷ (n + k) has the same form as a reliability coefficient, so the two can be compared directly. The match holds for heart failure only. At Thompson's volumes for the other conditions our fitted pass-through is lower (Section 13, risk 3).
- **Two implementations.** The SQL mart (`sql/07_mart_penalty_estimate.sql`) is the base case; `src/penalty.py` recomputes the same formula for what-if scenarios. P1 shows they agree to the cent for every hospital.

---

## 10. External validation against CMS's actual FY2026 results

### 10.1 What was compared, and what is independent

CMS publishes two kinds of files that our model never sees. Table 15 gives each hospital's actual payment adjustment factor ([FY2026][t15-26], [FY2027][t15-27]). The FY2026 supplemental data file ([CMS][supp-26]) adds each hospital's dual-eligible peer group, the peer-group median ERRs, unsuppressed discharge counts, CMS's penalty flags and the DRG payment ratios. `src/validate_cms.py` downloads them to `data/external/` (not committed) and compares them with our estimates.

**They are used only to test the method.** No hospital-level value from these files (peer group, peer median, discharge count, penalty flag, payment factor) enters the model.

**One exception comes from the same CMS release.** The six relative payment weights by condition (`payment_rel_to_hf` in `seeds/condition_params.csv`, which sets `base_payment_per_discharge`) are CMS's median within-hospital payment per case relative to heart failure, computed from the supplemental file's DRG payment ratios (`reports/tables/cms_payment_weights.csv`). Two national constants also come from that release: the neutrality modifier (0.9627) and the median share of base operating payments from the six conditions (0.133), which is used only for the 3% cap and to express the cut as a percentage. These are national numbers, not any hospital's answer. Still, they make the cut correlation in Table 9 partly in-sample. The penalized-or-not agreement and the ERR identity are fully independent of them, because neither depends on payment.

### 10.2 Headline agreement

**Table 9.** Our FY2026 estimate against CMS's actual FY2026 results. Scope: the 2,937 hospitals in both our HRRP file and CMS's supplemental file. Cut = percentage reduction of Medicare fee-for-service base operating DRG payments. Source: `reports/tables/cms_validation_summary.csv`.

| Measure | Ours | CMS | Note |
|---|---:|---:|---|
| Hospitals compared | 2,937 | 2,945 in CMS's file | CMS's file excludes Maryland and closed hospitals; 8 of its hospitals are not in the Care Compare extract |
| Hospitals penalized | 2,336 | 2,302 | CMS's full count is 2,304 |
| Same classification, penalized or not | 97.1% | | 2,276 penalized by both, 575 by neither, 60 only by us, 26 only by CMS |
| Correlation of payment cut, Pearson / Spearman | 0.92 / 0.94 | | per hospital, including hospitals with no cut |
| Mean cut among penalized hospitals | 0.46% | 0.44% | each side's own penalized hospitals |
| Median cut among penalized hospitals | 0.34% | 0.30% | |
| Hospitals at the 3% cap | 10 | 15 | |
| ERR, largest absolute difference | 0.0000 | | 11,523 hospital × condition rows at 2,791 hospitals; the Care Compare ERRs are CMS's |
| Condition flag agreement | 96.8% | | above our threshold vs CMS penalty indicator, 11,484 hospital × condition results |
| Neutrality modifier | 0.9627 (input) | 0.9627 | taken from CMS's FY2026 release |
| Median sum of the six DRG payment ratios | 0.133 (input) | 0.1329 | taken from the same file; used only for the 3% cap and the percentage |

### 10.3 Where the misses come from

Apart from hospitals that have left the program, the misses sit near the threshold and involve cuts of 0.15% or less.[^conf]

- **False negatives (26: CMS penalized, we did not).** 13 are hospitals we treat as not payment-eligible because they are missing from current Hospital General Information (Table 7); CMS cut them by 0.04% to 2.18%. The other 13 are in peer groups 1–3, where our threshold sits slightly above CMS's. Their CMS cuts are all 0.06% or less.
- **False positives (60: we penalized, CMS did not).** 40 are in peer group 5 (Section 10.5). 55 of the 60 have an estimated cut below 0.10%, and the largest is 0.15%.
- Leaving out the 18 unmatched hospitals that CMS still listed, agreement is 97.5% (2,919 hospitals).

### 10.4 Hidden discharge counts

The midpoint imputation is close overall (+9%) but biased by condition.

**Table 10.** Imputed vs actual discharges for rows where Care Compare hides the counts. Unit: Medicare fee-for-service eligible discharges, Jul 2021 to Jun 2024, summed over rows. Scope: the 3,635 hidden-count rows that CMS's supplemental file covers. Range = [25, ⌊10 ÷ predicted rate⌋]. Source: `reports/tables/cms_validation_imputation.csv`.

| Condition | Rows | CMS actual | Our midpoint | Estimate ÷ actual | Median per row, actual / ours | Actual inside our range |
|---|---:|---:|---:|---:|---|---:|
| Heart failure | 303 | 13,649 | 12,329 | 0.90 | 41 / 41 | 79% |
| Pneumonia | 391 | 23,152 | 19,299 | 0.83 | 55 / 49 | 72% |
| COPD | 774 | 35,296 | 33,055 | 0.94 | 41 / 43 | 80% |
| Heart attack (AMI) | 488 | 27,735 | 25,312 | 0.91 | 50 / 52 | 82% |
| Bypass (CABG) | 511 | 31,969 | 31,282 | 0.98 | 57 / 61 | 91% |
| Hip/knee replacement | 1,168 | 95,244 | 126,289 | 1.33 | 59 / 104 | 96% |
| **All** | **3,635** | **227,045** | **247,566** | **1.09** | | **86%** |

- **Direction.** The midpoint overstates hip/knee replacement by 33%: actual counts cluster near the low end of the range (median 59 against our 104). It understates pneumonia by 17% and the other medical conditions by 6% to 10%.
- **Range misses.** 86% of actual counts fall inside our range. All 496 misses lie above the upper bound, and 99.8% of those rows have an ERR below 1.00. The upper bound uses CMS's predicted rate, which is shrunk toward the national average. A hospital whose actual rate is below its predicted rate can have more than 10 ÷ predicted rate discharges and still fewer than 11 readmissions.[^impute]
- **Effect on dollars (test only).** Replacing our imputed counts with CMS's actual counts lowers the national estimate from \$296.1M to \$287.7M (−2.8%). Hip/knee falls from \$46.9M to \$39.7M (−15%), bypass by 2.7%, and the other conditions by 0.5% or less. The client group falls from \$1.231M to \$1.201M (−2.5%). Which hospitals are penalized does not change, because discharges do not enter the penalized-or-not test.

### 10.5 Penalty threshold: national median vs CMS peer groups

CMS compares each hospital with the median ERR of its peer group: one of five equal-sized groups ranked by the share of patients who are dually eligible for Medicare and Medicaid ([CMS supplemental file][supp-26]). Care Compare does not include peer groups, so our **penalty threshold** is the national median ERR per condition among payment-eligible hospitals.

**Table 11.** Penalty threshold by condition: CMS peer-group medians vs the national median we use. Unit: ERR. Peer group 1 = fewest dual-eligible patients, 5 = most. Source: `reports/tables/cms_validation_thresholds.csv`.

| Condition | Group 1 | Group 2 | Group 3 | Group 4 | Group 5 | National median (ours) |
|---|---:|---:|---:|---:|---:|---:|
| Heart failure | 0.9929 | 0.9922 | 0.9949 | 1.0005 | 1.0164 | 0.9989 |
| Pneumonia | 0.9908 | 0.9892 | 0.9932 | 0.9957 | 1.0101 | 0.9957 |
| COPD | 0.9965 | 0.9965 | 0.9935 | 0.9962 | 1.0020 | 0.9969 |
| Heart attack (AMI) | 0.9961 | 0.9964 | 0.9953 | 0.9970 | 1.0018 | 0.9994 |
| Bypass (CABG) | 0.9964 | 1.0008 | 0.9934 | 1.0091 | 0.9991 | 1.0008 |
| Hip/knee replacement | 0.9939 | 0.9918 | 0.9907 | 0.9954 | 0.9905 | 0.9910 |

For the four medical conditions, the group 5 median is the highest of the five, 0.002 to 0.018 above our threshold. We therefore flag high-dual hospitals that CMS does not, and miss a few small excesses in groups 1–3.

**Table 12.** Flag rates and payment cuts by CMS peer group. "Results" are hospital × condition rows with an ERR at payment-eligible hospitals; mean cuts are over all hospitals in the group, including those with no cut. Source: `reports/tables/cms_validation_peer_groups.csv` and `data/processed/cms_validation_hospital.parquet`.[^pgcut]

| CMS peer group | Hospitals | Results | Our share above threshold | CMS share penalized | Our mean cut | CMS mean cut |
|---|---:|---:|---:|---:|---:|---:|
| 1 (fewest dual-eligible) | 588 | 2,107 | 46.4% | 48.3% | 0.33% | 0.35% |
| 2 | 588 | 2,527 | 47.2% | 49.6% | 0.34% | 0.37% |
| 3 | 589 | 2,482 | 45.7% | 48.8% | 0.34% | 0.34% |
| 4 | 587 | 2,301 | 50.5% | 50.5% | 0.36% | 0.33% |
| 5 (most dual-eligible) | 585 | 2,067 | 61.2% | 53.7% | 0.46% | 0.33% |

Group 5 is the one material miss: 61% of results flagged against 54% penalized, and a mean cut of 0.46% against 0.33%.

### 10.6 Illustrative client group

The illustrative client group is 8 New Jersey hospitals drawn by a seeded, size-stratified rule. It is not an actual health system. Our FY2026 estimate is higher than CMS's actual cut at all eight hospitals.

**Table 13.** Illustrative client group: estimated vs actual CMS payment cuts. Cut = percentage reduction of Medicare fee-for-service base operating DRG payments. HRRP volume band = eligible Medicare fee-for-service discharges for the six conditions over the 3-year window (Low < 400, Mid 400–999, High ≥ 1,000; not hospital size). The dollar row applies each cut to our estimated annual base operating payments for the same eight hospitals. Source: `reports/tables/cms_validation_client.csv`.[^client]

| Hospital (CCN) | HRRP volume band | CMS peer group | Our estimate, FY2026 | CMS actual, FY2026 | CMS actual, FY2027 |
|---|---|---:|---:|---:|---:|
| University Medical Center of Princeton at Plainsboro (310010) | High | 1 | 1.08% | 0.88% | 0.04% |
| Inspira Medical Center Mullica Hill (310069) | High | 3 | 0.91% | 0.87% | 0.23% |
| Ocean Medical Center (310052) | High | 1 | 0.22% | 0.21% | 0.02% |
| Palisades Medical Center (310003) | Mid | 5 | 0.82% | 0.61% | 1.19% |
| Jersey City Medical Center (310074) | Mid | 5 | 0.49% | 0.32% | 0.51% |
| Monmouth Medical Center (310075) | Mid | 2 | 0.40% | 0.30% | 0.07% |
| Virtua Willingboro Hospital (310061) | Low | 4 | 0.50% | 0.34% | 0.12% |
| The University Hospital (310119) | Low | 5 | 0.34% | 0.05% | 0.05% |
| **Group, \$ per year on our payment base** | | | **\$1.23M** | **\$1.04M** | **\$0.40M** |

- **Level.** On the same payment base, our FY2026 estimate (\$1.23M) is 19% above what CMS's actual cuts imply (\$1.04M). Three of the eight hospitals are in peer group 5, where the threshold bias is largest (Table 12).
- **Ranking.** The order of the eight hospitals is the same under both, except that the top two swap places. The top two carry 62% of the group's penalty in our estimate and 65% at CMS's cuts.
- **Next year.** CMS's FY2027 cuts fell at five hospitals, rose at two (Palisades and Jersey City) and were unchanged at one. On the same base the group total would be \$0.40M, about 38% of the FY2026 level.

### 10.7 Persistence from FY2026 to FY2027

Penalties regress toward the mean. CMS's Table 15 files for FY2026 and FY2027 (2,894 hospitals in both; `reports/tables/cms_validation_persistence.csv`) show:

- A hospital's FY2027 cut ≈ 0.58 × its FY2026 cut, plus a constant (slope 0.578; correlation 0.573).
- The top decile by FY2026 cut averaged 1.38% in FY2026 and 0.96% in FY2027. 40% of those hospitals lost more than half of their cut.
- 78.8% of hospitals were penalized in FY2026 and 70.5% in both years, so 89% of FY2026-penalized hospitals were penalized again.[^pers] Whether a hospital is penalized is sticky; the size of the cut is not.

This is consistent with published evidence that regression to the mean explains 74% to 87% of the ERR improvement at penalized hospitals ([Joshi et al. 2019][joshi]). The business case therefore uses **persistence** (the share of today's ERR excess expected to remain without a program) of 0.5 in its baseline, tested from 0.3 to 0.8. The 0.58 anchor is approximate: it is measured on payment cuts rather than ERRs, the two windows share 12 months of data, and FY2027 changed the rules (Medicare Advantage patients added, 2-year window, COVID-19 exclusion removed).

### 10.8 Reading CMS's supplemental file

CMS's supplemental file prints counts of 1,000 or more with a thousands separator (for example, "2,393"). `src/validate_cms.py` converts with `pd.to_numeric(errors="coerce")`, which turns those 193 hospital × condition counts into missing values. No result in Sections 10.2 to 10.7 uses them: the imputation test covers hidden counts, which never exceed 637. The one affected output is the payment-weight table. With the counts read correctly, the median relative payments would be AMI 1.571 instead of 1.542, CABG 3.618 instead of 3.625, COPD 0.886 instead of 0.890, hip/knee 1.408 instead of 1.415 and pneumonia 1.162 instead of 1.165, and each median would draw on 97 to 124 more hospitals. Re-running the penalty estimate with the corrected weights changes the national total by +0.03% (\$296.10M to \$296.19M) and the client group by +\$274. The number of penalized hospitals and hospitals at the cap does not change.[^parse]

---

## 11. Full automated check table

**Table 14.** All 37 automated checks from the 2026-11-03 build, as generated in `data/processed/dq_checks_all.parquet` (31 SQL checks from `sql/09_dq_checks.sql`; P1–P6 from `src/analysis.py`). Rows are grouped by category.

| ID | Status | Category | Check | Expected | Actual | Note |
|---|---|---|---|---|---|---|
| R1 | PASS | Row counts | HRRP rows match published file (18,330) | 18330 | 18330 | – |
| R2 | PASS | Row counts | MSPB rows match published file (4,626) | 4626 | 4626 | – |
| R3 | PASS | Row counts | Hospital General Information rows match published file (5,419) | 5419 | 5419 | – |
| R4 | PASS | Row counts | HRRP is a complete hospital x 6-condition grid | 18330 | 18330 | 3055 hospitals x 6 conditions |
| K1 | PASS | Primary key | HRRP (facility_id, condition) is unique | 0 duplicates | 0 duplicates | – |
| K2 | PASS | Primary key | MSPB facility_id is unique | 0 duplicates | 0 duplicates | – |
| K3 | PASS | Primary key | Hospital General Information facility_id is unique | 0 duplicates | 0 duplicates | – |
| K4 | PASS | Primary key | Every HRRP measure maps to one of the 6 conditions | 0 unmapped | 0 unmapped | – |
| F1 | PASS | Format | HRRP facility IDs are 6-digit CMS Certification Numbers | 0 malformed | 0 malformed | IDs are read as text to keep leading zeros |
| F2 | PASS | Format | HRRP IDs fall in the short-term hospital number range (last 4 digits 0001-0899) | 0 outside | 0 outside | – |
| N1 | PASS | Missing values | Every blank HRRP value has a known reason (footnote / suppression) | 0 unexplained | 0 unexplained | – |
| N2 | WARN | Missing values | Share of hospital x condition rows with a published ERR | info | 63.9% | 3150 too few cases (<25), 3255 not available, 205 no cases |
| N3 | WARN | Missing values | Rows with ERR but suppressed counts (discharges imputed) | info | 3683 rows | imputed discharges = 9.7% of eligible discharges (hip/knee and CABG most affected) |
| N4 | WARN | Missing values | MSPB score available for HRRP hospitals | info | 2872 of 3055 | missing scores carry CMS footnotes (e.g., too few cases, not available) |
| V1 | PASS | Value range | ERR within plausible range [0.3, 2.0] | 0 outside | 0 outside | min 0.4698, max 1.6297 |
| V2 | PASS | Value range | Predicted and expected rates between 0% and 100% | 0 outside | 0 outside | – |
| V3 | PASS | Consistency | ERR equals predicted / expected rate (rounding only) | max diff < 0.001 | max diff 6.5e-05 | – |
| V4 | PASS | Consistency | Published discharges are at least 25 wherever an ERR is shown | min >= 25 | min 27 | CMS publishes an ERR only with 25+ cases |
| V5 | PASS | Consistency | Published readmission counts are 11 or more (small cells hidden) | min >= 11 | min 11 | confirms counts of 1-10 are suppressed |
| V6 | PASS | Consistency | Readmissions never exceed discharges | 0 rows | 0 rows | – |
| V7 | PASS | Consistency | Observed rate tracks CMS predicted rate (correlation) | >= 0.80 | 0.861 | predicted rates are shrunk toward the average, so the match is not exact |
| P1 | PASS | Consistency | SQL and Python penalty models agree (max difference per hospital) | < \$1 | \$0.000000 | two independent implementations of the HRRP formula |
| T1 | PASS | Time range | HRRP performance period is 2021-07-01 to 2024-06-30 on every row | 1 period | 1 period(s): 2021-07-01 to 2024-06-30 | – |
| T2 | PASS | Time range | MSPB period is calendar 2024 on every row | 1 period | 1 period(s): 2024-01-01 to 2024-12-31 | note: MSPB year does not line up with the HRRP window (documented limitation) |
| J1 | WARN | Join | HRRP hospitals found in Hospital General Information | 3055 | 3035 | 20 not found: closed, merged or converted since the period (e.g., to critical access) |
| J2 | WARN | Join | HRRP hospitals found in MSPB file | 3055 | 3035 | same 20 hospitals as J1 |
| J3 | PASS | Join | Matched HRRP hospitals are all Acute Care Hospitals | 100% | 100.0% | HRRP applies to short-term acute care (IPPS) hospitals only |
| J4 | PASS | Join | State agrees between HRRP and Hospital General Information | 0 mismatches | 0 mismatches | – |
| J5 | WARN | Join | Hospital name differs between files (renamed since the period) | info | 52 hospitals | IDs match, so names are informational only; current name is shown |
| S1 | WARN | Scope | Maryland hospitals (exempt from HRRP payment cuts) flagged | info | 43 hospitals | kept for benchmarking, excluded from penalty totals |
| S2 | PASS | Scope | Payment-eligible hospitals in the analysis | info | 2992 hospitals (2777 with at least one ERR) | – |
| V8 | PASS | Known numbers | National median ERR per condition is close to 1.00 | all within 0.98-1.02 | range 0.991-1.0008 | ERR is built so that an average hospital scores about 1.00 |
| P2 | PASS | Known numbers | Estimated penalized hospitals vs CMS FY2026 (2,304) | within ±5% of 2,304 | 2,336 (+1.4%) | CMS Table 15 / FY2026 IPPS final rule impact analysis |
| P3 | PASS | Known numbers | Estimated national penalty \$ vs nearest CMS published totals (\$316M-\$361M) | same order of magnitude | \$296M | CMS did not publish an FY2026 dollar total; our payment assumptions are conservative (see assumptions A4) |
| P6 | PASS | Known numbers | Fitted shrinkage matches published measure reliability (HF pass-through at 1,019 cases ≈ 0.70) | 0.65-0.80 | 0.73 | Thompson et al. 2016: HF needs ~1,019 cases for 0.70 reliability |
| P4 | PASS | Reproducibility | Client group draw reproduces config.yaml (seed 42) | True | True | 8 hospitals, stratified by size |
| P5 | PASS | Reproducibility | Monte Carlo with fixed seed gives identical results on re-run | True | True | seed 42 |

---

## 12. Decisions taken because of these checks

- **IDs as text (F1, F2).** Facility IDs are read as 6-character text everywhere. As numbers, every CCN with a leading zero (all of Alabama, for example) would fail to join.
- **A reason code on every row (N1–N3).** Each HRRP row carries a `reporting_status`. Rows without an ERR contribute no penalty, as in CMS's own file. Rows with hidden counts keep their ERR, and their discharges are imputed.
- **Impute hidden discharges at the midpoint and keep the range (N3, V4, V5, Section 10.4).** The midpoint of [25, ⌊10 ÷ predicted rate⌋] is the base case, and the two ends feed the penalty sensitivity (\$275M to \$317M nationally). The CMS test showed hip/knee overstated by a third. We kept the rule and documented the bias rather than tune it to CMS's counts, which would turn a test file into an input.
- **Keep footnote-29 rows.** Their ERRs are valid; they were calculated on a partial period under a CMS-approved exception.
- **Exclude Maryland from all penalty math (S1).** Maryland hospitals stay in the tables but are left out of the threshold, peer sets, segment statistics and totals.
- **Treat the 20 unmatched hospitals as not payment-eligible (J1, J2).** This fits the forward-looking question: four are now critical access hospitals and none is listed as an acute care hospital. It costs 13 false negatives in the FY2026 test.
- **National median ERR as the penalty threshold, tested against 1.00 (V8, Section 10.5).** CMS's dual-eligible peer groups are not in Care Compare. The national medians are 0.991 to 1.0008; using 1.00 instead gives 2,308 penalized hospitals and \$285M. The peer group 5 over-flagging is disclosed rather than corrected, because peer groups cannot be rebuilt from these three files.
- **Spending as description only (T2).** MSPB stays out of the penalty estimate and the business case.
- **Measured pass-through instead of 100% (V7, P6).** In the business case, the ERR moves by n ÷ (n + k) of the modeled change in readmissions, with k fitted per condition.
- **Regression to the mean in the baseline (Section 10.7).** The business case assumes persistence of 0.5, tested from 0.3 to 0.8, anchored on CMS's FY2026 → FY2027 slope of 0.58. Pilot hospitals are ranked on the benefit-cost ratio of the penalty a heart failure and pneumonia program can address, not on last year's total penalty, which would favor hospitals at a temporary peak.
- **Payment weights from CMS's payment ratios (Section 10.1).** Relative payment per case by condition uses CMS's DRG payment ratios rather than DRG weights alone. The two differ most for AMI (1.54 vs 1.06 × heart failure) and bypass surgery (3.63 vs 4.50 ×).
- **CMS test files stay out of the model.** Apart from the six payment weights and two national constants, nothing from the supplemental file or Table 15 is a model input. The test runs only when the files are present, and its results are reported separately.
- **Pinned row counts and fixed seeds (R1–R3, P4, P5).** A CMS refresh fails R1–R3 and forces a review. The client-group draw and the Monte Carlo reproduce exactly.

---

## 13. Residual risks

Ordered by likely effect. Most of these move dollar figures by a few percent to about 20% without changing the business-case conclusion. The exception is the payment level (risk 2): it is the one ±30% input that brings the targeted pilot to break-even.

1. **Penalty threshold.** One national median per condition stands in for CMS's five dual-eligible peer-group medians. High-dual hospitals are over-flagged (peer group 5: 61% of results above our threshold against 54% penalized; mean cut 0.46% against 0.33%), and low-dual hospitals are slightly under-flagged. In the illustrative client group, three of eight hospitals are in peer group 5, including Palisades Medical Center, one of the two pilot sites (estimated 0.82% against CMS's 0.61%). The group total is \$1.23M estimated against \$1.04M at CMS's actual cuts. The ranking of the eight hospitals is unchanged apart from the top two swapping places.
2. **Payment per discharge and the payment base.** National average payments (heart failure \$8,523 at a wage index of 1.0, scaled by condition) stand in for hospital-specific payments. Total base payments are approximated as HRRP-condition payments ÷ 0.133. As a result, the national total is \$296M against CMS-adjacent totals of \$316M to \$361M, and 10 hospitals hit the 3% cap against 15. Varying payment ±30% gives \$207M to \$385M nationally. Our base looks too low rather than too high (\$66.9B against about \$86.7B). Part of that gap may come from the ÷ 0.133 step, which affects only the cap and the percentage. To the extent it comes from payment per discharge, the penalty a program can avoid is understated too. Payment level is also the one ±30% input that flips the sign of the pilot's hospital net: at +30% the pilot is about break-even (+\$66 a year; `data/processed/bc_sensitivity.parquet`). For the client group this bias partly offsets risk 1, where our cuts run 19% above CMS's.
3. **Pass-through outside heart failure.** Our fitted shrinkage matches Thompson et al. for heart failure (0.73 against 0.70). At Thompson's volumes for the other conditions, it implies lower pass-through: pneumonia 0.52, COPD 0.59, AMI 0.62, bypass 0.32 and hip/knee 0.05, against 0.70 for each. Thompson used older data, so we keep our own fit. The effect on the business case is small. With k set to match Thompson's volumes, the pilot's benefit-cost ratio is 0.72 instead of 0.75. Only 100% pass-through, which V7 rules out, lifts it above 1 (1.20).[^thom]
4. **Imputed hidden counts.** The midpoint overstates hip/knee discharges by a third and understates pneumonia by 17%. Measured with CMS's actual counts, the net effect is −2.8% on the national total, −15% on hip/knee and −2.5% for the client group. Which hospitals are penalized does not change.
5. **FY2026 data, FY2027+ rules.** The data are fee-for-service only, cover 3 years and exclude COVID-19 patients. From FY2027 the window is 2 years, Medicare Advantage patients count and the COVID-19 exclusion is gone. ERR levels, peer medians and shrinkage may all shift. The business case applies the new window and the Medicare Advantage share, but it reuses k fitted on FY2026 data.
6. **Persistence anchor.** The 0.58 slope is measured on payment cuts, not ERRs, across two windows that share 12 months and use different rules. It is a reasonable anchor, not a clean estimate, so the business case tests 0.3 to 0.8.
7. **Test not fully independent.** The six payment weights, the neutrality modifier and the 0.133 payment share come from the same CMS release used for testing, so the 0.92 cut correlation is partly in-sample. The 97.1% classification agreement and the ERR identity do not depend on them.
8. **Reading the supplemental file.** The validation script reads counts of 1,000 or more as missing (Section 10.8). This is immaterial today: correcting it moves the national total by 0.03%.
9. **Spending data.** MSPB covers 6 of the 36 months and includes readmission spending, so associations with spending are descriptive and partly circular. 26 scored payment-eligible hospitals have no MSPB score.
10. **Hospital status and file refreshes.** Twenty hospitals have already dropped out, and more may close or convert before FY2029. CMS also revises Care Compare files. All eight client hospitals are matched and none was renamed. R1–R3 fail on a refreshed file by design.

---

## Sources

- **CMS Provider Data Catalog**, FY 2026 Hospital Readmissions Reduction Program – Hospital file: [CSV][pdc-hrrp]
- **CMS Provider Data Catalog**, Footnote Crosswalk: [CSV][footnotes]
- **CMS/QualityNet**, FY 2026 HRRP Hospital-Specific Report User Guide (Aug 2025): [PDF][hsr-guide]
- **ResDAC**, CMS Cell Size Suppression Policy (version 01/26/2024): [web page][resdac]
- **CMS**, FY 2026 IPPS/LTCH PPS Final Rule HRRP Supplemental Data File: [ZIP][supp-26]
- **CMS**, Table 15: FY 2026 HRRP Payment Adjustment Factors: [ZIP][t15-26]
- **CMS**, Table 15: FY 2027 HRRP Payment Adjustment Factors (posted Oct 7, 2026): [ZIP][t15-27]
- **FY 2026 IPPS/LTCH PPS Final Rule**, 90 FR 36536 (Aug 4, 2025): [Federal Register][fr-2026]
- **FY 2027 IPPS/LTCH PPS Final Rule**, 91 FR 49570 (Aug 4, 2026): [Federal Register][fr-2027]
- **CMS**, Hospital Readmissions Reduction Program FY 2027 Fact Sheet: [PDF][fact-27]
- **42 U.S.C. 1395ww(q) and (d)(1)(B)**, US Code 2023 edition: [govinfo][ssa-q]
- **CMS State Operations Manual**, Chapter 2, §2779A1 (CCN ranges): [PDF][som]
- **CMS/QualityNet**, Hospital IQR Re-Evaluated MSPB Hospital Measure FAQs (Oct 2025): [PDF][mspb-faq]
- **CMS/QualityNet**, Hospital IQR Re-Evaluated MSPB Hospital Measure Information Form (Oct 2025): [PDF][mspb-mif]
- **CMS**, FY 2026 IPPS Final Rule Impact File (basis for the \$86.7B base-payment approximation; the approximation is ours, not CMS's): [ZIP][impact]
- **COPSS-CMS White Paper Committee**, Statistical Issues in Assessing Hospital Performance (2012): [PDF][copss]
- **Thompson MP et al.** Reliability of 30-Day Readmission Measures Used in the HRRP. *Health Serv Res* 2016;51(6):2095–2114: [PMC][thompson]
- **Joshi S et al.** Regression to the Mean in the Medicare HRRP. *JAMA Intern Med* 2019;179(9):1167–1173: [PMC][joshi]

[pdc-hrrp]: https://data.cms.gov/provider-data/sites/default/files/resources/a171bc36c488d3e0dc33ec63abb469a6_1770163617/FY_2026_Hospital_Readmissions_Reduction_Program_Hospital.csv
[footnotes]: https://data.cms.gov/provider-data/sites/default/files/resources/f29bb7c812e242f6edfef0a4b7d0eaca_1760630713/Footnote_Crosswalk.csv
[hsr-guide]: https://qualitynet.cms.gov/files/6893aac2728800f196e92cb1?filename=FY-2026-HRRP-HSR-User-Guide.pdf
[resdac]: https://resdac.org/articles/cms-cell-size-suppression-policy
[supp-26]: https://www.cms.gov/files/zip/fy2026-hospital-readmissions-reduction-program-supplemental-data-file.zip
[t15-26]: https://www.cms.gov/files/zip/fy-2026-hospital-readmissions-reduction-program-payment-adjustment-factors.zip
[t15-27]: https://www.cms.gov/files/zip/fy-2027-hospital-readmissions-reduction-program-payment-adjustment-factors.zip
[fr-2026]: https://www.govinfo.gov/content/pkg/FR-2025-08-04/html/2025-14681.htm
[fr-2027]: https://www.govinfo.gov/content/pkg/FR-2026-08-04/html/2026-15833.htm
[fact-27]: https://www.cms.gov/files/document/fy-2027-hrrp-fact-sheet-pdf.pdf
[ssa-q]: https://www.govinfo.gov/content/pkg/USCODE-2023-title42/html/USCODE-2023-title42-chap7-subchapXVIII-partE-sec1395ww.htm
[som]: https://www.cms.gov/Regulations-and-Guidance/Guidance/Manuals/downloads/som107c02.pdf
[mspb-faq]: https://qualitynet.cms.gov/files/68f92e7dec89ae1f61aa3566?filename=FY2026_HIQR_MSPB_FAQS.pdf
[mspb-mif]: https://qualitynet.cms.gov/files/68f92567ec89ae1f61aa31e8?filename=HIQR_MSBP_Hospital_MIF_2025.pdf
[impact]: https://www.cms.gov/files/zip/fy2026-ipps-fr-impact-file.zip
[copss]: https://www.cms.gov/medicare/quality-initiatives-patient-assessment-instruments/hospitalqualityinits/downloads/statistical-issues-in-assessing-hospital-performance.pdf
[thompson]: https://pmc.ncbi.nlm.nih.gov/articles/PMC5134200/
[joshi]: https://pmc.ncbi.nlm.nih.gov/articles/PMC6596330/

## Notes on numbers computed for this page

Numbers not in `reports/key_metrics.json` or the `reports/tables/` CSVs were computed from the cached tables, the raw CMS files and the CMS test files, as described below.

[^types]: Counted from the raw CSVs (folder set by `data.raw_dir` in `config.yaml`): MSPB facility IDs joined to Hospital General Information and tabulated by `Hospital Type`; acute care hospitals in Hospital General Information compared with `dim_hospital`.
[^status]: Cross-tabulation of `reporting_status` and `footnote` by `condition_code` in `data/processed/fct_hospital_condition.parquet`.
[^cmsrows]: Rows of `fct_hospital_condition` merged on CCN and condition with CMS's FY2026 supplemental file (read with `src.validate_cms`, thousands separators stripped), then counted by `reporting_status`, CMS eligible discharges and CMS penalty indicator. Covers hospitals present in both files.
[^unmatched]: Rows of `dim_hospital` with `in_hospital_info = False`; CMS cut = 1 − "Payment adjustment factor" in the supplemental file.
[^names]: Exact, case-insensitive comparison of each unmatched hospital's HRRP name with every facility name in the raw Hospital General Information file, kept only when the state matches. For the rest, a same-state search on distinctive words of the name. Hospital type of each match is from the same file.
[^mspb]: Raw MSPB file filtered to the 3,035 matched HRRP hospitals, with `Footnote` tabulated where `Score` is "Not Available". Regression sample from `national.regression.info` in `reports/key_metrics.json`.
[^elig]: Our 2,777 = 2,776 hospitals scored in both sources + Bronson South Haven Hospital (MI, 230085), which has two scored conditions in Care Compare but is absent from CMS's supplemental file. CMS's 2,797 = the same 2,776 + 15 of the 20 hospitals missing from Hospital General Information (CMS still listed them) + 6 hospitals in CMS's file that are not in the Care Compare extract (110153, 200041, 200052, 330211, 420117, 450498). CMS side = hospitals in the supplemental file with 25 or more eligible discharges in at least one measure, thousands separators stripped (Section 10.8).
[^base]: Sum and median of `est_total_base_payments_annual` over the 2,777 payment-eligible hospitals with an ERR (`data/processed/mart_penalty_hospital.parquet`); aggregate penalty = sum of `penalty_est_annual` ÷ that sum. The \$86.7B comparison was built during research from CMS's FY2026 IPPS impact file (transfer-adjusted cases × transfer-adjusted case-mix index × wage-adjusted standardized amount, 2,792 hospitals). It is not a CMS total.
[^conf]: `data/processed/cms_validation_hospital.parquet` joined to `dim_hospital`. False negatives are split by `in_hospital_info`; false positives are tabulated by `cms_peer_group` and by estimated cut. The 97.5% repeats the agreement calculation without the 18 unmatched hospitals.
[^impute]: Rows with `reporting_status = counts_suppressed` merged with CMS's counts; a miss is a CMS count outside [`discharges_est_low`, `discharges_est_high`]. Dollar effect: `src.penalty.estimate` rerun with `discharges_est` replaced by CMS's count on the 3,635 rows, everything else unchanged. This is a test only; the model still uses the imputed counts.
[^pgcut]: Mean of `payment_reduction_pct` (ours) and `cms_reduction_pct` by `cms_peer_group` in `data/processed/cms_validation_hospital.parquet`, over all hospitals in each group.
[^client]: Each hospital's estimated annual base operating payments = `penalty_est_annual` ÷ `our_estimated_reduction_fy2026` from `reports/tables/cms_validation_client.csv`. That base × CMS's FY2026 or FY2027 cut, summed over the eight hospitals, gives the dollar row. Peer groups are from the supplemental file. Ranking and top-two shares use the same figures.
[^pers]: 0.7046 ÷ 0.7878, both from `reports/tables/cms_validation_persistence.csv`.
[^thom]: Pass-through n ÷ (n + k) evaluated at Thompson et al.'s 0.70-reliability volumes (AMI 605, heart failure 1,019, pneumonia 442, COPD 559, bypass 107, hip/knee 9), with k from `shrinkage` in `reports/key_metrics.json`. Business-case effect: `src.cost_model.evaluate` for the targeted pilot at the two pilot hospitals (`src.analysis.pilot_hospitals()`), first with k set so that pass-through equals 0.70 at those volumes (k = 0.3 ÷ 0.7 × volume), then with `pass_through_mode = "full"`. All other parameters are at their base values; the base benefit-cost ratio of 0.75 is from `reports/key_metrics.json`.
[^parse]: Supplemental file re-read with separators stripped; medians recomputed with the rule in `src/validate_cms.py`; penalty rerun with heart failure \$8,523 × the corrected relative weights.
