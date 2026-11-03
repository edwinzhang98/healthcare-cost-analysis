# 02 · Metric definitions

One definition for every number in the README, memo, report and dashboard. Each entry gives the meaning, then the **formula, grain and unit**, the **code** that computes it (SQL column, or `module.function()` in `src/module.py`), **CMS**'s definition and source, and **pitfalls**. Values: `reports/key_metrics.json` (run of 2026-11-03; keys abbreviated `bc.` = `business_case.`, `sc.` = `business_case.scenarios.`) unless another source is named.

**Scope.** CMS Care Compare files: HRRP (FY2026; discharges Jul 1, 2021 – Jun 30, 2024), MSPB-1 (CY2024), Hospital General Information. The **client group** is an illustrative set of 8 New Jersey hospitals drawn by a seeded rule, not an actual health system.

## Read this first: where numbers diverge

| Choice | Often mixed up | This project |
|---|---|---|
| Window | 3-year totals vs per year | HRRP counts are 3-year totals; "annual" = ÷ 3. |
| Hospitals | 3,055 listed; 2,992 payment-eligible; 2,777 scored | Payment-eligible for penalty, thresholds, peers, segments; share penalized ÷ scored (§5.6). |
| Rules | FY2026: 3 years, fee-for-service (FFS). FY2027+: 2 years, Medicare Advantage (MA) in the score, cut on FFS payments | Penalty estimate: FY2026. Business case: FY2027+. |
| Program year | Steady state vs phase-in year | Steady state = full strength (FY2032); phase-in values name their year. |

## 1. Conventions

| Term | Definition |
|---|---|
| Facility ID | 6-character CMS Certification Number (CCN), kept as text; first two characters = state; last four 0001–0879 = short-term hospitals, 0880–0899 = reserved for hospitals in demonstration projects [SOM]. HRRP IDs reach 0893 (checks F1–F2). |
| Conditions | HF heart failure, PN pneumonia, COPD, AMI heart attack, CABG bypass, HIP_KNEE elective hip/knee replacement; surgical = CABG, HIP_KNEE. |
| Payment-eligible | In the HRRP file (18,330 rows = 3,055 hospitals × 6 conditions [PDC]), outside Maryland (43, exempt [T15-26]) and still in Hospital General Information: 2,992 (`is_payment_eligible`). Of the 20 no longer listed, 4 are confirmed critical access conversions, 1 possible, 15 unverified, likely closures or mergers (03 §8). |
| Scored | Hospital × condition row with a published ERR: 11,720, of which 11,486 at payment-eligible hospitals (`mart_segment_summary`); scored hospital = at least one (2,777 payment-eligible). |
| Client group | 310010, 310052, 310069 (High volume); 310003, 310074, 310075 (Mid); 310061, 310119 (Low): `numpy.random.default_rng(42)` over payment-eligible NJ hospitals with ≥3 scored conditions (`src/client.py`). Target 310010 Princeton (Plainsboro); pilot 310069 Inspira Mullica Hill, 310003 Palisades. |
| Units | Rates in percent; ratios as published; dollars per year, nominal, FY2026 rates, undiscounted unless NPV. |
| Checks, tables | F1, V3, P1 etc. = the 37 checks (`sql/09`, `src/analysis.py`; see 03). Named tables are in `data/processed/` or `reports/tables/`. |

## 2. Time windows

The FY N adjustment applies to discharges Oct 1 (N−1) – Sep 30 (N) and uses discharges Jul 1 (N−5) – Jun 30 (N−2) through FY2026 (36 months, FFS, COVID-19 excluded) and Jul 1 (N−4) – Jun 30 (N−2) from FY2027 (24 months, FFS + MA, no COVID-19 exclusion); the window closes 15 months before the payment year [CFR152, FACT27]. Code: `cost_model.hrrp_window()`, `cost_model.fiscal_year()`.

| Program year | Data window | Penalty applies to | Program months in window (start Jan 2027) → effect share | Notes |
|---|---|---|---|---|
| **FY2026 (our data)** | Jul 2021 – Jun 2024 | Oct 2025 – Sep 2026 | n/a | Ended; 2,304 of 2,945 penalized [T15-26] |
| FY2027 | Jul 2023 – Jun 2025 | Oct 2026 – Sep 2027 | 0 | In effect; 2,334 of 2,912 penalized [T15-27]; hospital data due early 2027 [FACT27] |
| FY2028 | Jul 2024 – Jun 2026 | Oct 2027 – Sep 2028 | 0 | [IPPS27] |
| FY2029 | Jul 2025 – Jun 2027 | Oct 2028 – Sep 2029 | 6 of 24 (25%) → 12.5% | First year the program can lower the penalty |
| FY2030 | Jul 2026 – Jun 2028 | Oct 2029 – Sep 2030 | 18 of 24 (75%) → 50% | Sepsis measure enters payment [IPPS27] |
| FY2031 | Jul 2027 – Jun 2029 | Oct 2030 – Sep 2031 | 24 of 24 (100%) → 87.5% | Derived from the rule |
| FY2032 | Jul 2028 – Jun 2030 | Oct 2031 – Sep 2032 | 24 of 24 → 100% | Full strength; end of horizon |

Effect share = program months in the window weighted by strength (first 12 months at 50%) ÷ 24 (`program_share_of_cms_window`, `bc_phase_in.parquet`). The window is filled from FY2031, but full strength arrives in FY2032 (payments from Oct 2031); FY2031 gets about 88%.

Other files: MSPB-1 is CY2024 (T2); Hospital General Information and star ratings are download snapshots; CMS's supplemental file and Table 15s only test the method (`src/validate_cms.py`).

## 3. CMS measure fields (HRRP file)

Published by CMS, typed in `sql/02_stg_hrrp_readmissions.sql`, never recomputed. Grain: hospital × condition × FY2026 window.

| `reporting_status` | Published | Footnote: rows | Rows |
|---|---|---|---|
| reported | all fields | blank 7,798; 29: 239 | 8,037 |
| counts_suppressed | ERR, rates; readmissions "Too Few to Report" (1–10), discharges hidden | blank 3,545; 29: 138 | 3,683 |
| too_few_cases | nothing (<25 discharges) | 1 | 3,150 |
| not_available | nothing | 5 | 3,255 (1,975 CABG) |
| no_cases | discharges = 0 | 7 | 205 |

Only the first two carry a score; only `reported` rows fit pass-through. Footnotes [FN]: 1 too few cases; 5 not available; 7 no cases; 29 partial-period data under a CMS exception (kept, `has_footnote_29`). Every blank has a reason (N1).

### 3.1 Eligible discharges

