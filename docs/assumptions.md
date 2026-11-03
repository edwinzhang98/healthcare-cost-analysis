# Assumptions log

This log lists each assumption behind the penalty estimate, peer benchmarking and business case for a post-discharge follow-up program, with its source or reasoning. Base values are in `config.yaml` and `seeds/condition_params.csv`; results come from `reports/key_metrics.json` unless a footnote says otherwise. The last column says how each input is tested (in `docs/business_case.md` or on dashboard pages 5–6) or why it is fixed. "Pilot" is the targeted design at Inspira Mullica Hill and Palisades (hospital net −$33k a year, $0.75 back per $1); "broad" is the full program at all 8 hospitals (−$906k, $0.19 per $1). The 8 hospitals are an illustrative client group (D1), not an actual health system. ERR = excess readmission ratio; HF heart failure, PN pneumonia, AMI heart attack, CABG bypass surgery; FFS = fee-for-service Medicare; MA = Medicare Advantage; DQ checks are on dashboard page 2.

## A. Data handling

*Scope: Care Compare HRRP file, 3,055 hospitals × 6 conditions, discharges 2021-07-01 to 2024-06-30 (FY2026 program).*

| ID | Assumption | Base value (low–high if tested) | Source / reasoning | Where used (file) | Tested how |
|---|---|---|---|---|---|
| A1 | Discharge counts hidden by CMS are imputed | Midpoint of [25, 10 ÷ predicted rate] (low 25, high the upper bound) | CMS hides counts when readmissions are 1–10 ([ResDAC][resdac]) but shows the ERR, which needs ≥25 cases ([HSR guide][hsr]). 3,683 rows: 9.7% of discharges, 55% of hip/knee. The upper bound uses the predicted rate, so it is approximate. | `sql/05_fct_hospital_condition.sql` | Low/high: national $275M / $317M (base $296M), client $1.17M / $1.29M. Imputed ÷ CMS's actual counts (3,635 rows): 1.09 overall, 1.33 hip/knee; 86% of actual counts inside [low, high] ([03 §10.4][dq104]). Using them: national −2.8%, client −2.5% ($30k, mostly Ocean Medical Center)[^c]. |
| A2 | Maryland is excluded from penalties | 43 hospitals, out of penalty totals, thresholds and peer sets | Exempt from HRRP cuts under its all-payer model; absent from CMS Table 15 ([Table 15][t15-26]). | `sql/05_fct_hospital_condition.sql` | CMS validation: none is in CMS's FY2026 payment file[^c]. |
| A3 | Hospitals missing from Hospital General Information are excluded from penalties | 20 hospitals (15 with an ERR) | Closed, merged or converted since the period: 4 confirmed critical access conversions (exact name and state)[^d], which are outside HRRP ([42 USC 1395ww(q)][usc]); 1 possible (Geisinger Medical Center Muncy, perhaps now UPMC Muncy); 15 unverified, likely closures or mergers. List: [03 §8][dq8]. | `sql/05_fct_hospital_condition.sql` | CMS validation: 18 are in CMS's FY2026 file and CMS penalized 13 (half of our 26 false negatives); including them adds $1.1M (0.4%) nationally[^c]. None is in NJ. |
| A4 | Rows with footnote 29 are kept | 377 rows at 85 hospitals[^d] | Partial-period data under a CMS-approved exception ([footnote crosswalk][fn]); CMS still uses these ERRs for payment. | `sql/02_stg_hrrp_readmissions.sql` | CMS validation: all 372 rows at payment-eligible hospitals appear with the same ERR; 181 carry a CMS penalty flag[^c]. |
| A5 | ERRs are used as published, not floored at 1.0 | Range 0.47–1.63 | Since FY2019 a condition is penalized when its ERR exceeds its peer-group median ([CMS methodology][infographic]), which is usually below 1.0. The ERR definition in [42 CFR 412.152][cfr152] still says "not less than 1.0". | `sql/05_fct_hospital_condition.sql` | CMS validation: CMS's file has the same unfloored ERRs (difference 0.0000). Threshold 1.00 run (B2). |
| A6 | HRRP volume band stands in for hospital size | Low < 400, Mid 400–999, High ≥ 1,000 eligible FFS discharges over 3 years | No bed counts in these files. Near terciles: 949 / 891 / 937 scored payment-eligible hospitals[^d]. Volume also sets how far CMS shrinks the ERR (C15). | `sql/06_dim_hospital.sql` | Definition only. No significant ERR difference by band in the adjusted regression. |

