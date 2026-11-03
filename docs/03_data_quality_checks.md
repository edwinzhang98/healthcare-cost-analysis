# 03 · Data quality and sanity checks

**What this is:** the checks run on the three CMS Care Compare extracts behind the FY2026 HRRP analysis (data from 2021-07-01 to 2024-06-30), what they found and changed, and a test of the penalty method against CMS's actual FY2026 and FY2027 payment cuts.

**Status (build of 2026-11-03):** 37 automated checks: 30 PASS, 7 WARN (known limitations, documented here), 0 FAIL (a FAIL is recorded, not enforced, and must be investigated). `python run.py` writes `data/processed/dq_checks_all.parquet`; `python run.py --validate` adds the CMS comparison (`reports/tables/cms_validation_*.csv`). Other numbers come from `data/processed/`, the raw files and the CMS test files, as noted where they appear.

## 1. Summary

The files are complete, correctly keyed and internally consistent, and every blank has a CMS reason. They are fit for ranking hospitals and conditions and for estimating HRRP penalties, with three known biases in the dollars.

- **Complete and consistent.** 18,330 HRRP rows (3,055 hospitals × 6 conditions), unique keys, one 36-month window; the other files match their published sizes. The excess readmission ratio (ERR) = predicted ÷ expected rate on all 11,720 scored rows.
- **Every blank explained.** 36% of rows have no ERR (CMS footnotes 1, 5, 7). 3,683 scored rows (31%; 83% for hip/knee) hide their counts; we impute their discharges.
- **Join.** 3,035 of 3,055 hospitals match. The other 20 are no longer listed by CMS; 4 are now critical access hospitals.
- **Validated against CMS's actual FY2026 penalties.** Same penalized-or-not call for 97.1% of 2,937 hospitals; payment cuts correlate at 0.92; our ERRs are identical to CMS's.
- **Known biases.** (1) The national threshold over-flags hospitals with many dual-eligible patients (CMS peer group 5: 61% of results flagged, 54% penalized); for the illustrative client group we estimate \$1.23M against \$1.04M at CMS's actual cuts (+19%). (2) Imputation overstates hip/knee discharges by a third (about +3% nationally). (3) Our national total (\$296M) is below CMS's nearest totals (\$316M, \$361M) because our payment base is smaller, not the rate; payment level is the one ±30% input that brings the two-hospital pilot to break-even.

## 2. Files and pipeline

**HRRP** (hospital × condition: ERR, predicted and expected rates, discharges, readmissions), **Medicare Spending Per Beneficiary, MSPB-1** (descriptive only) and **Hospital General Information** (type, ownership, star rating, still listed or not) are read in place, never committed. `sql/01`–`08` land them as text, label why values are missing and build the marts; `sql/09_dq_checks.sql` runs 31 checks, `src/analysis.py` 6 more (P1–P6). N2, N3, N4, J5 and S1 always report WARN so the number stays visible.

## 3. Row counts

All three files have their published row counts (R1–R4). The counts are pinned, so a CMS refresh fails R1–R3 and forces a review.

**Table 1.** Row-count reconciliation (expected = landed); hospital types counted from the raw files.

| File | Rows | How it reconciles |
|---|---:|---|
| HRRP | 18,330 | 3,055 hospitals × 6 conditions, a complete grid (R4); the size of CMS's published FY2026 file ([CMS Provider Data Catalog][pdc-hrrp]) |
| MSPB-1 | 4,626 | one row per Hospital General Information facility of four types: 3,107 acute care, 1,382 critical access, 94 children's, 43 rural emergency |
| Hospital General Information | 5,419 | those four types plus 624 psychiatric, 132 VA, 32 Department of Defense and 5 long-term care facilities |

## 4. Keys and identifiers

- Keys are unique: (facility ID, condition) in HRRP, facility ID in the other files (K1–K3). Every HRRP measure maps to one of the six conditions (K4).
- Facility IDs are 6-digit CMS Certification Numbers (CCNs), kept as text (F1): as numbers, Alabama's 010008 would become 10008 and fail to join.
- The last four digits give the facility type: 0001–0879 short-term hospitals, 0880–0899 reserved for hospitals in demonstration projects ([CMS State Operations Manual §2779A1][som]). HRRP IDs run from 0001 to 0893 (8 hospitals in 0880–0899); none is a critical access number (1300–1399) or another range outside the inpatient prospective payment system, IPPS (F2).