Stays meeting the cohort rules: the denominator of every rate and penalty dollar.
- **Formula, grain, unit.** Published "Number of Discharges"; hospital × condition × 3 years; discharges. Hidden counts: `discharges_est` = round((25 + U) ÷ 2), U = max(25, floor(10 ÷ (predicted rate ÷ 100))); range [25, U].
- **Code.** `stg_hrrp_readmissions.discharges`; `fct_hospital_condition.discharges_est` (`_low`, `_high`, `_annual`), `discharges_imputed`; `dim_hospital.eligible_discharges_3yr`.
- **CMS.** Eligible discharges [HSR]: FFS, 65+, Parts A and B for 12 months, discharged alive, not transferred, no COVID-19 on admission [SPEC]; public at ≥25.
- **Pitfalls.** A 3-year total (the most common mixing error). Not all-payer; MA joins from FY2027. Hidden on 3,683 rows (9.7% of discharges, 54.6% of hip/knee; N3), checked against CMS's counts in 03 §10.4. Footnote 7 zero = no cases.

### 3.2 Number of readmissions

Eligible discharges followed by an unplanned readmission to any hospital within 30 days; counted events.
- **Formula, grain, unit.** Published count; hospital × condition × 3 years; readmissions.
- **Code.** `stg_hrrp_readmissions.readmissions`, `readmissions_suppressed`.
- **CMS.** Observed count [HSR]; values 1–10 are never published [RESDAC].
- **Pitfalls.** "Too Few to Report" = 1–10, not 0. Includes other hospitals, so own records undercount.

### 3.3 Observed readmission rate

Share of discharges readmitted; no risk adjustment, no shrinkage.
- **Formula, grain, unit.** 100 × readmissions ÷ discharges (reported rows); hospital × condition; percent. Hidden rows (business case): expected + (predicted − expected) ÷ pass-through, clipped to 0–100.
- **Code.** `stg_hrrp_readmissions.observed_rate_pct`; implied rate in `cost_model.ModelInputs.build()`.
- **CMS.** Not published [HSR].
- **Pitfalls.** Not risk-adjusted; never rank on it. The implied rate is noisy at low volume.

### 3.4 Predicted and expected readmission rates

Predicted: CMS's model rate for the hospital's patients with its own hospital effect (ERR numerator). Expected: the rate an average hospital would have with those patients (ERR denominator).
- **Formula, grain, unit.** Hierarchical logistic model: Σ patient probabilities ÷ discharges, with the hospital's own or the average hospital effect [SPEC]; hospital × condition; percent.
- **Code.** `stg_hrrp_readmissions.predicted_rate_pct`, `expected_rate_pct`.
- **CMS.** [HSR]; predicted = "adjusted actual readmissions" in SSA §1886(q).
- **Pitfalls.** Predicted rates are shrunk toward the national average, most at low volume [MEDPAC13]. Expected rates are case-mix specific, not national (medians: HF 19.4, COPD 17.9, PN 15.5, AMI 13.2, CABG 10.5, hip/knee 5.4; `national.conditions.*.expected_rate_pct`), with no social-risk adjustment [SPEC].

### 3.5 Excess readmission ratio (ERR)

Readmissions vs an average hospital with the same patients (1.05 = 5% more); the score behind the penalty.
- **Formula, grain, unit.** Predicted ÷ expected; hospital × condition; ratio. Identity holds within 0.000065 (V3); range 0.4698–1.6297 (V1).
- **Code.** `stg_hrrp_readmissions.err`, `has_err`, `reporting_status`.
- **CMS.** [HSR], [SPEC]; 42 CFR 412.152 [CFR152].
- **Pitfalls.**
  - Above 1.00 is not "penalized": the threshold is a median, slightly below 1.00 for five conditions (§5.1).
  - Shrinkage pulls small hospitals toward 1.00 (§8.1) [MEDPAC13]. Median reliability: AMI 0.58, HF 0.61, PN 0.68, COPD 0.65, CABG 0.78, hip/knee 0.94 [THOMPSON], so year-to-year changes are partly noise.
  - Not comparable across program years (§2) [IPPS26].
  - The rule says "not less than 1.0" [CFR152], but published ERRs are unfloored and reproduce all 2,945 FY2026 payment factors [SUPP]. Use them as published.

## 4. Derived readmission metrics

### 4.1 Excess readmissions

Readmissions above (negative: below) an average hospital with the same patients: the ERR as patients.
- **Formula, grain, unit.** discharges × (predicted − expected) ÷ 100 = discharges × expected ÷ 100 × (ERR − 1); signed at hospital × condition; readmissions per year (÷ 3) or per 3 years. Totals sum the positive part. **Above threshold** = annual discharges × expected ÷ 100 × max(ERR − threshold, 0), what the penalty charges for.
- **Code.** `fct_hospital_condition.excess_readmissions_3yr`, `_annual`, `_annual_pos`; `dim_hospital.excess_readmissions_annual_net`, `_pos`; `analysis.build()` → `condition_summary.excess_above_threshold`.
- **CMS.** Predicted minus expected readmissions [MEDPAC13]; the payment formula never counts them [CFR152].
- **Pitfalls.** Signed values cancel (national +217 a year signed vs 4,159 positive[^net]). Measured from 1.00, not the threshold. Model-based: understate observed gaps at small hospitals.

### 4.2 Readmission index

Discharge-weighted mean ERR over a hospital's scored conditions (project metric).
- **Formula, grain, unit.** Σ ERR_c × discharges_c ÷ Σ discharges_c; hospital; ratio. Median 1.00, range 0.55–1.36 (scored payment-eligible hospitals).
- **Code.** `dim_hospital.readmission_index`; percentile in `benchmarking.peer_summary()`.
- **CMS.** None; not the hospital-wide readmission measure [STAR51].
- **Pitfalls.** Discharge-weighted, not payment-weighted: a hip/knee excess readmission carries about 5× the penalty of an HF one (§5.7). Depends on which conditions are scored.

## 5. Penalty metrics

```
CMS [CFR154, SUPP]  reduction % = min(3%, NM × Σc DRG ratio_c × max(ERR_c − peer median_c, 0)); PAF = 1 − reduction %
Ours (sql/07, src/penalty.py)
  payments_c = discharges_c ÷ 3 × payment per case_c;  base = Σc payments_c ÷ 0.133
  penalty $  = min(NM × Σc payments_c × max(ERR_c − national median_c, 0), 3% × base);  reduction % = penalty $ ÷ base
```

Public data force two substitutions: national medians for peer-group medians, and payment per case (assumptions B3) × discharges for DRG ratio × total payments. SQL is the base case; `src/penalty.py` is its twin for what-ifs (agreement $0.000000 per hospital, P1).

### 5.1 Penalty threshold and excess ratio over it