## B. Penalty formula

*Penalty per year = 0.9627 × Σ condition payments × max(ERR − threshold, 0), capped at 3% (`sql/07_mart_penalty_estimate.sql`, mirrored in `src/penalty.py`). Against CMS's actual FY2026 results for 2,937 hospitals: same penalized/not call for 97.1% (60 false positives, 26 false negatives); correlation of payment cuts 0.92 (partly in-sample: the six payment weights, 0.9627 and 0.133 come from the same CMS release; the 97.1% does not depend on them).*

| ID | Assumption | Base value (low–high if tested) | Source / reasoning | Where used (file) | Tested how |
|---|---|---|---|---|---|
| B1 | Neutrality modifier | 0.9627 | CMS FY2026 value, the same for every hospital ([supplemental file][supp]); FY2027 is 0.9628. | `config.yaml` | Matches CMS; fixed. |
| B2 | Penalty threshold = national median ERR per condition among payment-eligible hospitals | HF 0.999, PN 0.996, COPD 0.997, AMI 0.999, CABG 1.001, hip/knee 0.991 (alternative 1.00) | Proxy for CMS's dual-eligible peer-group medians, which Care Compare lacks. CMS's medians range 0.989–1.016 and, for the medical conditions, are highest in peer group 5, the most dual-eligible (`reports/tables/cms_validation_thresholds.csv`). | `sql/05_fct_hospital_condition.sql` | Threshold 1.00: national $285M vs $296M, client $1.18M vs $1.23M. CMS validation: peer group 5 results flagged 61% (ours) vs 54% (CMS). Each hospital's CMS FY2026 peer-group medians, same pilot patients: expected penalty $240k, avoided $98.7k, hospital net −$44k a year ($0.66 per $1; base −$33k, $0.75). Palisades' pneumonia ends below its group-5 threshold (medians HF 1.016, PN 1.010): avoided $23.2k vs $34.6k, net −$41.6k vs −$30.2k; Inspira's $75.5k unchanged. |
| B3 | Payment per case by condition | HF $8,523, PN $9,928, COPD $7,583, AMI $13,139, CABG $30,892, hip/knee $12,062 (±30%) | HF = standardized amount $6,752.61 ([Tables 1A–1E][t1]) × discharge-weighted HF DRG weight 1.262 ([Table 5][t5], [2024 case mix][mup]), wage index 1.0. Others = HF × CMS's median within-hospital payment per case relative to HF (`reports/tables/cms_payment_weights.csv`); cohorts include cases outside the core DRGs ([HRRP archives][archives]). | `seeds/condition_params.csv` | ±30% table: national $207M–$385M, client $0.86M–$1.60M; the only ±30% input that flips the pilot for the hospital (+30% → hospital net +$66/yr). Monte Carlo 0.85–1.20. Sliders, pages 5–6. |
| B4 | Annual volume = 3-year discharges ÷ 3 | 36-month window | The cut applies to one fiscal year's payments. COVID-19 patients (0.15%–2.5% of cases) are excluded until FY2027 ([FY2026 final rule][fr26]). | `sql/05_fct_hospital_condition.sql` | Covered by the ±30% payment range. |
| B5 | 3% cap on total base payments, estimated as HRRP-condition payments ÷ 0.133 | 0.133; cap 3% | CMS median sum of the six DRG payment ratios is 0.1329 ([supplemental file][supp]); the cap is statutory ([42 USC 1395ww(q)][usc]). Affects only the cap and the % cut. | `sql/07_mart_penalty_estimate.sql` | CMS validation: 10 hospitals at the cap vs 15; mean cut among penalized 0.46% vs 0.44%. Fixed. |
| B6 | A condition counts only if it has a published ERR | ≥25 eligible discharges | CMS rule for display ([HSR guide][hsr]) and payment ([FY2026 final rule][fr26]). MA patients will lift some conditions above 25 from FY2027; the model keeps today's set. | `sql/05_fct_hospital_condition.sql` | CMS validation: condition flags agree for 96.8%. |

## C. Business case

