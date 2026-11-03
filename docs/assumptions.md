# Assumptions log

This log lists every assumption behind the penalty estimate, the peer benchmarking and the business case for a post-discharge follow-up program, one per row, with its source or reasoning. Base values live in `config.yaml` and `seeds/condition_params.csv`; results come from `reports/key_metrics.json` unless a footnote says otherwise. Every uncertain input is varied in `docs/business_case.md` or the dashboard (page 5 Penalty Exposure, page 6 Intervention Business Case); the last column says how, or why a value is fixed. "Pilot" results there are for the targeted design at Inspira Mullica Hill and Palisades (hospital net −$33k a year, benefit-cost ratio $0.75 per $1); "broad" is the full program at all 8 hospitals (−$906k, $0.19 per $1). The 8 hospitals are an illustrative client group (D1), not an actual health system. ERR = excess readmission ratio; HF heart failure, PN pneumonia, AMI heart attack, CABG bypass surgery; FFS = fee-for-service Medicare; MA = Medicare Advantage. DQ checks are listed on dashboard page 2.

## A. Data handling

*Scope: Care Compare HRRP file, 3,055 hospitals × 6 conditions, performance period 2021-07-01 to 2024-06-30 (FY2026 program). Counts are hospitals or hospital × condition rows.*

| ID | Assumption | Base value (low–high if tested) | Source / reasoning | Where used (file) | Tested how |
|---|---|---|---|---|---|
| A1 | Discharge counts hidden by CMS are imputed | Midpoint of [25, 10 ÷ predicted rate] (low 25, high the upper bound) | CMS hides counts when readmissions are 1–10 ([ResDAC][resdac]) but shows the ERR, which needs ≥25 cases ([HSR guide][hsr]). 3,683 rows: 9.7% of discharges, 55% of hip/knee. The bound uses the predicted rate in place of the hidden observed rate, so it is approximate. | `sql/05_fct_hospital_condition.sql` | Low/high: national $275M / $317M (base $296M), client $1.17M / $1.29M. CMS validation in the table below. Dashboard page 5. |
| A2 | Maryland is excluded from penalties | 43 hospitals, out of penalty totals, thresholds and peer sets | Exempt from HRRP cuts under its all-payer model; absent from CMS Table 15 ([Table 15][t15-26]). | `sql/05_fct_hospital_condition.sql` | CMS validation: none is in CMS's FY2026 payment file[^c]. |
| A3 | Hospitals missing from Hospital General Information are excluded from penalties | 20 hospitals (15 with an ERR) | Closed, merged or converted since the period. 4 now have critical access hospital numbers (same name and state)[^d], which are outside HRRP ([42 USC 1395ww(q)][usc]); the other 16 were not checked one by one. | `sql/05_fct_hospital_condition.sql` | CMS validation: CMS penalized 13 of them in FY2026 (half of our 26 false negatives); including them adds $1.1M (0.4%) nationally[^c]. None is in NJ. |
| A4 | Rows with footnote 29 are kept | 377 rows at 85 hospitals[^d] | Partial-period data under a CMS-approved exception ([footnote crosswalk][fn]); CMS still uses these ERRs for payment. | `sql/02_stg_hrrp_readmissions.sql` | CMS validation: all 372 rows at payment-eligible hospitals appear with the same ERR; CMS penalized 181[^c]. |
| A5 | ERRs are used as published, not floored at 1.0 | Range 0.47–1.63 | Since FY2019 a condition is penalized when its ERR exceeds its peer-group median ([CMS methodology][infographic]), which is usually below 1.0. The regulation's ERR definition still says "not less than 1.0" ([42 CFR 412.152][cfr152]). | `sql/05_fct_hospital_condition.sql` | CMS validation: CMS's file has the same unfloored ERRs (difference 0.0000). Threshold 1.00 run (B2). |
| A6 | HRRP volume band stands in for hospital size | Low < 400, Mid 400–999, High ≥ 1,000 eligible FFS discharges over 3 years | No bed counts in these files. Near terciles: 949 / 891 / 937 scored payment-eligible hospitals[^d]. Volume also drives CMS shrinkage (C15). | `sql/06_dim_hospital.sql` | Definition only. No significant ERR difference by band in the adjusted regression. |

*Imputed vs CMS actual discharge counts, 3-year totals, for suppressed rows found in CMS's FY2026 supplemental file (`reports/tables/cms_validation_imputation.csv`).*