The ERR above which a condition adds to the penalty, and how far above it the ERR sits.
- **Formula, grain, unit.** Threshold, ours: median ERR among payment-eligible hospitals: HF 0.9989, PN 0.9957, COPD 0.9969, AMI 0.9994, CABG 1.0008, hip/knee 0.9910 (condition; ratio). CMS: the median of the hospital's peer group (dual-eligible quintile) [SUPP]. Excess ratio = max(ERR − threshold, 0), 0 if unscored (hospital × condition; ratio points).
- **Code.** `fct_hospital_condition.penalty_threshold_err` (CTE `threshold`), `excess_ratio_over_threshold`, `is_above_threshold`; `penalty.penalty_thresholds()`.
- **CMS.** (ERR − peer-group median), counted with ≥25 discharges [CFR152]; peer groups required from FY2019 [SSA]; HF medians 0.9922–1.0164 across groups (`cms_validation_thresholds.csv`).
- **Pitfalls.** The national median under-flags low-dual and over-flags high-dual hospitals (03 §10.5); for the group's penalty this matters most at University Hospital (Newark): 0.34% estimated vs CMS's 0.05%, about $11K; for the pilot, at Palisades (§9.8). A 1.00 threshold gives $285.3M and 2,308 penalized. Medians move every year. Unscored conditions are 0, not "at threshold".

### 5.2 Neutrality modifier (NM)

National multiplier keeping peer-grouped savings in line with the pre-FY2019 method.
- **Formula, grain, unit.** 0.9627 (FY2026), 0.9628 (FY2027) [SUPP]; national; multiplier.
- **Code.** `config.yaml` `penalty_model.neutrality_modifier`; `PenaltyParams`, `ProgramParams`.
- **CMS.** [SUPP]; budget neutrality in SSA §1886(q)(3)(D) [SSA].
- **Pitfalls.** Not in Care Compare. Omitting it overstates penalties by about 4%.

### 5.3 DRG payment ratio

A condition's share of FFS base operating DRG payments; converts an ERR gap into a cut.
- **Formula, grain, unit.** CMS: cohort payments ÷ all payments, MedPAR FY2021–FY2024 [SUPP]; hospital × condition; share. Ours is implied: the six always sum to 0.133, CMS's median.
- **Code.** `config.yaml` `hrrp_payment_share`; CMS ratios only in `src/validate_cms.py`.
- **CMS.** [SUPP], [CFR152].
- **Pitfalls.** Varies by hospital (sum 0.075–0.192, 10th–90th percentile [SUPP]), so the % cut and the cap are approximate; below the cap the dollar penalty does not depend on it.

### 5.4 Payment adjustment factor (PAF) and reduction %

PAF multiplies the hospital's FFS base operating DRG payments for the year; reduction = 1 − PAF.
- **Formula, grain, unit.** Formula block; ours = `penalty_est_annual ÷ est_total_base_payments_annual`; hospital × year; percent (0–3%).
- **Code.** `mart_penalty_hospital.payment_reduction_pct`, `hits_cap`; `penalty.estimate()`.
- **CMS.** [CFR154]; FY2026 factors [T15-26].
- **Pitfalls.** Applies to all FFS base payments, not only the six conditions; excludes IME, DSH, outlier, low-volume and capital payments and all MA payments [CFR152, FACT27]. r = 0.92 on the size of the cut is partly in-sample: the six payment weights, 0.9627 and 0.133 come from the same CMS release (03 §10.1); the 97.1% agreement does not depend on them.

### 5.5 Estimated penalty $

Dollars lost to HRRP in a year under FY2026 rules (CMS publishes factors, not dollars).
- **Formula, grain, unit.** Formula block; payment-eligible hospitals, scored conditions; contributions scale pro rata at the cap; hospital × condition and hospital; dollars per year. Payment per case (assumptions B3): HF $8,523, PN $9,928, COPD $7,583, AMI $13,139, CABG $30,892, hip/knee $12,062.
- **Code.** `mart_penalty_condition.penalty_contribution_annual`; `mart_penalty_hospital.penalty_est_annual`; `penalty.estimate()`.
- **CMS.** Aggregate payments for excess readmissions [CFR152]; FY2026 cuts were 0.44% of base payments, no dollar total [IPPS26]. CMS's cuts on our payment base (`validation.client_cms_dollars_fy2026`, `_fy2027`; `.client[].cms_dollars_*`) = CMS's reduction % × our penalty ÷ our cut: $1.04M FY2026, $0.40M FY2027.
- **Pitfalls.** Not official: $296.1M vs CMS's nearest totals, $316.1M (FY2025 method) and about $361M (FY2027) [IPPS26, IPPS27]. National, not wage-adjusted, payments: ±30% gives $207M–$385M, so single hospitals are ±30%. Hidden counts at 25 or at the bound: $275.3M–$316.6M.

### 5.6 Penalized hospital and share penalized

Payment-eligible with at least one scored condition above the threshold.
- **Formula, grain, unit.** Uncapped penalty > 0; share = 2,336 ÷ 2,777 scored = 84.1%; hospital; count, share.
- **Code.** `mart_penalty_hospital.is_penalized`, `hits_cap`; `national.hospitals_penalized`.
- **CMS.** PAF < 1 [T15-26]: 2,304 of 2,945 listed (78.2%) = 82.4% of 2,797 penalty-eligible; 15 at the cap [IPPS26].
- **Pitfalls.** Three denominators circulate; name it. Our call matches CMS's for 97.1% of 2,937 hospitals.

### 5.7 Penalty per excess readmission

Penalty dollars per readmission above the threshold, by condition.
- **Formula, grain, unit.** Σ penalty ÷ Σ excess above threshold over payment-eligible scored rows; condition; dollars of annual penalty per excess readmission. One uncapped row: NM × payment per case ÷ expected rate (within 5% nationally[^ppe]). HF $41.5K, PN $58.9K, COPD $39.9K, AMI $93.7K, CABG $278.1K, hip/knee $216.6K.
- **Code.** `analysis.build()` → `condition_summary.penalty_per_excess_readmission`.
- **CMS.** None. MedPAC: payment × excess × 1 ÷ national rate, about 5× at a 20% rate [MEDPAC13]; under the pre-FY2019 formula almost 5× the stay's payment for HF and over 20× for hip/knee [MEDPAC18].
- **Pitfalls.** A list price: zero below the threshold or at the cap. Shrinkage, MA share and regression to the mean cut the value of an avoided readmission to $15.1K (pilot) and $6.9K (broad)[^value]. Multiples are relative to the payment for the stay, not its cost: ours are about 4.9× (HF) and 18× (hip/knee)[^mult]; `penalty_per_excess_vs_readmission_cost` divides by the $19,000 cost instead.

### 5.8 Concentration and condition-mix shares

How concentrated the penalty is, and how discharges, excess readmissions and dollars split by condition.
- **Formula, grain, unit.** Top-10% share: top 299 of 2,992 payment-eligible hospitals (unpenalized included) ÷ national total. Condition share: condition ÷ six-condition total; surgical = CABG + hip/knee; share.
- **Code.** `drivers.concentration_curve()`, `drivers.top_share()`; `drivers.condition_mix()` → `condition_summary.parquet`.
- **CMS.** None.
- **Pitfalls.** Among penalized hospitals only, the top-10% share is 48.2%, not 54.6% (top 233 of 2,336, `mart_penalty_hospital`). Excess shares start at 1.00 and ignore payment; dollar shares start at the threshold, so "HF + PN = 74% of excess readmissions" and "surgery = 29% of dollars" are both right.