*From `config.yaml` (`intervention`) and `ProgramParams` in `src/cost_model.py`. The broad and targeted presets differ only in C1–C3; both reuse the penalty formula (B1–B6). Hospital net = avoided penalty + shared savings − lost margin − program cost. Whole-system net (payers and hospital together) = variable cost saved − program cost; patients' health gains are real but not counted. Dollars are per year at full strength (FY2032).*

| ID | Assumption | Base value (low–high if tested) | Source / reasoning | Where used (file) | Tested how |
|---|---|---|---|---|---|
| C1 | Conditions enrolled | Broad: HF, PN, COPD, AMI, all hospital-conditions. Targeted: HF, PN, only above the threshold | HF and PN carry 74% of national excess readmissions; HF has the strongest evidence (C5). Penalty relief exists only above the threshold. Surgery has weak evidence. | `config.yaml` | Scenarios: broad $0.19 per $1, targeted at 8 hospitals $0.38, pilot $0.75. |
| C2 | Share of eligible patients (FFS + MA) enrolled | Broad 50% (35%–65%); targeted 30% (21%–39%) | Design choice. 50% is ambitious: transitional care management (TCM) was billed after only 3%–7% of eligible discharges in 2013–2015 ([Bindman & Cox 2018][bindman]). | `config.yaml` | ±30% table, tornado, slider. |
| C3 | Readmission risk of enrollees vs average | Broad 1.0; targeted 1.5 (1.2–1.8) | HOSPITAL score (Donzé et al., JAMA Intern Med 2016): the top 38% by risk readmit at about 1.65× the average, the top 30% at about 1.76×[^e]; 1.5 allows for imperfect enrollment. | `src/cost_model.py` | Monte Carlo, slider. |
| C4 | Readmission reduction among enrollees (base effect) | 10% (3%–20%) | RR 0.89 for discharge planning ([Cochrane 2022][cochrane]) and for trials since 2002 ([Leppin 2014][leppin]); post-discharge calls alone have no effect ([Boggan 2025][boggan]). | `config.yaml` | ±30% table, tornado, Monte Carlo. Break-even: pilot 14.0% (whole-system 11.8%), about 16% pooled (C5); broad none below 60%. Pilot power: minimum detectable reduction 32% with ~301 enrolled by month 24 (52% at month 12). |
| C5 | Effect by condition (× C4) | HF 1.2, PN 1.0, AMI 1.0, COPD 0.5, CABG and hip/knee 0.3 | HF evidence is strongest ([AHRQ 2014][ahrq]), tempered from 15% to 12% after the PACT-HF trial found no significant effect (HR 0.93, 0.73–1.18; Van Spall et al., JAMA 2019). AMI and PN rest mostly on observational studies ([Balasubramanian 2025][bala]). COPD: no significant effect on 30-day all-cause readmission (RR 0.95, 95% CI 0.76–1.19; [Zhong 2022][zhong]). Surgery inconclusive ([Tobiano 2025][tobiano]). | `src/cost_model.py` | Scales with C4; not varied alone. Pooled over the pilot's patients: 1.16 × C4 (10% → 11.6%; 14% → ~16%). |
| C6 | Program cost per enrollee, 2024 dollars | $400 ($250–$700) | Middle of CPI-adjusted anchors ([CPI-U][cpi]): Care Transitions Intervention $334–$362 ([Coleman 2006][cti]), CCTP about $478 ([CCTP evaluation][cctp]), C-TraC about $519 ([Kind 2012][ctrac]), general programs $418–$733 ([Nuckols 2017][nuckols]). Includes frontline staff time. | `config.yaml` | ±30% table, tornado, Monte Carlo. Break-even: pilot $236; broad $8. |
| C7 | Fixed cost per hospital per year | $25,000 ($10,000–$60,000) | Oversight and reporting only: about 390 hours of RN time at $45.00/h ([BLS][bls-rn]) × 1.42 benefits load ([BLS ECEC][bls-ecec])[^e]. | `config.yaml` | ±30% table, tornado, Monte Carlo, slider. |
| C8 | Hospital cost of one readmission, 2025 dollars | $19,000 ($13,300–$24,700) | Chosen between HCUP's condition-specific Medicare readmission costs (COPD, PN, HF, AMI; 2013, $12,186–$14,478; [SB #196][hcup196]) × 1.318 ([BEA PCE hospitals][bea]) = $16,061–$19,082 and the 2020 all-condition Medicare average ($18,100, largest group septicemia; [SB #307][hcup307]) × 1.161 ≈ $21,000[^e]. Base at the top of the condition range. | `config.yaml` | ±30% table, tornado, slider. Not in the Monte Carlo. |
| C9 | Payment ÷ cost of a readmission | 0.892 | FFS Medicare margin −12.1% ([MedPAC 2026][medpac26]), so payment = cost ÷ 1.121. Per avoided readmission payers save $16,948 and the hospital loses $1,748 of margin. Also applied to MA patients. | `config.yaml` | Bounded by the beds-refilled scenario (C12). |
| C10 | Variable share of a readmission's cost | 0.80 (0.60–0.90) | MedPAC: 75%–85% of hospital costs vary with volume ([MedPAC 2025][medpac25]). Stress case: 16% short-run ([Roberts 1999][roberts]). | `config.yaml` | ±30% table and tornado (+30% would give 1.04; both cap it at 1.0), Monte Carlo. At 16%: pilot −$122k, whole-system −$108k[^m]. |
| C11 | Payer savings shared with the hospital | 0% (scenario 30%) | No shared-savings terms with payers assumed. About 59% of payer savings accrue to traditional Medicare, which shares savings only through its own programs (such as accountable care organizations). | `config.yaml` | Break-even share 27% of all payer savings ($33k of $123k a year); from the MA plans alone, about 65% of theirs. Scenario 30%: pilot +$4k/yr ($1.03 per $1), but the FY2027–FY2032 total stays −$306k. Slider. |
| C12 | Freed beds are not refilled | No (scenario: yes) | Occupancy unknown, so lost margin stays. | `config.yaml` | Scenario: pilot −$20k/yr ($0.84 per $1). |
| C13 | Persistence of today's ERR excess (regression to the mean) | 0.5 (0.3–0.8; scenario 1.0) | Regression to the mean explained 74%–87% of penalized hospitals' ERR improvement ([Joshi 2019][joshi]). In CMS's actual cuts (2,894 hospitals), a hospital's FY2027 cut ≈ 0.58 × its FY2026 cut + 0.16 points (correlation 0.57), so penalties drift back toward the average: the top tenth's mean cut fell from 1.38% to 0.96% (about −30%; 40% of them lost more than half), small cuts grew, and the mean barely moved (0.346% → 0.356%; `cms_persistence_hospital.parquet`). Part of the slope reflects the FY2027 rule change (MA, 2-year window) and the 12 months both windows share; FY2029+ windows share none with today's data. Lowers the group's expected penalty from $1.23M (FY2026 estimate) to $0.64M (FY2029+; Inspira $191k, Palisades $59k). CMS's FY2027 cuts on our payment base total $0.40M (Inspira $94k, Palisades $161k), but FY2027 is scored under different rules and thresholds: a warning, not a replacement baseline. | `src/cost_model.py` | ±30% table, tornado, Monte Carlo. Scenario 1.0: pilot −$23k/yr ($0.83 per $1). |
| C14 | MA share of Medicare patients | NJ 41% (30%–55%); national 54% | NJ 41.1% ([RUPRI Center 2026, *Medicare Advantage Enrollment Update 2025*][rupri]); national 54% (KFF 2025). From FY2027 MA patients count in the ERR but the cut applies to FFS payments only ([CMS fact sheet][fs27]): each enrollee, whichever payer covers them, moves the score about 59% as much as an FFS patient did under FY2026 rules. Enrolling by risk, not payer, is a design choice; it scales enrollment and cost by 1 ÷ (1 − MA share), 1.69×[^e]. All 8 client hospitals use New Jersey's 41%; the national view applies 54% to every hospital. | `src/cost_model.py` | ±30% table, tornado, Monte Carlo. FY2026-rules scenario (no MA, 3 years): broad −$509k vs −$906k. FFS-only pilot (30% of FFS patients, 17.7% of all Medicare): cost $97.4k, avoided $65.0k, hospital net −$39.9k vs −$33k. |
| C15 | Pass-through n ÷ (n + k) | k: HF 369, PN 414, COPD 396, AMI 370, CABG 228, hip/knee 192; n = FY2027+ cohort = annual FFS discharges ÷ (1 − MA share) × 2 years (1.13× the 3-year FFS count)[^e] | CMS shrinks low-volume hospitals toward 1.0 ([COPSS-CMS][copss]). k fitted on FY2026 rows with published counts (R² ≥ 0.99); at 1,019 HF cases it gives 0.73 vs the 0.70 reliability mark ([Thompson 2016][thompson]). Reuse under FY2027 rules is assumed. Pilot rows on this basis: Inspira Mullica Hill HF 0.673, Palisades HF 0.400, PN 0.447 (3-year FFS basis, as in benchmarking: 0.645, 0.371, 0.417). | `src/shrinkage.py` | Full pass-through: pilot +$26k/yr ($1.20 per $1)[^m]. Dashboard toggle; DQ check P6. |
| C16 | CMS window from FY2027 | 2 years: FY N uses discharges July N−4 to June N−2 | CMS rule ([42 CFR 412.152][cfr152]). A January 2027 start puts program months in 25% of the FY2029 window (6 of 24), 75% of FY2030 and 100% of FY2031; with the half-strength first year (C17) the effect reaches 12.5%, 50% and 87.5%, and full strength in FY2032 (payments from October 2031). | `src/cost_model.py` | FY2026-rules scenario (C14); phase-in chart, page 6. |
| C17 | Timing and discounting | Start 2027-01-01; 50% strength for 12 months; FY2027–FY2032; 7% | Go-live after the next budget cycle; 7% is a judgment of cost of capital. | `config.yaml` | Not varied. The pilot loses money every year (cumulative FY2027–FY2032 hospital net −$501k; never pays back), so no discount rate flips it. |
| C18 | Monte Carlo | 2,000 runs, triangular, seed 42 | Varies C3, C4, C6, C7, C10, C13, C14 and payment scale independently; cost ranges skew high. | `src/cost_model.py` | Reproducible (DQ check P5). Pilot positive in 11.9% of runs (whole-system 22.7%); median −$54k, 5th–95th percentile −$127k to +$19k. |
| C19 | Pilot hospitals | Top 2 by targeted benefit-cost ratio: Inspira Mullica Hill $0.96, Palisades $0.50[^m] | Rank on the penalty the program can address. The group's largest FY2026 penalty, at Princeton, is mostly hip/knee; CMS's cut there fell from 0.88% to 0.04% in FY2027 (Inspira 0.87% → 0.23%; Palisades rose, 0.61% → 1.19%). | `src/analysis.py` | Dashboard selector; all 8 hospitals in C1. On each hospital's own CMS peer-group medians Inspira stays first ($0.64) and Palisades ranks 5th of 8 ($0.30; B2): confirm both sites with each hospital's CMS Hospital-Specific Report before launch. |