| Condition | Rows | Imputed ÷ actual | Actual inside [low, high] |
|---|---|---|---|
| HF | 303 | 0.90 | 79% |
| PN | 391 | 0.83 | 72% |
| COPD | 774 | 0.94 | 80% |
| AMI | 488 | 0.91 | 82% |
| CABG | 511 | 0.98 | 91% |
| Hip/knee | 1,168 | 1.33 | 96% |
| All | 3,635 | 1.09 | 86% |

Hip/knee volume is overstated by about a third. Using CMS's actual counts lowers the national total by 2.8% ($296M → $288M) and the client total by 2.5% ($30k, mostly one hip/knee row at Ocean Medical Center)[^c].

## B. Penalty formula

*Penalty per year = 0.9627 × Σ condition payments × max(ERR − threshold, 0), capped at 3% (`sql/07_mart_penalty_estimate.sql`, mirrored in `src/penalty.py`). Against CMS's actual FY2026 results for 2,937 hospitals: same penalized/not call for 97.1% (60 false positives, 26 false negatives); correlation of payment cuts 0.92.*

| ID | Assumption | Base value (low–high if tested) | Source / reasoning | Where used (file) | Tested how |
|---|---|---|---|---|---|
| B1 | Neutrality modifier | 0.9627 | CMS FY2026 value, the same for every hospital ([supplemental file][supp]); FY2027 is 0.9628. | `config.yaml` | Matches CMS. Fixed (published constant). |
| B2 | Penalty threshold = national median ERR per condition among payment-eligible hospitals | HF 0.999, PN 0.996, COPD 0.997, AMI 0.999, CABG 1.001, hip/knee 0.991 (alternative 1.00) | Proxy for CMS's dual-eligible peer-group medians, which Care Compare lacks. CMS's medians range 0.989–1.016 and, for the medical conditions, are highest in peer group 5, the most dual-eligible (`reports/tables/cms_validation_thresholds.csv`). So the national median overstates safety-net penalties. | `sql/05_fct_hospital_condition.sql` | Threshold 1.00: national $285M vs $296M, client $1.18M vs $1.23M. CMS validation: peer group 5 results flagged 61% (ours) vs 54% (CMS). Dashboard page 5. |
| B3 | Payment per case by condition | HF $8,523, PN $9,928, COPD $7,583, AMI $13,139, CABG $30,892, hip/knee $12,062 (±30%) | HF = standardized amount $6,752.61 ([Tables 1A–1E][t1]) × discharge-weighted HF DRG weight 1.262 ([Table 5][t5], [2024 case mix][mup]), wage index 1.0. Others = HF × CMS's median within-hospital payment per case relative to HF (`reports/tables/cms_payment_weights.csv`); cohorts include cases outside the core DRGs ([HRRP archives][archives]). DRG-only values stay in the seeds, unused. | `seeds/condition_params.csv` | ±30% table: national $207M–$385M, client $0.86M–$1.60M; the only ±30% input that flips the pilot (+30% → +$66/yr). Monte Carlo 0.85–1.20. Sliders, pages 5–6. |
| B4 | Annual volume = 3-year discharges ÷ 3 | 36-month window | The cut applies to one fiscal year's payments. COVID-19 patients (0.15%–2.5% of cases) are excluded until FY2027 ([FY2026 final rule][fr26]). | `sql/05_fct_hospital_condition.sql` | Covered by the ±30% payment range. |
| B5 | 3% cap on total base payments, estimated as HRRP-condition payments ÷ 0.133 | 0.133; cap 3% | CMS median sum of the six DRG payment ratios is 0.1329 ([supplemental file][supp]); the cap is statutory ([42 USC 1395ww(q)][usc]). Affects only the cap and the % cut. | `sql/07_mart_penalty_estimate.sql` | CMS validation: 10 hospitals at the cap vs 15; mean cut among penalized 0.46% vs 0.44%. Fixed. |
| B6 | A condition counts only if it has a published ERR | ≥25 eligible discharges | CMS rule for display ([HSR guide][hsr]) and payment ([FY2026 final rule][fr26]). MA patients will lift some conditions above 25 from FY2027; the model keeps today's set. | `sql/05_fct_hospital_condition.sql` | CMS validation: condition flags agree for 96.8%. |

## C. Business case

*From `config.yaml` (`intervention`) and `ProgramParams` in `src/cost_model.py` (see its docstring). The broad and targeted presets differ only in C1–C3; both reuse B1 and B3–B5. Hospital net = avoided penalty + shared savings − lost margin − program cost. Whole-system net = variable cost saved − program cost. Dollars are per year at steady state (FY2032).*