## 5. Missing values: every blank has a reason

No HRRP value is missing without a CMS reason (N1).

**Table 2.** HRRP rows by reporting status (footnote) and condition, all 3,055 hospitals; each column sums to 3,055. HF = heart failure, PN = pneumonia, AMI = heart attack, CABG = bypass surgery. Source: `data/processed/fct_hospital_condition.parquet`.

| `reporting_status` (footnote) | HF | PN | COPD | AMI | CABG | Hip/knee | All |
|---|---:|---:|---:|---:|---:|---:|---:|
| `reported` (blank, 29): ERR and counts | 2,316 | 2,320 | 1,545 | 1,240 | 363 | 253 | 8,037 |
| `counts_suppressed` (blank, 29): ERR only | 305 | 395 | 778 | 496 | 515 | 1,194 | 3,683 |
| `too_few_cases` (1): no ERR | 230 | 163 | 526 | 933 | 184 | 1,114 | 3,150 |
| `not_available` (5): no ERR | 196 | 169 | 199 | 319 | 1,975 | 397 | 3,255 |
| `no_cases` (7): no ERR | 8 | 8 | 7 | 67 | 18 | 97 | 205 |
| Share of hospitals with an ERR | 85.8% | 88.9% | 76.0% | 56.8% | 28.7% | 47.4% | 63.9% |
| Share of ERR rows with hidden counts | 11.6% | 14.5% | 33.5% | 28.6% | 58.7% | 82.5% | 31.4% |

**Footnote meanings** ([Footnote Crosswalk][footnotes]): **1** = too few cases (for HRRP, fewer than 25 eligible discharges, the minimum for publishing results; [HSR User Guide][hsr-guide]); **5** = results not available for this period; **7** = no cases met the criteria; **29** = partial-period data under a CMS-approved exception (377 rows at 85 hospitals, all with an ERR, used normally). **Hidden counts:** readmissions were 1–10, so CMS hides both counts but publishes the ERR; its cell-size policy bars any count of 1–10 or a value from which one could be derived ([ResDAC][resdac]).

**CMS's unsuppressed FY2026 supplemental file ([CMS][supp-26]) confirms the labels** (merged on CCN and condition). Its 3,122 footnote-1 rows record 1–24 eligible discharges. Of its 2,977 footnote-5 and footnote-7 rows, 2,976 have no discharge count (1,887 of them CABG: 1,869 with footnote 5, 18 with footnote 7) and one shows 12. None of these 6,099 rows has a CMS penalty flag, so "no ERR, no penalty" matches CMS. It also gives actual discharges for 3,635 of the 3,683 hidden-count rows (25–637); the other 48 are 46 Maryland rows and 2 at a hospital absent from CMS's file.

**Imputation.** An ERR needs 25+ discharges, and more than about 10 ÷ predicted rate discharges would usually yield 11+ readmissions, so each hidden count is imputed at the midpoint of [25, ⌊10 ÷ predicted rate⌋] (`sql/05`), ends kept for sensitivity. Imputed rows are 9.7% of eligible discharges overall and 54.6% for hip/knee, where readmissions are rare (median expected rate 5.4%). Section 10.4 tests this.

## 6. Value ranges and internal consistency

All fields are plausible and agree to rounding (V1–V7, Table 11): ERR runs from 0.4698 to 1.6297 (48.1% above 1.00); rates lie within 0–100%; ERR = predicted ÷ expected rate to within 0.000065 ([HSR User Guide][hsr-guide]); the smallest published discharge count is 27 and readmission count 11; readmissions never exceed discharges. The observed rate (readmissions ÷ discharges) correlates 0.861 with CMS's predicted rate (8,037 rows with counts), not 1, because CMS's hierarchical model shrinks low-volume hospitals toward the average ([COPSS-CMS white paper][copss]).