## D. Client group and benchmarking

*Scope: payment-eligible hospitals; FY2026 ERRs.*

| ID | Assumption | Base value (low–high if tested) | Source / reasoning | Where used (file) | Tested how |
|---|---|---|---|---|---|
| D1 | Client group drawn by a fixed rule | NJ, payment-eligible, ≥3 scored conditions; 3 High, 3 Mid, 2 Low volume; numpy `default_rng(42)` | CMS data has no health-system membership, so the group is illustrative. 3/3/2 over-weights smaller hospitals against the 36/15/8 pool[^d] so every band appears. | `src/client.py` | DQ check P4 reproduces the IDs in `config.yaml`. |
| D2 | New Jersey as the state | Mean ERR 1.028, 2nd of 50 state groups (49 states + DC; Maryland excluded); 93% penalized | A high-penalty setting. Massachusetts (1.034) has no qualifying Low-volume hospital[^d]. Not an average state. | `config.yaml` | Dashboard page 5 takes any state. |
| D3 | Peers for benchmarking | Same ownership group (3) and HRRP volume band; payment-eligible; target excluded | As requested; the same band keeps shrinkage comparable (C15). Not CMS's dual-eligible peer groups (B2). Target 310010 has the group's largest FY2026 penalty. | `src/benchmarking.py` | 707 peers for the target (520–704 per condition); a condition with fewer than 10 scored peers is flagged, a group under 30 warned. Other peer sets on page 4. |
| D4 | Percentile vs peers | % of peers with a lower ERR; ≥75 "worse than most", ≤25 "better than most" | Rank-based; ties count as not lower. Hospital level uses the discharge-weighted readmission index. | `src/benchmarking.py` | Definition only. |