## 6. Spending, quality and hospital attributes

### 6.1 MSPB-1 score

Medicare spending per episode around a stay vs the national median hospital, price-standardized and risk-adjusted.
- **Formula, grain, unit.** Mean of (standardized observed ÷ expected cost) × national average episode cost, ÷ the national median; episode = Part A and B claims 3 days before to 30 days after the stay [MIF]; hospital × CY2024; ratio.
- **Code.** `stg_mspb.mspb_ratio`; `dim_hospital.mspb_band`; `mspb_per_005` in `drivers.regression_frame()`.
- **CMS.** [MIF].
- **Pitfalls.** Includes readmission spending, so its link to ERR (+0.38 points per +0.05, §6.6) is partly built in; never add MSPB savings to readmission savings. Not what the hospital is paid. Excludes MA; 2,872 of 3,055 HRRP hospitals scored (N4).

### 6.2 Overall star rating

CMS's 1–5 star quality summary.
- **Formula, grain, unit.** Mortality, Safety, Readmission and Patient Experience 22% each, Timely & Effective Care 12%; ≥3 measures in ≥3 groups; k-means stars [STAR4]; from April 2026 the lowest Safety quartile is capped at 4 stars [STAR51]; hospital; stars.
- **Code.** `stg_hospital_info.star_rating`; `dim_hospital.star_rating_label`.
- **CMS.** [STAR4], [STAR51].
- **Pitfalls.** Circular: the Readmission group includes the CABG, COPD and hip/knee 30-day readmission measures, the hospital-wide readmission measure, and excess days in acute care (EDAC) after AMI, HF and pneumonia [STAR51]; descriptive segment only, not in the regression. 197 scored payment-eligible hospitals are unrated.

### 6.3 HRRP volume band

HRRP-eligible Medicare volume; defines peers and segments.
- **Formula, grain, unit.** `eligible_discharges_3yr`: Low < 400, Mid 400–999, High ≥ 1,000; hospital; category. Scored payment-eligible hospitals: 949 / 891 / 937 (medians 183 / 644 / 1,593).
- **Code.** `dim_hospital.size_band` (historical name).
- **CMS.** None (project definition).
- **Pitfalls.** Not bed size. Includes imputed discharges; MA enters the counts from FY2027.

### 6.4 Ownership group and census region

Owner type in three groups, and US Census region (DC = South).
- **Formula, grain, unit.** Non-profit = voluntary non-profit; For-profit = proprietary, physician; Government = government, tribal, VHA, DoD. Region from a state map in `sql/04`. Hospital; category. Scored hospitals: 1,788 / 599 / 390; South 1,136, Midwest 662, West 552, Northeast 427.
- **Code.** `stg_hospital_info.ownership_group`, `census_region` → `dim_hospital`.
- **CMS.** Ownership values follow the Provider of Services codes [POS]; region: none.
- **Pitfalls.** Ownership is as of the file release. Differences are associations: the Northeast's +0.98 ERR points vs the Midwest (§6.6) does not say why.

### 6.5 Segment mean ERR and 95% interval

Average ERR of scored rows in a segment (region, state, ownership, volume, stars, MSPB band, emergency services).
- **Formula, grain, unit.** mean ± 1.96 × SD ÷ √n over payment-eligible scored rows, flagged when n < 30; segment × condition; ratio. 50 state groups (49 states + DC; Maryland excluded); New Jersey is 2nd of 50 (1.0277; Massachusetts 1.0344).
- **Code.** `mart_segment_summary.mean_err`, `mean_err_ci_low`, `mean_err_ci_high`, `small_sample_flag`.
- **CMS.** None.
- **Pitfalls.** Rows from one hospital are not independent, so intervals are too narrow. Row-weighted.

### 6.6 ERR points and adjusted associations

Unit and model for comparing characteristics with the others held equal.
- **Formula, grain, unit.** ERR points = (ERR − 1) × 100. OLS on condition, ownership, volume, region, no-emergency-department flag and MSPB (per +0.05), errors clustered by hospital; 11,415 rows, 2,751 hospitals; points.
- **Code.** `drivers.adjusted_associations()` → `regression_coefs.parquet`.
- **CMS.** None.
- **Pitfalls.** Associations, not causes; R² 0.018.

## 7. Benchmarking

### 7.1 Peers

Comparison hospitals for a target.
- **Formula, grain, unit.** Payment-eligible hospitals with an ERR, same ownership group and volume band, target excluded, counted per condition; set. Princeton (Plainsboro): 707 overall, 704 HF, 577 hip/knee.
- **Code.** `benchmarking.peer_ids()`.
- **CMS.** None; not CMS's dual-eligible peer groups [SUPP].
- **Pitfalls.** Say "peers (same ownership and volume)", never just "peer group". Fewer than 10 scored peers flags a condition (`small_peer_group`, dashboard page 4); fewer than 30 peers overall, a warning.

### 7.2 Percentile, gap and readmissions vs peers

Where the target sits among peers (higher = worse), and how far it is from the typical peer.
- **Formula, grain, unit.** Percentile = 100 × share of peers with a lower ERR (or index); ≥ 75 "worse than most", ≤ 25 "better than most"; unscored "No CMS score" / "–" (footnotes 1, 5, 7). Gap = ERR − peer median (ratio points); × annual discharges × expected ÷ 100 = readmissions per year. Target × condition.
- **Code.** `benchmarking.benchmark()` → `percentile_vs_peers`, `gap_vs_peer_median`, `readmissions_vs_peer_median`; `benchmarking.peer_summary()`; `analysis.client_peer_grid()` → `client.peer_percentiles`.
- **CMS.** None.
- **Pitfalls.** Headline counts: index percentile > 50 = "readmits more than the typical peer", ≥ 80 = "bottom 20%"; HF ≥ 90, PN and COPD ≥ 75 (`recommendations.peer_summary()`). A high percentile can mean few patients: Princeton's hip/knee ERR of 1.38 (98.8th percentile) rests on 16 readmissions on 164 discharges over 3 years against 8.8 expected, about 2 extra a year (1.1 above the peer median in score terms)[^hk]. Its $249,157 is the FY2026 estimate; forward exposure is likely lower (FY2027 cut 0.04%; §8.2).

## 8. Model mechanics

### 8.1 Pass-through

Share of a real change in a hospital's readmission rate that reaches its CMS score; small hospitals get partial credit.
- **Formula, grain, unit.** (predicted − expected) ≈ λ × (observed − expected), λ = n ÷ (n + k), n = discharges in the CMS window; k by least squares on the 8,037 reported rows: HF 369, PN 414, COPD 396, AMI 370, CABG 228, hip/knee 192 (R² 0.994–0.998); hospital × condition; share. HF λ at 100 / 1,500 discharges: 0.21 / 0.80.
  - **Basis.** The business case uses the FY2027+ cohort, n = FFS discharges per year ÷ (1 − MA share) × 2 (1.13× the 3-year count): pilot rows 0.673 (Inspira Mullica Hill HF), 0.400 (Palisades HF), 0.447 (Palisades PN). The 3-year FFS basis of the data window gives 0.645 / 0.371 / 0.417[^pt]. Always say which.