| ID | Assumption | Base value (low–high if tested) | Source / reasoning | Where used (file) | Tested how |
|---|---|---|---|---|---|
| C1 | Conditions enrolled | Broad: HF, PN, COPD, AMI, all hospital-conditions. Targeted: HF, PN, only above the threshold | HF and PN carry 74% of national excess readmissions and the best evidence (C5); penalty relief exists only above the threshold. Surgery has weak evidence. | `config.yaml` | Scenarios: broad $0.19 per $1, targeted at 8 hospitals $0.38, pilot $0.75. Dashboard page 6. |
| C2 | Share of eligible patients (FFS + MA) enrolled | Broad 50% (35%–65%); targeted 30% (21%–39%) | Design choice. 50% is ambitious: transitional care management (TCM) was billed after only 3%–7% of eligible discharges in 2013–2015 ([Bindman & Cox 2018][bindman]). | `config.yaml` | ±30% table, tornado, slider. |
| C3 | Readmission risk of enrollees vs average | Broad 1.0; targeted 1.5 (1.2–1.8) | HOSPITAL score (Donzé et al., JAMA Intern Med 2016): the top 38% by risk readmit at about 1.65× the average, the top 30% at about 1.76×[^e]; 1.5 allows for imperfect enrollment. | `src/cost_model.py` | Monte Carlo, slider. |
| C4 | Readmission reduction among enrollees | 10% (3%–20%) | RR 0.89 for discharge planning ([Cochrane 2022][cochrane]) and for trials since 2002 ([Leppin 2014][leppin]); post-discharge calls alone have no effect ([Boggan 2025][boggan]). | `config.yaml` | ±30% table, tornado, Monte Carlo. Break-even: pilot 14.0% (11.8% whole-system); broad none below 60%. |
| C5 | Effect by condition (× C4) | HF 1.2, PN 1.0, AMI 1.0, COPD 0.5, CABG and hip/knee 0.3 | HF evidence is strongest ([AHRQ 2014][ahrq]) but tempered from 15% to 12% after the PACT-HF trial found no significant effect (HR 0.93, 0.73–1.18; Van Spall et al., JAMA 2019). AMI and PN rest mostly on observational studies ([Balasubramanian 2025][bala]); COPD 30-day RR 0.95 ([Zhong 2022][zhong]); surgery inconclusive ([Tobiano 2025][tobiano]). | `src/cost_model.py` | Scales with C4; not varied alone. |
| C6 | Program cost per enrollee, 2024 dollars | $400 ($250–$700) | Middle of CPI-adjusted anchors ([CPI-U][cpi]): Care Transitions Intervention $334–$362 ([Coleman 2006][cti]), CCTP about $478 ([CCTP evaluation][cctp]), C-TraC about $519 ([Kind 2012][ctrac]), general programs $418–$733 ([Nuckols 2017][nuckols]). Includes frontline staff time. | `config.yaml` | ±30% table, tornado, Monte Carlo. Break-even: pilot $236; broad $8. |
| C7 | Fixed cost per hospital per year | $25,000 ($10,000–$60,000) | Oversight and reporting only: about 390 hours of RN time at $45.00/h ([BLS][bls-rn]) × 1.42 benefits load ([BLS ECEC][bls-ecec])[^e]. | `config.yaml` | ±30% table, tornado, Monte Carlo, slider. |
| C8 | Hospital cost of one readmission | $19,000 ($13,300–$24,700) | HCUP Medicare $18,100 in 2020 ([SB #307][hcup307]) × 1.161 ([BEA hospital prices][bea]) ≈ $21,000; 2013 condition figures ([SB #196][hcup196]) × 1.318 ≈ $16,000–$19,000[^e]. Base at the top of the condition range. | `config.yaml` | ±30% table, tornado, slider. Not in the Monte Carlo. |
| C9 | Payment ÷ cost of a readmission | 0.892 | FFS Medicare margin −12.1% ([MedPAC 2026][medpac26]), so payment = cost ÷ 1.121. Per avoided readmission payers save $16,948 and the hospital loses $1,748 of margin. Also applied to MA patients. | `config.yaml` | Bounded by the beds-refilled scenario (C12). |
| C10 | Variable share of a readmission's cost | 0.80 (0.60–0.90) | MedPAC: 75%–85% of hospital costs vary with volume ([MedPAC 2025][medpac25]). Stress case: 16% short-run ([Roberts 1999][roberts]). | `config.yaml` | ±30% table (its 1.04 means "all variable"), tornado, Monte Carlo. At 16%: pilot −$122k, whole-system −$108k[^m]. |
| C11 | Payer savings shared with the hospital | 0% (scenario 30%) | No shared-savings contract assumed. | `config.yaml` | Break-even share 27%. Scenario 30%: pilot +$4k/yr ($1.03 per $1), 6-year total −$306k. Slider. |
| C12 | Freed beds are not refilled | No (scenario: yes) | Occupancy unknown, so lost margin stays. | `config.yaml` | Scenario: pilot −$20k/yr ($0.84 per $1). |
| C13 | Persistence of today's ERR excess (regression to the mean) | 0.5 (0.3–0.8; scenario 1.0) | Regression to the mean explained 74%–87% of improvement at penalized hospitals ([Joshi 2019][joshi]). CMS's FY2027 cuts kept 0.58 of FY2026 cuts (`reports/tables/cms_validation_persistence.csv`), but those windows share 12 months and FY2029+ windows share none. Lowers the group's expected penalty from $1.23M to $0.64M. | `src/cost_model.py` | ±30% table, tornado, Monte Carlo. Scenario 1.0: pilot −$23k/yr ($0.83 per $1). |
| C14 | MA share of Medicare patients | NJ 41% (30%–55%); national 54% | NJ 41.1% ([RUPRI 2025][rupri]); national 54% (KFF, July 2025). From FY2027 MA patients count in the ERR but the cut applies to FFS payments only ([CMS fact sheet][fs27]), so enrollment and cost scale by 1 ÷ (1 − MA share), 1.69×[^e]. Each hospital is assumed to have its state's share. | `src/cost_model.py` | ±30% table, tornado, Monte Carlo. FY2026-rules scenario (no MA, 3 years): broad −$509k vs −$906k. |
| C15 | Pass-through n ÷ (n + k), n = 2-year all-Medicare cohort | k: HF 369, PN 414, COPD 396, AMI 370, CABG 228, hip/knee 192 | CMS shrinks low-volume hospitals toward 1.0 ([COPSS-CMS][copss]). k is fitted on FY2026 rows with published counts (R² ≥ 0.99); HF at 1,019 cases gives 0.73 vs the 0.70 reliability mark ([Thompson 2016][thompson]). Reuse under FY2027 rules is an assumption; the NJ 2-year cohort is about 1.13× today's 3-year FFS count[^e]. | `src/shrinkage.py` | Full pass-through: pilot +$26k/yr ($1.20 per $1)[^m]. Dashboard toggle; DQ check P6. |
| C16 | CMS window from FY2027 | 2 years, July N−4 to June N−2 | CMS rule ([42 CFR 412.152][cfr152]). A January 2027 start covers 12% of the FY2029 window, 50% of FY2030, 88% of FY2031, 100% of FY2032. | `src/cost_model.py` | FY2026-rules scenario (C14); phase-in chart, page 6. |
| C17 | Timing and discounting | Start 2027-01-01; 50% strength for 12 months; FY2027–FY2032; 7% | Go-live after the next budget cycle; 7% is a judgment of cost of capital. | `config.yaml` | Not varied. The pilot loses money every year, so no rate flips it. |
| C18 | Monte Carlo | 2,000 runs, triangular, seed 42 | Varies C3, C4, C6, C7, C10, C13, C14 and payment scale independently; ranges skew toward higher cost. | `src/cost_model.py` | Reproducible (DQ check P5). Pilot positive in 11.9% of runs (whole-system 22.7%); 5th–95th percentile −$127k to +$19k. |
| C19 | Pilot hospitals | Top 2 by targeted benefit-cost ratio: Inspira Mullica Hill $0.96, Palisades $0.50[^m] | Rank on the penalty the program can address. The group's largest penalty, at Princeton, is mostly hip/knee, and its actual CMS cut fell from 0.88% (FY2026) to 0.04% (FY2027). | `src/analysis.py` | All 8 hospitals: $0.38 per $1. Dashboard selector. |

## D. Client group and benchmarking

*Scope: payment-eligible hospitals; FY2026 ERRs.*

| ID | Assumption | Base value (low–high if tested) | Source / reasoning | Where used (file) | Tested how |
|---|---|---|---|---|---|
| D1 | Client group drawn by a fixed rule | NJ, payment-eligible, ≥3 scored conditions; 3 High, 3 Mid, 2 Low volume; numpy `default_rng(42)` | CMS data has no health-system membership, so the group is illustrative, not an actual health system. 3/3/2 over-weights smaller hospitals against the 36/15/8 pool[^d] so every band appears. | `src/client.py` | DQ check P4 reproduces the IDs in `config.yaml`. |
| D2 | New Jersey as the state | Mean ERR 1.028, 2nd of 50 state groups; 93% penalized | A high-penalty setting for the request. Massachusetts (1.034) has no qualifying Low-volume hospital[^d]. Not an average state. | `config.yaml` | Dashboard page 5 takes any state. |
| D3 | Peers for benchmarking | Same ownership group (3) and HRRP volume band; payment-eligible; target excluded | The comparisons requested; the same band keeps shrinkage comparable (C15). Not CMS's dual-eligible peer groups (B2). Target 310010 has the group's largest penalty. | `src/benchmarking.py` | 707 peers for the target (520–704 per condition); fewer than 10 is flagged. Page 4 can add region or emergency-department status. |
| D4 | Percentile vs peers | % of peers with a lower ERR; ≥75 "worse than most", ≤25 "better than most" | Rank-based; ties count as not lower. Hospital level uses the discharge-weighted readmission index. | `src/benchmarking.py` | Definition only. |

## Known biases and their direction

*Likely effect of each simplification on the client-group results. "Favors the program" means it makes the program look better than it probably is.*

| Bias | Direction | Size or evidence | Effect on the conclusion |
|---|---|---|---|
| National-median threshold (B2) | Overstates safety-net penalties | Peer group 5 mean cut 0.46% (ours) vs 0.33% (CMS)[^c]; pilot site Palisades is in group 5 (0.82% vs 0.61%) | Favors the program |
| Overall client estimate (B rows) | Overstated | Above CMS's FY2026 cut at all 8 hospitals; CMS's cuts on our payment base give $1.04M, not $1.23M (−16%)[^c] | Favors the program |
| Hip/knee imputation (A1) | Overstates hip/knee volume | ×1.33; actual counts lower the national total 2.8%, the client total 2.5% | Small; surgery is outside the pilot |
| Wage index ignored (B3) | Understates NJ dollars | About 10%–15% if NJ wage indexes are 1.15–1.23 (66% labor share, [Tables 1A–1E][t1])[^e] | Against the program; +15% still leaves the pilot at −$16k/yr[^m] |
| Uniform persistence (C13) | Unknown per hospital | Hospitals with lasting problems keep more than half their excess, noisy ones less | One-way tests from 0.35 to 1.0 do not flip the pilot |
| Trial effects shrink at scale (C4) | Overstates the effect | CCTP: no hospital-wide effect ([evaluation][cctp]); 13 of 15 Medicare care-coordination trials null ([Peikes 2009][peikes]) | Favors the program |
| TCM revenue not counted | Understates hospital net | CY2026 Medicare pays $122–$299 per qualifying service ([CMS RVU file][rvu]); uptake is low (C2) | Against the program |
| Sepsis measure (payment from FY2030) not modeled | Understates FY2030+ penalties | Raises CMS's national savings estimate by 47% ([FY2027 final rule][fr27]) | Raises the baseline; HF/PN savings unchanged |

Net: the larger biases mostly flatter the program, so the finding that it does not pay for itself survives them; the exceptions are the wage index and TCM revenue. One at a time, the pilot reaches break-even only with a 14% readmission reduction (C4), $236 per enrollee (C6), 27% of payer savings shared back (C11), +30% payment per case (B3) or full pass-through (C15).

[^c]: Computed for this log from CMS's FY2026 supplemental file and Table 15 (`data/external/`), joined on CCN and condition. Re-estimates use `src/penalty.estimate`. Client total = Σ our penalty × CMS cut ÷ our cut; peer-group means from `data/processed/cms_validation_hospital.parquet`.
[^d]: Counted in `data/processed/dim_hospital.parquet` and `fct_hospital_condition.parquet`; critical access matches by exact name and state in the Hospital General Information file.
[^e]: Arithmetic: (14.0% × 22.8% + 16.0% × 12.0%) ÷ 30% = 17.0% vs 9.7% = 1.76×; $25,000 ÷ ($45.00 × 1.42) ≈ 390 h; $18,100 × 1.161 = $21,014; ($12,186 to $14,478) × 1.318 = $16,061 to $19,082; 1 ÷ 0.59 = 1.69; (2 ÷ 3) ÷ 0.59 = 1.13; $4,456.72 × 0.1 ÷ $6,752.61 = 6.6% per 0.1 of wage index.
[^m]: Computed for this log with `src/cost_model.evaluate` on the pilot inputs (`analysis.model_inputs` for the two pilot hospitals, `program_params("targeted")`), one input changed at a time; C19 runs it per client hospital, as `analysis.pilot_hospitals` does.

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