## Known biases and their direction

*Effect on the client-group results; "favors the program" means it makes the program look better than it probably is.*

| Bias | Direction | Size or evidence | Effect on the conclusion |
|---|---|---|---|
| National-median threshold (B2) | Overstates safety-net penalties | Peer group 5 mean cut 0.46% (ours) vs 0.33% (CMS)[^c]; pilot site Palisades is in group 5 (0.82% vs 0.61%); on group-5 medians the pilot is about −$44k a year ($0.66 per $1) and Palisades' return falls to $0.30 per $1, below Princeton's $0.54 | Favors the program; the second pilot site is not robust to it (C19) |
| Overall client estimate (B rows) | Overstated | Above CMS's FY2026 cut at all 8 hospitals; CMS's cuts on our payment base give $1.04M, not $1.23M (−16%)[^c] | Favors the program |
| Hip/knee imputation (A1) | Overstates hip/knee volume | ×1.33 vs CMS's actual counts (A1) | Small; surgery is outside the pilot |
| Wage index ignored (B3) | Understates NJ dollars | +6.6% payment per 0.1 of wage index above 1.0 (66% labor share, [Tables 1A–1E][t1])[^e]; the hospitals' own indexes are not in this repo | Against the program, but payment +15% still leaves the pilot at −$16k/yr[^m]; break-even needs about +30% (B3) |
| Uniform persistence (C13) | Unknown per hospital | Hospitals with lasting problems likely keep more than half their excess, noisy ones less | One-way tests from 0.35 to 1.0 do not flip the pilot |
| Trial effects shrink at scale (C4) | Overstates the effect | CCTP: no hospital-wide effect ([evaluation][cctp]); 13 of 15 Medicare care-coordination trials null ([Peikes 2009][peikes]) | Favors the program |
| TCM revenue not counted | Understates hospital net | CY2026 Medicare pays $122–$299 per qualifying service ([CMS RVU file][rvu]); uptake is low (C2) | Against the program |
| Sepsis measure (payment from FY2030) not modeled | Understates FY2030+ penalties | Raises CMS's national savings estimate by 47% ([FY2027 final rule][fr27]) | Raises the baseline; HF/PN savings unchanged |