- **Code.** `shrinkage.fit_k()`, `shrinkage.pass_through()` → `shrinkage_k.parquet`; `pass_through` in `bc_rows_*.parquet`.
- **CMS.** Not published; shrinkage gives small hospitals partial credit [MEDPAC13]. HF at 1,019 discharges: 0.73 vs Thompson's 0.70 reliability (P6) [THOMPSON].
- **Pitfalls.** Fitted on rows with 11+ readmissions; k may shift under FY2027 rules. Score only: readmissions and payer savings count in full.

### 8.2 Persistence

Share of today's ERR excess expected to remain in FY2029+ windows without a program (regression to the mean).
- **Formula, grain, unit.** Baseline ERR = 1 + persistence × (ERR − 1); same for the observed rate; base 0.5 (0.3–0.8; 1.0 = `targeted_pilot_no_rtm`); hospital × condition; share.
- **Code.** `cost_model.evaluate()` → `baseline_err`, `penalty_before`; anchor `validate_cms.run()` → `cms_validation_persistence.csv`.
- **CMS.** No metric. Anchor (2,894 hospitals in both Table 15 files [T15-26, T15-27]): FY2027 cut ≈ 0.58 × FY2026 cut + 0.16 points (slope 0.578, intercept +0.0016, correlation 0.573). Penalties drift back toward the average: the top tenth's mean cut fell from 1.38% to 0.96% (about −30%; 40% of them lost more than half) and small cuts grew, while the mean barely moved (0.346% → 0.356%; FY2026-penalized 0.439% → 0.423%)[^pers]. Regression to the mean explained 74–87% of improvement at hospitals penalized in FY2013 [JOSHI].
- **Pitfalls.** The slope is not a ratio of levels: with the intercept, the mean cut did not fall. It also reflects the FY2027 rule change (MA, 2-year window) and 12 shared months; FY2029+ windows share none. Persistence lowers the baseline (`penalty_before`: group $644K, pilot $249K; FY2026 $1.23M, $485K); comparing with FY2026 credits the program with natural improvement. CMS's FY2027 cuts on our base ($0.40M; Inspira $94K vs $191K baseline, Palisades $161K vs $59K) come under other rules and thresholds: a warning, not a replacement baseline.

## 9. Program (business-case) metrics

Steady-state annual values under FY2027+ rules (full strength, FY2032) unless a year is named, from `cost_model.evaluate()` → `bc_scenarios.parquet`, `business_case.scenarios`. Scenarios: `broad_all`, `targeted_all` (8 hospitals), `targeted_pilot` (2 hospitals with the best benefit-cost ratio alone; `analysis.pilot_hospitals()`), variants `_risk30`, `_no_rtm`, `_beds_refilled`, `broad_fy2026_rules`. The national run uses an MA share of 54% [KFF-MA].

```
cohort_c             = FFS discharges per year_c ÷ (1 − MA share)
r_c                  = reach × min(risk multiplier, 1 ÷ reach) × relative reduction × condition multiplier_c
new ERR_c            = baseline ERR_c − λ_c × r_c × baseline observed rate_c ÷ expected rate_c
readmissions avoided = Σc cohort_c × baseline observed rate_c ÷ 100 × r_c
avoided penalty      = penalty(baseline ERR) − penalty(new ERR)          FFS payments, 3% cap
```

**Inputs** (`config.yaml` `intervention`; sources in `docs/assumptions.md` C1–C16, B3). Broad: HF, PN, COPD, AMI on all scored rows, reach 50%, risk multiplier 1.0. Targeted: HF, PN above the threshold, reach 30%, risk 1.5. Both: base effect 10% (HF × 1.2, COPD × 0.5, surgery × 0.3), persistence 0.5, MA share 0.41 (NJ 41.1% [RUPRI]), no shared savings. Monte Carlo ranges: effect 3–20%, $250–$700 per enrollee, risk 1.2–1.8, persistence 0.3–0.8, MA 0.30–0.55, payment scale 0.85–1.20, variable share 0.60–0.90, fixed cost $10K–$60K.

### 9.1 Enrollees, program cost, readmissions avoided

Who is enrolled, at what cost, and what it prevents.
- **Formula, grain, unit.** Enrollees = cohort × reach over targeted rows (discharges per year: broad 2,309, pilot 201). Program cost = enrollees × $400 + $25,000 × hospitals (dollars per year: broad $1.12M, pilot $130K). Two-year pilot budget (`bc.pilot_unit_economics`): `budget_first_12_months` = fixed + half the variable cost, $90K; `budget_full_strength_annual` = program cost. Readmissions avoided per year among all Medicare patients, formula block, effect capped at 90% (broad 42.4, pilot 7.3).
- **Code.** `evaluate()` → `enrollees`, `program_cost`, `readmissions_avoided`; `phase_in()` by year. **CMS.** None.
- **Pitfalls.** Enrollees are discharges, not people, and include MA patients. Readmissions avoided count in full (shrinkage affects only the ERR); trial effects usually shrink in practice, and a before-and-after count overstates them (§8.2).

### 9.2 Avoided penalty

The cut in the annual penalty attributable to the program.
- **Formula, grain, unit.** Penalty at baseline ERR − penalty at new ERR, FFS payments, 3% cap; hospital; dollars per year. Full strength (FY2032): broad $292K, pilot $110K; FY2031: $267K, $96K[^phase]. Phase-in scales the ERR effect by the effect share (§2).
- **Code.** `evaluate()` → `penalty_today`, `penalty_before`, `avoided_penalty`; `phase_in()`. **CMS.** Timing per [CFR152].
- **Pitfalls.** Name the year. Measured against the baseline forecast, not the FY2026 penalty. Zero below the threshold.

### 9.3 Payer saving (P), variable cost (V) and lost margin per readmission

The money each avoided readmission moves.
- **Formula, grain, unit.** P = 0.892 × C = $16,948 (what payers stop paying); V = 0.80 × C = $15,200 (cost that disappears); lost margin = max(P − V, 0) = $1,748 (0 if beds are refilled); dollars per readmission. Payer savings: broad $718K, pilot $123K a year.
- **Code.** `ProgramParams.payment_per_readmission`, `variable_cost_per_readmission`, `lost_margin_per_readmission`; `evaluate()` → `payer_savings`, `system_savings`, `lost_margin`.
- **Sources.** 0.892 from the −12.1% FFS Medicare margin [MEDPAC26]. Variable share: 75–85% of costs vary with volume [MEDPAC25]; short-run 16% [ROBERTS]. C = $19,000 (2025 dollars), chosen between condition-specific HCUP Medicare readmission costs (2013 [HCUP196] × 1.318, BEA PCE hospitals [BEA] = $16.1K–$19.1K for COPD, PN, HF, AMI) and the all-condition 2020 average ($18,100 [HCUP307] × 1.161 ≈ $21.0K, led by septicemia).
- **Pitfalls.** A payer saving is hospital revenue lost unless shared back. MA assumed to pay like FFS. In the short run V is lower (lost margin $5,548 at a 0.60 share).