So only part of an actual change in readmissions reaches the ERR. We fit this **pass-through** per condition as (predicted − expected) = n ÷ (n + k) × (observed − expected), R² 0.994–0.998 (`src/shrinkage.py`), with n = eligible discharges in the 3-year fee-for-service data window: 20–34% at 100 discharges, 78–89% at 1,500. The business case applies k to FY2027+ cohort volume (fee-for-service discharges ÷ (1 − Medicare Advantage share) × 2 years): 0.673, 0.400 and 0.447 for its pilot rows (Inspira Mullica Hill heart failure; Palisades heart failure and pneumonia), against 0.645, 0.371 and 0.417 on the 3-year basis (`bc_rows_targeted_pilot.parquet`). P6 compares the fit with published reliability, which has the same n ÷ (n + k) form (Section 9).

## 7. Time windows

**Table 3.** Time window of each file. FY2026–FY2032 program-year windows are in [metric definitions](02_metric_definitions.md).

| File | Window | Check | Consequence |
|---|---|---|---|
| HRRP | 2021-07-01 to 2024-06-30 on every row | T1 PASS | sets the FY2026 cut, applied to discharges from Oct 2025 to Sep 2026 ([FY2026 IPPS final rule][fr-2026]) |
| MSPB-1 | calendar 2024 on every row ([MSPB FAQ][mspb-faq]) | T2 PASS | overlaps only 6 of the 36 HRRP months |
| Hospital General Information | current snapshot | – | hospitals that closed or converted since drop out (Section 8) |
| CMS test files | FY2026 supplemental file and Table 15; FY2027 Table 15 | test only | FY2027 uses Jul 2023 to Jun 2025 (12 months shared with FY2026), adds Medicare Advantage patients and drops the COVID-19 exclusion ([FY2026 IPPS final rule][fr-2026]) |

MSPB episodes also include 30-day readmission spending ([MSPB measure information form][mspb-mif]), so spending is used only descriptively (a national segment and one regression covariate), never in the penalty estimate or the business case.

## 8. Joining the three files

3,035 of 3,055 HRRP hospitals (99.3%) join both other files on CCN.

**Table 4.** Join funnel (hospitals).

| Step | Hospitals | Removed | Why |
|---|---:|---:|---|
| In the HRRP file | 3,055 | | |
| In Hospital General Information and MSPB (J1, J2) | 3,035 | 20 | no longer listed by CMS |
| Payment-eligible (S2) | 2,992 | 43 | Maryland is exempt from HRRP cuts |
| With at least one ERR (S2) | 2,777 | 215 | no published ERR |
| Estimated penalized, FY2026 rules | 2,336 | 441 | no condition above the threshold |

**Matched hospitals.** All 3,035 are acute care hospitals (J3; 72 other acute care hospitals have no HRRP rows), and the state agrees for all (J4). 52 names differ (J5), from rebrands (Tennova Healthcare-Clarksville is now Vanderbilt Clarksville Hospital) or formatting; the current name is shown. No client hospital is affected.

**Unmatched hospitals.** Four of the 20 have become critical access hospitals (CAHs), which HRRP does not cover ([42 U.S.C. 1395ww(q)][ssa-q]): the exact name reappears in the same state under a CAH number in Hospital General Information.

**Table 5.** Unmatched hospitals with an identified successor.

| HRRP CCN | Name | State | Now |
|---|---|---|---|
| 010008 | Crenshaw Community Hospital | AL | CAH 011308 |
| 330060 | Carthage Area Hospital | NY | CAHs 331318 and 331324 |
| 450143 | Ascension Seton Smithville | TX | CAH 671304 |
| 450411 | Eastland Memorial Hospital | TX | CAH 671303 |
| 390337 | Geisinger Medical Center Muncy | PA | possibly CAH 391301, UPMC Muncy (renamed, so not counted) |

The other 15 (`in_hospital_info = False` in `dim_hospital`) have no same-state name match and are likely closures or mergers (not checked one by one). The change is recent: 18 of the 20 are in CMS's FY2026 supplemental file (August 2025, open hospitals only), and CMS cut 13 of them, by 0.04% to 2.18%. All 20 are treated as not payment-eligible (not active IPPS hospitals going forward); they hold 39 scored results (0.3%), none in the client group, and cost 13 false negatives in the FY2026 test.