Net: the larger biases mostly flatter the program, so the finding that it does not pay for itself survives them (exceptions: wage index, TCM revenue). One at a time, the pilot breaks even only with a 14% readmission reduction (C4; about 16% pooled), $236 per enrollee (C6), a 27% share of all payer savings (C11), +30% payment per case (B3) or full pass-through (C15).

[^c]: Computed for this log from CMS's FY2026 supplemental file and Table 15 (`data/external/`), joined on CCN and condition; re-estimates with `src/penalty.estimate`; client total = Σ our penalty × CMS cut (FY2026 or FY2027) ÷ our FY2026 cut.
[^d]: Counted in `data/processed/dim_hospital.parquet` and `fct_hospital_condition.parquet`; critical access matches by exact name and state in Hospital General Information.
[^e]: Arithmetic: top 30% = 14.0% high-risk (22.8% readmitted) + 16.0% intermediate (12.0%): (14.0 × 22.8 + 16.0 × 12.0) ÷ 30 = 17.0% vs 9.7% = 1.76×; $25,000 ÷ ($45.00 × 1.42) ≈ 390 h; $18,100 × 1.161 = $21,014; 1 ÷ 0.59 = 1.69; (2 ÷ 3) ÷ 0.59 = 1.13; $4,456.72 × 0.1 ÷ $6,752.61 = 6.6% per 0.1 of wage index.
[^m]: Computed for this log with `src/cost_model.evaluate` on the two pilot hospitals (`program_params("targeted")`), one input changed at a time; C19 evaluates each client hospital alone, as `analysis.pilot_hospitals` does.