### 9.4 Hospital net and payback year

The program's effect on the hospital P&L.
- **Formula, grain, unit.** Avoided penalty + shared savings − lost margin − program cost; hospital or group; dollars per year: broad −$906K, pilot −$33K, pilot with 30% shared +$4K. Payback = first year with cumulative undiscounted net > 0: "not within FY2032" in every scenario.
- **Code.** `evaluate()` → `hospital_net`; `phase_in()` → `hospital_net_cum`, `hospital_npv_cum` (7%); `analysis.years_to_payback()`. **CMS.** None.
- **Pitfalls.** Steady state skips the lag: cumulative FY2027–FY2032 is −$5.6M (broad) and about −$501K (pilot).

### 9.5 Whole-system net

The effect for payers and the hospital together; transfers between them cancel.
- **Formula, grain, unit.** V × readmissions avoided − program cost; dollars per year: broad −$479K, pilot −$20K.
- **Code.** `evaluate()` → `combined_net`. **CMS.** None.
- **Pitfalls.** Uses V, not P, to avoid double counting. It does not value patients' health or time in dollars: patients' health gains are real but not counted.

### 9.6 Benefit-cost ratio and cost per readmission avoided

Hospital return per program dollar, and program dollars per readmission prevented.
- **Formula, grain, unit.** (Avoided penalty + shared savings − lost margin) ÷ program cost, dollars per $1: broad $0.19, targeted at 8 $0.38, pilot $0.75, pilot with 30% shared $1.03. Program cost ÷ readmissions avoided: broad $26.5K, pilot $17.9K (`bc.pilot_unit_economics`: also penalty relief $15,120, payer saving $16,948).
- **Code.** `evaluate()` → `benefit_cost_ratio`, `cost_per_readmission_avoided`; `analysis.pilot_unit_economics()`. **CMS.** None.
- **Pitfalls.** Not ROI (ratio − 1); hospital view, steady state. Cost per readmission above V means a negative whole-system net.

### 9.7 Break-even value