**Maryland.** 43 hospitals (258 rows, 195 with an ERR) are scored and reported but exempt from HRRP cuts; Table 15 lists none ([FY2026 Table 15][t15-26]). Flagged (S1), they stay in the tables but are excluded from the threshold, peer sets, segment statistics and penalty totals.

**MSPB coverage.** All 3,035 matched hospitals are in the MSPB file; 2,872 have a score (N4). The other 163 carry footnotes 5 (78), 1 (58), "1, 29" (14) and 19 (13; reported only for hospitals in CMS's inpatient and outpatient quality reporting programs). 2,751 of the 2,777 payment-eligible hospitals with an ERR (99.1%) have a score; their 11,415 rows are the association-regression sample.

## 9. Checks against published numbers

Where CMS has published a comparable figure, our estimate lands close to it. The dollar total is lower because of the payment base, not the penalty rate.

**Table 6.** Our FY2026 estimates against published CMS figures (payment-eligible hospitals).

| Measure | Ours | Published | Read |
|---|---|---|---|
| Median ERR per condition (V8) | 0.991 to 1.0008 | about 1.00 by construction ([HSR User Guide][hsr-guide]) | PASS |
| Hospitals penalized (P2) | 2,336 | 2,304 ([FY2026 Table 15][t15-26]) | +1.4%; PASS (±5% band) |
| Hospitals with a scored condition | 2,777 | 2,797 penalty-eligible ([FY2026 IPPS final rule][fr-2026]) | reconciles one by one |
| Share of those penalized | 84.1% | 82.4% (same rule) | close |
| Penalty ÷ base operating DRG payments | 0.44% | 0.44% (same rule) | same |
| National penalty per year (P3) | \$296M | no FY2026 total; nearest CMS totals \$316M (FY2025 method, FY2026 rule) and \$361M ([FY2027 rule][fr-2027]) | 6% to 18% lower; PASS (coarse band: \$190M to \$506M) |
| HF pass-through at 1,019 discharges (P6) | 0.73 | 0.70 reliability at about 1,019 cases ([Thompson et al. 2016][thompson]) | PASS |

- **Reconciliation.** Our 2,777 and CMS's 2,797 (25+ eligible discharges in a measure) share 2,776. Ours adds Bronson South Haven (230085), absent from CMS's file; CMS's adds 15 unmatched hospitals and 6 not in the Care Compare extract (110153, 200041, 200052, 330211, 420117, 450498).
- **Dollar total.** The rate matches, so the shortfall is in the base: our implied base operating DRG payments total \$66.9B, against about \$86.7B in an approximation built during research from CMS's FY2026 IPPS impact file (2,792 hospitals; [impact file][impact]; not a CMS figure). The median hospital is about \$16M in both, so the gap is in larger hospitals. Payment ±30% gives \$207M to \$385M.

## 10. External validation against CMS's actual FY2026 results

### 10.1 What was compared, and what is independent

Table 15 gives each hospital's actual payment adjustment factor ([FY2026][t15-26], [FY2027][t15-27]); the FY2026 supplemental file ([CMS][supp-26]) adds peer groups, peer-group median ERRs, unsuppressed discharges, penalty flags and DRG payment ratios. `src/validate_cms.py` downloads them to `data/external/`.

- **Independent.** No hospital-level value from these files enters the model, so the penalized-or-not agreement and the ERR identity are clean tests.
- **Not independent.** Three national inputs come from the same release: the six relative payment weights (`payment_rel_to_hf` in `seeds/condition_params.csv`, CMS's median within-hospital payment per case relative to heart failure), the neutrality modifier (0.9627) and the median six-condition share of base payments (0.133, CMS 0.1329; used only for the 3% cap and the percentage). They make the cut correlation partly in-sample.

### 10.2 Headline agreement

**Table 7.** Our FY2026 estimate against CMS's actual FY2026 results for the 2,937 hospitals in both files. CMS's file has 2,945 (no Maryland or closed hospitals; 8 are not in our extract). Cut = percentage reduction of fee-for-service base operating DRG payments. Source: `cms_validation_summary.csv`.

| Measure | Ours | CMS |
|---|---:|---:|
| Hospitals penalized (CMS total: 2,304) | 2,336 | 2,302 |
| Same penalized-or-not call (2,276 both, 575 neither, 60 only ours, 26 only CMS's) | 97.1% | |
| Cut correlation per hospital, Pearson / Spearman | 0.92 / 0.94 | |
| Mean / median cut among each side's penalized hospitals | 0.46% / 0.34% | 0.44% / 0.30% |
| Hospitals at the 3% cap | 10 | 15 |
| ERR, largest absolute difference (11,523 rows at 2,791 hospitals) | 0.0000 | |
| Condition flags agree (above threshold vs CMS flag; 11,484 results) | 96.8% | |

### 10.3 Where the misses come from

Apart from hospitals that have left the program, the misses sit near the threshold and involve cuts of 0.15% or less (`cms_validation_hospital.parquet` joined to `dim_hospital`).

- **False negatives (26).** 13 are unmatched hospitals (Section 8). The other 13 are in peer groups 1–3, where our threshold sits slightly above CMS's; their CMS cuts are all 0.06% or less.
- **False positives (60).** 40 are in peer group 5 (Section 10.5); 55 have an estimated cut below 0.10%, the largest 0.15%.
- Without the 18 unmatched hospitals CMS still listed, agreement is 97.5% (2,919 hospitals).

### 10.4 Hidden discharge counts

**Table 8.** Our imputed midpoint against CMS's actual discharges on the 3,635 hidden-count rows the supplemental file covers; range = [25, ⌊10 ÷ predicted rate⌋]. Rows and sums: `cms_validation_imputation.csv`.

| | HF | PN | COPD | AMI | CABG | Hip/knee | All |
|---|---:|---:|---:|---:|---:|---:|---:|
| Our midpoint ÷ actual | 0.90 | 0.83 | 0.94 | 0.91 | 0.98 | 1.33 | 1.09 |
| Actual inside our range | 79% | 72% | 80% | 82% | 91% | 96% | 86% |

Close overall (+9%), the midpoint is biased by condition: it overstates hip/knee by 33% (actual counts cluster at the low end: median 59 per row against our 104) and understates pneumonia by 17% and the other medical conditions by 6% to 10%. All 496 range misses lie above the upper bound, 99.8% of them with an ERR below 1.00: the bound uses CMS's shrunk predicted rate, so a hospital whose actual rate is below its predicted rate can exceed the bound with fewer than 11 readmissions. Rerunning `src.penalty.estimate` with CMS's counts (a test only) lowers the national estimate from \$296.1M to \$287.7M (−2.8%; hip/knee \$46.9M to \$39.7M, −15%; CABG −2.7%; others 0.5% or less) and the client group from \$1.231M to \$1.201M (−2.5%); the penalized hospitals stay the same.

### 10.5 Penalty threshold: national median vs CMS peer groups

CMS compares each hospital with the median ERR of its peer group, one of five equal-sized groups by share of patients dually eligible for Medicare and Medicaid ([CMS supplemental file][supp-26]). Care Compare has no peer groups, so our **penalty threshold** is the national median ERR per condition among payment-eligible hospitals. For the four medical conditions the group 5 median is the highest, 0.002 to 0.018 above ours, and groups 1–3 sit slightly below it (`cms_validation_thresholds.csv`). We therefore over-flag high-dual hospitals and miss a few small excesses in groups 1–3.

**Table 9.** Flag rates and payment cuts by CMS peer group. Results = scored rows at payment-eligible hospitals; mean cuts are over all hospitals in the group. Sources: `cms_validation_peer_groups.csv`, `cms_validation_hospital.parquet`.

| Peer group | Hospitals | Results | Ours above threshold | CMS penalized | Our mean cut | CMS mean cut |
|---|---:|---:|---:|---:|---:|---:|
| 1 (fewest dual-eligible) | 588 | 2,107 | 46.4% | 48.3% | 0.33% | 0.35% |
| 2 | 588 | 2,527 | 47.2% | 49.6% | 0.34% | 0.37% |
| 3 | 589 | 2,482 | 45.7% | 48.8% | 0.34% | 0.34% |
| 4 | 587 | 2,301 | 50.5% | 50.5% | 0.36% | 0.33% |
| 5 (most dual-eligible) | 585 | 2,067 | 61.2% | 53.7% | 0.46% | 0.33% |

Group 5 is the one material miss.

### 10.6 Illustrative client group

Eight New Jersey hospitals drawn by a seeded rule stratified by HRRP volume band: an illustrative group, not an actual health system.

**Table 10.** Payment cut (% of base operating DRG payments). Dollar row = each cut × our estimated base payments (our penalty ÷ our cut). Source: `cms_validation_client.csv`.

| Hospital (CCN) | Peer group | Ours, FY2026 | CMS, FY2026 | CMS, FY2027 |
|---|---:|---:|---:|---:|
| Princeton (Plainsboro) (310010) | 1 | 1.08% | 0.88% | 0.04% |
| Inspira Mullica Hill (310069) | 3 | 0.91% | 0.87% | 0.23% |
| Ocean Medical Center (310052) | 1 | 0.22% | 0.21% | 0.02% |
| Palisades Medical Center (310003) | 5 | 0.82% | 0.61% | 1.19% |
| Jersey City Medical Center (310074) | 5 | 0.49% | 0.32% | 0.51% |
| Monmouth Medical Center (310075) | 2 | 0.40% | 0.30% | 0.07% |
| Virtua Willingboro (310061) | 4 | 0.50% | 0.34% | 0.12% |
| University Hospital (Newark) (310119) | 5 | 0.34% | 0.05% | 0.05% |
| **Group, \$ per year on our payment base** | | **\$1.23M** | **\$1.04M** | **\$0.40M** |

Our estimate is above CMS's FY2026 cut at all eight hospitals and 19% above in total; three are in peer group 5. The ranking matches except that the top two swap; they carry 62% of the group's penalty in our estimate and 65% at CMS's cuts. In FY2027, CMS's cuts fell at five hospitals, rose at Palisades and Jersey City and were unchanged at University Hospital; the FY2027 total, \$0.40M, is 38% of the \$1.04M at CMS's FY2026 cuts (32% of our \$1.23M).

### 10.7 Persistence from FY2026 to FY2027

Penalties drift back toward the average. Across the 2,894 hospitals in both CMS Table 15 files (`cms_persistence_hospital.parquet`):

- Each hospital's FY2027 cut ≈ 0.58 × its FY2026 cut + 0.16 percentage points (least-squares slope 0.578, intercept +0.0016; correlation 0.573). Big FY2026 cuts shrank and small ones grew.
- The top tenth by FY2026 cut averaged 1.38% in FY2026 and 0.96% in FY2027, about 30% less; 40% of them lost more than half of their cut.
- The overall mean cut barely moved: 0.346% to 0.356% (0.439% to 0.423% among hospitals penalized in FY2026).
- 89% of FY2026-penalized hospitals were penalized again (78.8% of hospitals in FY2026, 70.5% in both years): penalty status is sticky, the size of the cut is not.

Published work finds that regression to the mean explains 74% to 87% of the ERR improvement at penalized hospitals ([Joshi et al. 2019][joshi]). The business case therefore assumes **persistence** (the share of today's ERR excess that remains without a program) of 0.5, tested from 0.3 to 0.8. The regression is only an approximate anchor: it uses payment cuts rather than ERRs, the windows share 12 months, and part of the slope reflects the FY2027 rule change (Medicare Advantage patients, 2-year window, no COVID-19 exclusion).

### 10.8 Reading CMS's supplemental file

CMS prints counts of 1,000 or more with a thousands separator ("2,393"), and `src/validate_cms.py` (`pd.to_numeric(errors="coerce")`) turns those 193 counts into missing values. No result in Sections 10.2–10.7 uses them. Only the payment weights are affected: read correctly, AMI's median relative payment would be 1.571 instead of 1.542, the others would move by less than 1%, and each median would use 97 to 124 more hospitals. With the corrected weights the national penalty rises by about 0.02% and the client group's by about \$250; penalized and capped counts do not change.

## 11. Full automated check table

**Table 11.** All 37 automated checks from the 2026-11-03 build, as generated in `data/processed/dq_checks_all.parquet` (31 SQL checks from `sql/09_dq_checks.sql`; P1–P6 from `src/analysis.py`), grouped by category. Text as generated.

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
| F2 | PASS | Format | HRRP IDs fall in the IPPS hospital range (last 4 digits 0001-0879 short-term, 0880-0899 demonstration) | 0 outside | 0 outside | – |
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
| P3 | PASS | Known numbers | Estimated national penalty \$ vs nearest CMS published totals (\$316M-\$361M) | same order of magnitude | \$296M | CMS did not publish an FY2026 dollar total; our payment assumptions are conservative (see assumptions B3) |
| P6 | PASS | Known numbers | Fitted shrinkage matches published measure reliability (HF pass-through at 1,019 cases ≈ 0.70) | 0.65-0.80 | 0.73 | Thompson et al. 2016: HF needs ~1,019 cases for 0.70 reliability |
| P4 | PASS | Reproducibility | Client group draw reproduces config.yaml (seed 42) | True | True | 8 hospitals, stratified by HRRP volume band |
| P5 | PASS | Reproducibility | Monte Carlo with fixed seed gives identical results on re-run | True | True | seed 42 |

## 12. Decisions taken because of these checks

- **IDs as text** (F1, F2), so CCNs with leading zeros join; **row counts and seeds pinned** (R1–R3, P4, P5).
- **A reason code on every row** (N1–N3): no ERR means no penalty, as at CMS; hidden-count rows keep their ERR, with imputed discharges.
- **Midpoint imputation, range kept** (N3, V4, V5; §10.4): the ends give \$275M to \$317M nationally. The hip/knee bias is documented, not tuned to CMS's counts, so a test file never becomes an input.
- **Footnote-29 rows kept** (valid ERRs); **Maryland out of all penalty math** (S1).
- **The 20 unmatched hospitals not payment-eligible** (J1, J2): this fits the forward-looking question and costs 13 false negatives in the FY2026 test.
- **National median threshold, tested against 1.00** (V8; §10.5): 1.00 gives 2,308 penalized and \$285M. The peer group 5 bias is disclosed, not corrected; peer groups cannot be rebuilt from these files.
- **Spending descriptive only** (T2); **measured pass-through, not 100%** (V7, P6).
- **Regression to the mean in the baseline** (§10.7): persistence 0.5 (0.3–0.8). Pilot hospitals are ranked on the benefit-cost ratio of the penalty a heart failure and pneumonia program can address, not on last year's total, which favors hospitals at a temporary peak.
- **Payment weights from CMS's DRG payment ratios** (§10.1), not DRG weights, which differ most for AMI (1.54 vs 1.06 × heart failure) and CABG (3.63 vs 4.50 ×). The other two inputs from that release are national constants (0.9627 and 0.133); no hospital-level CMS result enters the model.

## 13. Residual risks

Ordered by likely effect. Most move dollar figures by a few percent to about 20% without changing the business-case conclusion; payment level (risk 2) is the exception.

1. **Penalty threshold** (§10.5): over-flags high-dual hospitals, including pilot site Palisades (0.82% estimated, 0.61% actual); client total \$1.23M against \$1.04M at CMS's cuts, same ranking apart from the top two.
2. **Payment per discharge and base** (Section 9). National average payments (heart failure \$8,523 at wage index 1.0, scaled by condition) and base = HRRP-condition payments ÷ 0.133 give \$296M against \$316M to \$361M and 10 capped hospitals against 15. A shortfall in payment per discharge (the ÷ 0.133 step affects only the cap and the percentage) also understates avoidable penalty: payment +30% brings the pilot to break-even (hospital net +\$66 a year; `bc_sensitivity.parquet`). This partly offsets risk 1 for the client group.
3. **Pass-through outside heart failure.** At Thompson et al.'s 0.70-reliability volumes (AMI 605, HF 1,019, PN 442, COPD 559, CABG 107, hip/knee 9) our fit gives HF 0.73 but PN 0.52, COPD 0.59, AMI 0.62, CABG 0.32 and hip/knee 0.04. Thompson used older data, so we keep our fit. With k = 0.3 ÷ 0.7 × Thompson's volume, the pilot's benefit-cost ratio is 0.72 instead of 0.75; only 100% pass-through, which V7 rules out, lifts it above 1 (1.20).
4. **Imputed hidden counts** (§10.4): −2.8% nationally, −15% for hip/knee, −2.5% for the client group, same penalized hospitals.
5. **FY2026 data, FY2027+ rules.** The 2-year window, Medicare Advantage patients and the end of the COVID-19 exclusion may shift ERRs, peer medians and shrinkage; the business case applies the window and Medicare Advantage share but reuses FY2026 k.
6. **Persistence anchor** (§10.7): payment cuts, overlapping windows and a rule change; hence the 0.3–0.8 range.
7. **Partly in-sample test** (§10.1): affects the 0.92 correlation, not the 97.1% agreement or the ERR identity.
8. **Supplemental-file parsing** (§10.8): about 0.02%.
9. **Spending data.** MSPB covers 6 of the 36 months and includes readmission spending, so spending associations are descriptive and partly circular; 26 scored payment-eligible hospitals lack a score.
10. **Hospital status and refreshes.** Twenty hospitals have dropped out and more may close or convert before FY2029; a refreshed CMS file fails R1–R3 by design. All eight client hospitals are matched and none was renamed.

## Sources

CMS files, rules and guides (the FY 2026 and FY 2027 IPPS/LTCH PPS final rules are 90 FR 36536 and 91 FR 49570), ResDAC, the US Code and the State Operations Manual are linked where cited. Studies: COPSS-CMS White Paper Committee, *Statistical Issues in Assessing Hospital Performance*, 2012 ([PDF][copss]); Thompson MP et al., *Health Serv Res* 2016;51(6):2095–2114 ([PMC][thompson]); Joshi S et al., *JAMA Intern Med* 2019;179(9):1167–1173 ([PMC][joshi]).

[pdc-hrrp]: https://data.cms.gov/provider-data/sites/default/files/resources/a171bc36c488d3e0dc33ec63abb469a6_1770163617/FY_2026_Hospital_Readmissions_Reduction_Program_Hospital.csv
[footnotes]: https://data.cms.gov/provider-data/sites/default/files/resources/f29bb7c812e242f6edfef0a4b7d0eaca_1760630713/Footnote_Crosswalk.csv
[hsr-guide]: https://qualitynet.cms.gov/files/6893aac2728800f196e92cb1?filename=FY-2026-HRRP-HSR-User-Guide.pdf
[resdac]: https://resdac.org/articles/cms-cell-size-suppression-policy
[supp-26]: https://www.cms.gov/files/zip/fy2026-hospital-readmissions-reduction-program-supplemental-data-file.zip
[t15-26]: https://www.cms.gov/files/zip/fy-2026-hospital-readmissions-reduction-program-payment-adjustment-factors.zip
[t15-27]: https://www.cms.gov/files/zip/fy-2027-hospital-readmissions-reduction-program-payment-adjustment-factors.zip
[fr-2026]: https://www.govinfo.gov/content/pkg/FR-2025-08-04/html/2025-14681.htm
[fr-2027]: https://www.govinfo.gov/content/pkg/FR-2026-08-04/html/2026-15833.htm
[ssa-q]: https://www.govinfo.gov/content/pkg/USCODE-2023-title42/html/USCODE-2023-title42-chap7-subchapXVIII-partE-sec1395ww.htm
[som]: https://www.cms.gov/Regulations-and-Guidance/Guidance/Manuals/downloads/som107c02.pdf
[mspb-faq]: https://qualitynet.cms.gov/files/68f92e7dec89ae1f61aa3566?filename=FY2026_HIQR_MSPB_FAQS.pdf
[mspb-mif]: https://qualitynet.cms.gov/files/68f92567ec89ae1f61aa31e8?filename=HIQR_MSBP_Hospital_MIF_2025.pdf
[impact]: https://www.cms.gov/files/zip/fy2026-ipps-fr-impact-file.zip
[copss]: https://www.cms.gov/medicare/quality-initiatives-patient-assessment-instruments/hospitalqualityinits/downloads/statistical-issues-in-assessing-hospital-performance.pdf
[thompson]: https://pmc.ncbi.nlm.nih.gov/articles/PMC5134200/
[joshi]: https://pmc.ncbi.nlm.nih.gov/articles/PMC6596330/