[resdac]: https://resdac.org/articles/cms-cell-size-suppression-policy
[hsr]: https://qualitynet.cms.gov/files/6893aac2728800f196e92cb1?filename=FY-2026-HRRP-HSR-User-Guide.pdf
[t15-26]: https://www.cms.gov/files/zip/fy-2026-hospital-readmissions-reduction-program-payment-adjustment-factors.zip
[usc]: https://www.govinfo.gov/content/pkg/USCODE-2023-title42/html/USCODE-2023-title42-chap7-subchapXVIII-partE-sec1395ww.htm
[fn]: https://data.cms.gov/provider-data/sites/default/files/resources/f29bb7c812e242f6edfef0a4b7d0eaca_1760630713/Footnote_Crosswalk.csv
[cfr152]: https://www.ecfr.gov/api/versioner/v1/full/2026-10-01/title-42.xml?part=412&section=412.152
[infographic]: https://www.cms.gov/files/document/fy-2027-hrrp-infographic-pdf.pdf
[supp]: https://www.cms.gov/files/zip/fy2026-hospital-readmissions-reduction-program-supplemental-data-file.zip
[t1]: https://www.cms.gov/files/zip/fy2026-ipps-fr-table-1a-1e.zip
[t5]: https://www.cms.gov/files/zip/fy2026-ipps-fr-table-5.zip
[mup]: https://data.cms.gov/sites/default/files/2026-04/4517a6a1-adeb-4345-9f3d-a95391a470db/MUP_INP_RY26_P03_V10_DY24_Geo.CSV
[archives]: https://www.cms.gov/medicare/medicare-fee-for-service-payment/acuteinpatientpps/hrrp-archives
[fr26]: https://www.govinfo.gov/content/pkg/FR-2025-08-04/html/2025-14681.htm
[fr27]: https://www.govinfo.gov/content/pkg/FR-2026-08-04/html/2026-15833.htm
[fs27]: https://www.cms.gov/files/document/fy-2027-hrrp-fact-sheet-pdf.pdf
[bindman]: https://pmc.ncbi.nlm.nih.gov/articles/PMC6583218/
[cochrane]: https://pmc.ncbi.nlm.nih.gov/articles/PMC8867723/
[leppin]: https://pmc.ncbi.nlm.nih.gov/articles/PMC4249925/
[boggan]: https://pubmed.ncbi.nlm.nih.gov/39805113/
[ahrq]: https://www.ncbi.nlm.nih.gov/sites/books/NBK209244/table/discussion.t2/?report=objectonly
[bala]: https://jamanetwork.com/journals/jamanetworkopen/fullarticle/2840895
[zhong]: https://pmc.ncbi.nlm.nih.gov/articles/PMC8815439/
[tobiano]: https://pmc.ncbi.nlm.nih.gov/articles/PMC12136900/
[cpi]: https://fred.stlouisfed.org/graph/fredgraph.csv?id=CPIAUCNS
[cti]: https://jamanetwork.com/journals/jamainternalmedicine/fullarticle/410933
[cctp]: https://downloads.cms.gov/files/cmmi/cctp-final-eval-rpt.pdf
[ctrac]: https://pmc.ncbi.nlm.nih.gov/articles/PMC3520606/
[nuckols]: https://pmc.ncbi.nlm.nih.gov/articles/PMC5710454/
[bls-rn]: https://www.bls.gov/news.release/archives/ocwage_04022025.htm
[bls-ecec]: https://www.bls.gov/news.release/archives/ecec_09122025.htm
[hcup307]: https://hcup-us.ahrq.gov/reports/statbriefs/sb307-readmissions-2020.jsp
[hcup196]: https://www.hcup-us.ahrq.gov/reports/statbriefs/sb196-Readmissions-Trends-High-Volume-Conditions.jsp
[bea]: https://apps.bea.gov/national/Release/TXT/NipaDataA.txt
[medpac26]: https://www.medpac.gov/wp-content/uploads/2026/03/Mar26_Ch3_MedPAC_Report_To_Congress_SEC.pdf
[medpac25]: https://www.medpac.gov/wp-content/uploads/2025/03/Mar25_Ch3_MedPAC_Report_To_Congress_SEC.pdf
[roberts]: https://pubmed.ncbi.nlm.nih.gov/10029127/
[joshi]: https://pmc.ncbi.nlm.nih.gov/articles/PMC6596330/
[rupri]: https://rupri.public-health.uiowa.edu/publications/policybriefs/2026/MA_Enrollment_2025.pdf
[copss]: https://www.cms.gov/medicare/quality-initiatives-patient-assessment-instruments/hospitalqualityinits/downloads/statistical-issues-in-assessing-hospital-performance.pdf
[thompson]: https://pmc.ncbi.nlm.nih.gov/articles/PMC5134200/
[rvu]: https://www.cms.gov/files/zip/rvu26d-updated-08-26-2026.zip
[peikes]: https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi?db=pubmed&id=19211468,23340640&rettype=abstract&retmode=text
[dq8]: 03_data_quality_checks.md#8-joining-the-three-files
[dq104]: 03_data_quality_checks.md#104-hidden-discharge-counts