The input value giving zero net, others at base.
- **Formula, grain, unit.** Bisection on `evaluate()` (reduction 0–60%, cost $0–$3,000, share 0–100%); unit of the input. Pilot: base effect 14.0% (whole-system 11.8%), $236 per patient, 26.7% of all payer savings ($33K of $123K; 59% is traditional Medicare's, shared only via its own programs such as ACOs; from MA plans alone, about 65%). Broad: none up to 60%; $7.77.
- **Code.** `cost_model.break_even()` → `business_case.break_even`; `cost_model.grid()` → `bc_grid.parquet`. **CMS.** None.
- **Pitfalls.** One input at a time. The input is the base (pneumonia) effect; with HF at 1.2×, the pooled effect across enrollees is 1.16 × base[^pool]: 14% base ≈ 16% pooled (`bc.pooled_break_even_reduction`), 10% base ≈ 12% pooled (where 27% co-funding or $236 per patient breaks even). Month-24 rule (pooled): keep only if ≥16% at ≤$400 per patient, ≥12% with ≥27% payer co-funding, or ≥12% at ≤$236.

### 9.8 Sensitivity: ±30%, tornado, Monte Carlo

How far the result moves when inputs change.
- **Formula, grain, unit.** ±30%: each `TORNADO_PARAMS` input with a nonzero base at −30% and +30% (reach, MA share capped at 0.95); sign flips of hospital and whole-system net. Monte Carlo: 2,000 draws (seed 42) of eight independent triangular inputs (ranges above); probability net > 0.
- **Values.** Pilot: only payment +30% flips hospital net, to +$66 a year[^flip]; broad: none. P(hospital net > 0) 11.9%, whole-system 22.7%; hospital net 5th / 50th / 95th percentile −$127K / −$54K / +$19K.
- **Robustness** (`analysis.robustness()` → `bc.robustness`). `peer_thresholds`: pilot patients on each hospital's CMS FY2026 peer-group medians (Palisades, group 5: HF 1.0164, PN 1.0101): expected penalty $240K, avoided $98.7K, net −$44.4K, $0.66 per $1; Palisades' pneumonia ends below its threshold (avoided $23.2K vs $34.6K, net −$41.6K), Inspira's avoided $75.5K holds. `.each_hospital_alone`, `.rank_peer_threshold`: alone, Inspira first ($0.64), Palisades 5th of 8 ($0.30). `ffs_only_pilot`: 30% of FFS patients only (reach 0.177): net −$39.9K (cost $97.4K, avoided $65.0K); enrolling by risk, not payer, is a design choice.
- **Code.** `analysis.sensitivity_table()` → `bc_sensitivity*.parquet`; `cost_model.tornado()`; `cost_model.monte_carlo()` → `business_case.monte_carlo` (rerun identical, P5). **CMS.** None.
- **Pitfalls.** The tornado and the ±30% table both cap variable cost share at 1.0 (+30% of 0.80 would be 1.04). Monte Carlo ranges lean adverse (median below base); correlated inputs would widen the spread. Base case: national-median proxy; confirm both sites with each hospital's CMS Hospital-Specific Report before launch.

### 9.9 Pilot power

Whether the pilot can show the effect it needs.
- **Formula, grain, unit.** Two-group test of 30-day readmission, 80% power, two-sided 5%: n per group = (z0.975 + z0.80)² × [p0(1 − p0) + p1(1 − p1)] ÷ (p0 − p1)²; minimum detectable reduction (MDR) where n = enrolled. p0 31.3%; 2,480 per group for the base effect (11.6% pooled), about 1,250 for break-even; enrolled about 100 by month 12, 301 by month 24; MDR 52% and 32%.
- **Code.** `analysis.pilot_power()` → `business_case.pilot_power`. **CMS.** None.
- **Pitfalls.** The pilot cannot prove a break-even effect, so month 12 is stop/continue on delivery, cost and safety (≥80% receive all three components, ≥90 enrolled, variable cost ≤ $400 per patient, no rise in ED visits, observation stays, mortality or readmissions vs the comparison group) and the effect is judged at month 24 (§9.7). Optimistic (no clustering or matching losses). Not significant ≠ no effect.

## 10. Where each headline number comes from

README and memo numbers (abridged) and their `reports/key_metrics.json` keys; § gives the definition and code.

| Headline | Key | § |
|---|---|---|
| 3,055 hospitals, 18,330 rows (discharges Jul 2021 – Jun 2024); 30 checks pass, 7 warnings, 0 fail | `data.hrrp_hospitals`, `.hrrp_rows`, `.dq_checks` | 1, 2 |
| 2,336 hospitals penalized (CMS: 2,304); 84% of scored | `national.hospitals_penalized`, `.share_penalized_of_scored`; `known_numbers.fy2026_hospitals_penalized` | 5.6 |
| $296M a year, below CMS's $316M–$361M; single hospitals ±30% | `national.total_penalty`, `.penalty_sensitivity`; `known_numbers.fy2026_total_penalty_reference_low`, `_high` | 5.5 |
| Top 10% carry 55%; HF + PN 74% of excess readmissions; surgery 29% of dollars from 13% of discharges | `national.top10_share_of_penalty`, `.hf_pn_share_excess_readmissions`, `.surgical_share_penalty`, `.surgical_share_discharges` | 5.8 |
| About $217K per extra hip/knee readmission vs $42K for HF | `national.conditions.HIP_KNEE.penalty_per_excess_readmission` (and `HF`) | 5.7 |
| The group lost an estimated $1.2M in the FY2026 payment year; two hospitals carried 62%; HF ($511K) and hip/knee ($327K) the largest drivers | `client.total_penalty`, `.top2_share`, `.hospitals`, `.penalty_by_condition` | 5.5 |
| CMS's cuts on our payment base: FY2026 $1.04M (ours $1.23M); FY2027 about $0.4M, led by Palisades ($161K), below the FY2029+ baseline ($0.64M); they fell at five hospitals, held at one, rose at Palisades and Jersey City | `validation.client_cms_dollars_fy2026`, `_fy2027`, `.client[]` (`cms_reduction_*`, `cms_dollars_*`); `sc.broad_all.penalty_before` | 5.5, 8.2 |
| 7 of 8 readmit more than their typical peer, 5 in the bottom 20%; HF at three hospitals worse than at 90%+ of peers | `client.peer_percentiles`[^peer] | 7.2 |
| One hospital's hip/knee ratio (1.38) worse than at 99% of peers; it drove about $250K of the FY2026 estimate, forward exposure likely lower (FY2027 cut 0.04%) | `client.benchmark_target.HIP_KNEE`, `.target_penalty_by_condition.HIP_KNEE` ($249,157); `validation.client` (310010) | 7.2 |
| Biggest FY2026 cuts shrank about 30% in FY2027 (1.38% → 0.96%); small ones grew | `validation.persistence.top_decile_mean_cut_fy2026`, `_fy2027`, `.slope_fy2027_on_fy2026`; intercept[^pers] | 8.2 |
| Group-wide: about $1.1M a year for about $0.29M ($0.3M) at full strength (FY2032), $0.19 per $1; no break-even; under $8 per patient | `sc.broad_all.program_cost`, `.avoided_penalty`, `.benefit_cost_ratio`; `bc.break_even.broad_relative_reduction` (null), `.broad_cost_per_enrollee` | 9.1–9.7 |
| Two-year pilot (month-12 checkpoint) at Inspira Mullica Hill and Palisades: about $90K in the first 12 months, $130K a year at full size, 7 fewer readmissions, $110K less penalty at full strength; contact ≤72 h, visit ≤7 days | `client.pilot_hospital_names`; `bc.pilot_unit_economics.budget_first_12_months`, `.budget_full_strength_annual`; `sc.targeted_pilot.readmissions_avoided`, `.avoided_penalty`; design: business case §2 | 9.1, 9.2 |
| Best-placed pilot (base case): $0.75 per $1, hospital net −$33K a year; on CMS's peer-group thresholds $0.66, Palisades 5th of 8 | `sc.targeted_pilot.benefit_cost_ratio`, `.hospital_net`; `bc.robustness.peer_thresholds.pilot.benefit_cost_ratio`, `.rank_peer_threshold` | 9.4, 9.6, 9.8 |
| Relief starts late 2028 (2-year look-back); full effect late 2031; no payback by FY2032; FY2027 data early 2027; sepsis from FY2030 | `bc_phase_in.parquet`[^phase]; `sc.targeted_pilot.cum_hospital_net_6y` (−$500,848); [FACT27, IPPS27] | 2, 9.4 |
| Break-even: about 16% fewer readmissions among enrolled patients (14% base effect, HF at 1.2×; base case 10%, trials about 11%), ≤ $236 per patient, or about 27% of all payer savings ($33K of $123K; 59% traditional Medicare's; from MA plans alone about 65%) | `bc.pooled_break_even_reduction`; `bc.break_even.pilot_relative_reduction`, `.pilot_cost_per_enrollee`, `.pilot_hospital_share_of_savings` (× `sc.targeted_pilot.payer_savings`; ÷ `bc.params_targeted.ma_share`, 0.41); `bc.params_targeted.relative_reduction`; trials: assumptions C4 | 9.7 |
| Month 12: ≥90 enrolled (about 100 expected), ≥80% get all three steps at ≤$400. Month 24: keep if pooled readmissions fall about 16% (12% with co-funding or ≤$236); about 300 patients cannot prove it (needs about 1,250 per group) | `bc.pilot_power.enrolled_first_12_months`, `_24_months`, `.n_per_group_for_break_even_effect`; `bc.params_targeted.cost_per_enrollee`; break-even keys above[^pool] | 9.7, 9.9 |
| 2,000 scenarios: pays for itself 12% of the time (median −$54K) | `bc.monte_carlo.p_hospital_net_positive`, `.hospital_net_p50` | 9.8 |
| Of the ±30% changes only payment per discharge +30% flips the pilot (+$66 a year) | `bc.sensitivity_pilot.hospital_flips`; `bc_sensitivity.parquet`[^flip] | 9.8 |
| One readmission costs about $18,000 to prevent and earns about $15,000 of relief (group-wide $27,000 vs $7,000); the $17,000 saved goes to the insurer | `bc.pilot_unit_economics`; `sc.broad_all.cost_per_readmission_avoided`, `.avoided_penalty` ÷ `.readmissions_avoided` | 9.3, 9.6 |
| Same call as CMS for 97.1%; r = 0.92 (rank 0.94), partly in-sample; mean cut among penalized 0.46% vs 0.44%; University Hospital (Newark) 0.34% vs CMS's 0.05%, about $11K | `validation.agreement`, `.r_pearson`, `.r_spearman`, `.mean_reduction_ours`, `.mean_reduction_cms`; `.client` (310119) | 5.1, 5.4, 5.6 |
| About 20% of an HF improvement reaches the score at 100 discharges, 80% at 1,500 (R² ≥ 0.99) | `shrinkage.HF.pass_through_at_100`, `_at_1500`; `shrinkage.*.r_squared` | 8.1 |
| 0.9627 × payments × excess ratio, capped at 3%; SQL = Python (P1) | `bc.params_targeted.neutrality_modifier`, `.penalty_cap_pct` | 5, 5.2 |

## 11. Sources

- [CFR152] 42 CFR 412.152. https://www.ecfr.gov/api/versioner/v1/full/2026-10-01/title-42.xml?part=412&section=412.152
- [CFR154] 42 CFR 412.154. https://www.govinfo.gov/content/pkg/CFR-2024-title42-vol2/xml/CFR-2024-title42-vol2-sec412-154.xml
- [SSA] 42 U.S.C. 1395ww(q). https://www.govinfo.gov/content/pkg/USCODE-2023-title42/html/USCODE-2023-title42-chap7-subchapXVIII-partE-sec1395ww.htm
- [HSR] FY2026 HRRP HSR user guide. https://qualitynet.cms.gov/files/6893aac2728800f196e92cb1?filename=FY-2026-HRRP-HSR-User-Guide.pdf
- [SPEC] 2025 readmission measure specifications. https://qualitynet.cms.gov/files/6a0b7d2db58870567d25f40b?filename=2025_Rdmsn_MeasureMethodology.zip
- [FACT27] FY2027 HRRP fact sheet. https://www.cms.gov/files/document/fy-2027-hrrp-fact-sheet-pdf.pdf
- [SUPP] FY2026 HRRP supplemental file. https://www.cms.gov/files/zip/fy2026-hospital-readmissions-reduction-program-supplemental-data-file.zip
- [T15-26] FY2026 Table 15. https://www.cms.gov/files/zip/fy-2026-hospital-readmissions-reduction-program-payment-adjustment-factors.zip
- [T15-27] FY2027 Table 15. https://www.cms.gov/files/zip/fy-2027-hospital-readmissions-reduction-program-payment-adjustment-factors.zip
- [IPPS26] FY2026 IPPS final rule. https://www.govinfo.gov/content/pkg/FR-2025-08-04/html/2025-14681.htm
- [IPPS27] FY2027 IPPS final rule. https://www.govinfo.gov/content/pkg/FR-2026-08-04/html/2026-15833.htm
- [PDC] FY2026 HRRP hospital file. https://data.cms.gov/provider-data/sites/default/files/resources/a171bc36c488d3e0dc33ec63abb469a6_1770163617/FY_2026_Hospital_Readmissions_Reduction_Program_Hospital.csv
- [FN] Footnote crosswalk. https://data.cms.gov/provider-data/sites/default/files/resources/f29bb7c812e242f6edfef0a4b7d0eaca_1760630713/Footnote_Crosswalk.csv
- [RESDAC] ResDAC cell-size policy. https://resdac.org/articles/cms-cell-size-suppression-policy
- [MIF] MSPB measure information form. https://qualitynet.cms.gov/files/68f92567ec89ae1f61aa31e8?filename=HIQR_MSBP_Hospital_MIF_2025.pdf
- [STAR4] Star rating method v4.0. https://qualitynet.cms.gov/files/6009aab621f78000252347fc?filename=Star_Rtngs_CompMthdlgy_v4.0.pdf
- [STAR51] Star rating method v5.1. https://qualitynet.cms.gov/files/69eb9be1f1becb2be7183b08?filename=Star_Rtngs_CompMthdlgy_v5.1.pdf
- [POS] Provider of Services layout. https://data.cms.gov/sites/default/files/2023-07/0ca58d5d-7914-4532-b22d-41741d3e6151/P.QWB.POSQ.OTHER.LAYOUT.MAR23.pdf
- [SOM] State Operations Manual Ch. 2 §2779A1. https://www.cms.gov/Regulations-and-Guidance/Guidance/Manuals/downloads/som107c02.pdf
- [THOMPSON] Thompson et al. 2016. https://pmc.ncbi.nlm.nih.gov/articles/PMC5134200/
- [JOSHI] Joshi et al. 2019. https://pmc.ncbi.nlm.nih.gov/articles/PMC6596330/
- [MEDPAC13] MedPAC June 2013 Ch. 4. https://www.medpac.gov/wp-content/uploads/import_data/scrape_files/docs/default-source/reports/jun13_ch04.pdf
- [MEDPAC18] MedPAC June 2018 Ch. 1. https://www.medpac.gov/wp-content/uploads/import_data/scrape_files/docs/default-source/reports/jun18_medpacreporttocongress_rev_nov2019_note_sec.pdf
- [MEDPAC25] MedPAC March 2025 Ch. 3. https://www.medpac.gov/wp-content/uploads/2025/03/Mar25_Ch3_MedPAC_Report_To_Congress_SEC.pdf
- [MEDPAC26] MedPAC March 2026 Ch. 3. https://www.medpac.gov/wp-content/uploads/2026/03/Mar26_Ch3_MedPAC_Report_To_Congress_SEC.pdf
- [ROBERTS] Roberts et al. 1999. https://pubmed.ncbi.nlm.nih.gov/10029127/
- [HCUP196] HCUP SB #196. https://www.hcup-us.ahrq.gov/reports/statbriefs/sb196-Readmissions-Trends-High-Volume-Conditions.jsp
- [HCUP307] HCUP SB #307. https://hcup-us.ahrq.gov/reports/statbriefs/sb307-readmissions-2020.jsp
- [BEA] BEA NIPA Table 2.5.4. https://apps.bea.gov/national/Release/TXT/NipaDataA.txt
- [RUPRI] RUPRI Center (2026), Medicare Advantage Enrollment Update 2025. https://rupri.public-health.uiowa.edu/publications/policybriefs/2026/MA_Enrollment_2025.pdf
- [KFF-MA] KFF (2025), Medicare Advantage in 2025: Enrollment Update and Key Trends, kff.org.

[^net]: `mart_segment_summary`, National / ALL row: `excess_readmissions_annual_net` (+217.4).
[^ppe]: 0.9627 × `payment_per_discharge` ÷ (`expected_rate_pct` ÷ 100) vs `penalty_per_excess_readmission` (`national.conditions`): −4.3% (PN) to +0.9% (hip/knee).
[^value]: Pilot: `bc.pilot_unit_economics`. Broad: $292,053 ÷ 42.39.
[^mult]: `penalty_per_excess_readmission` ÷ `payment_per_discharge`: $41,518 ÷ $8,523 = 4.87; $216,638 ÷ $12,062 = 17.96.
[^hk]: `fct_hospital_condition`, 310010 HIP_KNEE: 164 × 5.39% expected = 8.8; (16 − 8.8) ÷ 3 = 2.4 a year. 1.1 = `readmissions_vs_peer_median`.
[^pt]: n from `fct_hospital_condition.discharges_est` (671; 218; 296), k from `shrinkage_k.parquet`; business-case n = n ÷ 3 ÷ 0.59 × 2.
[^pers]: `cms_persistence_hospital`: least-squares fit of `cut_fy2027` on `cut_fy2026`; means overall and where `cut_fy2026` > 0 (2,280); top tenth = at or above its 90th percentile (297).
[^phase]: `bc_phase_in`: `program_share_of_cms_window`, `avoided_penalty`.
[^flip]: `bc_sensitivity`, `payment_scale` +30%: $65.58.
[^peer]: Rules of `recommendations.peer_summary()`: index > 50 (7), ≥ 80 (5); HF ≥ 90 (3).
[^pool]: `bc.pilot_power.base_case_relative_reduction` 0.116 ÷ base 0.10 = 1.16; 1.16 × 13.97% = 16.2%.
