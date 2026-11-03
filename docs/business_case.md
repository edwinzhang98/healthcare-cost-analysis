# Business case: post-discharge follow-up program

**For:** VP of Quality and CFO · **Decision:** whether to fund a post-discharge follow-up program in the next budget cycle, and where · **Date:** November 2026 · **Request:** question 4 in [01_request_and_scope.md](01_request_and_scope.md)

> **Illustrative client group.** "The group" is an **illustrative client group** of 8 New Jersey acute care hospitals drawn by a seeded rule (3 High, 3 Mid, 2 Low HRRP volume band; seed 42; `config.yaml`), **not an actual health system**; CMS data does not record system membership. Names only make the example concrete; results are model estimates from public data, not the hospitals' finances; owners and roles below are illustrative; nothing implies a relationship or contract with these hospitals or their payers.

**Scope and conventions**
- **Data.** CMS Care Compare, 3,055 hospitals: HRRP for the FY2026 program (discharges Jul 2021–Jun 2024), Medicare Spending per Beneficiary (CY2024), Hospital General Information. Our penalty estimate matches CMS's actual FY2026 penalized-or-not decision for 97% of hospitals.
- **Rules.** A program starting in 2027 is scored under the FY2027+ rules: a 2-year window, Medicare Advantage (MA) patients counted in the score, and the penalty charged only on traditional Medicare (fee-for-service, FFS) payments.
- **Money.** US dollars a year in a full-strength year (FY2032) unless labeled; current prices; six-year totals undiscounted unless marked NPV (7%).
- **Terms.** *ERR* (excess readmission ratio): CMS's predicted ÷ expected 30-day readmission rate, by hospital and condition. *Penalty threshold:* the national median ERR per condition (CMS uses dual-eligible peer-group medians, not published in Care Compare). *HRRP volume band:* eligible FFS discharges over 3 years (Low < 400, Mid 400–999, High ≥ 1,000), not hospital size.
- **Numbers:** `reports/key_metrics.json` and `data/processed/bc_*.parquet` (`python run.py`); figures computed for this document carry a note. Assumptions and citations: [assumptions.md](assumptions.md); interactive version: dashboard page 6.

## 1. Executive summary

- **A group-wide program does not pay for itself through penalties.** The broad design (heart failure, pneumonia, COPD and heart attack; half of all Medicare patients; all 8 hospitals) would cost about $1.12M a year to avoid about $292K of penalty at full strength: $0.19 back per $1, a hospital net of −$906K a year. It costs more than the group's entire expected penalty ($644K a year), so no effect size makes it break even; nationally it would pay back at none of the 2,688 hospitals where it could run.
- **The best-placed pilot returns about $0.75 per $1.** A targeted program for higher-risk heart failure and pneumonia patients at Inspira Medical Center Mullica Hill and Palisades Medical Center would cost about $130K a year, prevent about 7 readmissions and avoid about $110K of penalty a year at full strength (hospital net −$33K a year). CMS's window closes 15 months before each payment year, so relief starts in FY2029 and reaches full strength in FY2032; the pilot does not pay back within FY2027–FY2032 (cumulative hospital net −$501K).
- **Break-even needs more than the evidence supports.** For the hospital the pilot breaks even only if it cuts readmissions among enrolled patients by about 16% (a 14.0% base effect with heart failure at 1.2 times; base case 10%, recent trials about 11%), costs ≤ $236 per patient (base $400), or payers return ≥ 27% of all their savings. Only 1 of 18 one-at-a-time ±30% changes reaches break-even (payment per discharge +30%), and 12% of 2,000 Monte Carlo runs end positive.
- **For payers and hospital together the pilot is close but negative:** −$20K a year (broad: −$479K), positive in 23% of Monte Carlo runs. Penalties and FFS payments are transfers between them; what remains is $15,200 of hospital cost saved per avoided readmission against $17,900 of program cost. Payers save about $16,900 per avoided readmission, the basis for asking them to co-fund.
- **Recommendation: no group-wide program; a measured two-year pilot only on quality grounds,** with a concurrent comparison group and a co-funding request to the Medicare Advantage plans and ACO partners the group contracts with. **Month 12 (stop or continue):** ≥ 80% of enrolled patients receive all three components, ≥ 90 enrolled, variable cost ≤ $400 per patient, and no rise in ED visits, observation stays, mortality or readmissions vs the comparison group. **Month 24 (keep or stop):** make it permanent only if the pooled reduction is ≥ 16% at ≤ $400 per patient, or ≥ 12% with ≥ 27% payer co-funding or at ≤ $236 per patient. The pilot is too small to prove such an effect statistically (Section 9.3).

## 2. The program

A three-part transitional care bundle for higher-risk heart failure and pneumonia patients; all three parts are required: (1) **medication review before discharge** by a pharmacist or nurse; (2) **a nurse contact within 72 hours**, by phone or home visit, on symptoms, medicines and the follow-up appointment; (3) **a clinic visit within 7 days**, booked before the patient leaves.

**Not phone-only.** Contacts within 7 days of discharge, almost all single phone calls, showed no effect on 30-day readmissions (risk difference 0.00, 95% CI −0.02 to 0.02; Boggan 2025). In heart failure, telephone support and telemonitoring did not reduce all-cause readmissions; home visits and multidisciplinary clinics did (AHRQ/Feltner 2014; Van Spall 2017). How many components are needed is unsettled (Leppin 2014; Tyler 2023). In observational studies, follow-up within 7 days was associated with fewer readmissions for patients 65+ with heart failure or heart attack (Balasubramanian 2025).

**Who is enrolled (pilot).** Medicare patients 65+, FFS and MA, discharged alive with heart failure or pneumonia where the hospital's ERR is above the threshold (heart failure at Inspira Mullica Hill, whose pneumonia ERR of 0.995 is just below the 0.996 threshold; both conditions at Palisades), and only the highest-risk 30% by a risk score at discharge, assumed to carry 1.5 times the average risk (range 1.2–1.8; C3, Donzé 2016). That is about 200 patients a year (114 at Inspira Mullica Hill; 37 heart failure and 50 pneumonia at Palisades), of whom about 31% (63 a year) would be readmitted within 30 days without the program; the base case prevents about 7.[^power]

**Why heart failure and pneumonia.**
- **Size:** 74% of national excess readmissions and 54% of estimated penalty dollars. In the group's FY2026 estimate, heart failure is the largest condition ($511K) and the two are $687K of $1.23M (56%).[^calc] Larger volumes also let more of an improvement reach the score (Section 3.5).
- **Weight:** the largest DRG payment ratios of the six conditions (medians 4.6% for pneumonia and 3.6% for heart failure of base operating DRG payments; CMS FY2026 supplemental file).
- **Evidence:** heart failure has the strongest trials, so it gets 1.2 times the base effect (12%); pneumonia rests on discharge-planning trials in older medical patients (Cochrane 2022: RR 0.89 within about 3 months) and observational studies, so it gets the base 10%.
- **Left out:** COPD shows no significant effect on 30-day all-cause readmission (Zhong 2022: RR 0.95, 95% CI 0.76–1.19). Bypass and hip/knee surgery have sparse, inconclusive evidence (Tobiano 2025). For heart attack only 13–45% of an improvement would reach the score at the group's hospitals, and the evidence is mostly observational.

**The comparison ("broad") design** is the program as first proposed: half of all Medicare patients with heart failure, pneumonia, COPD or heart attack at all 8 hospitals, at average risk, whatever each hospital's score.

## 3. How the money works

Penalties and payments are transfers between hospital and payers (Section 3.1). Four mechanics shrink the money at stake or the share a program captures: lost margin, the FY2027 MA rule, regression to the mean and partial credit for smaller hospitals.

### 3.1 Two perspectives

| View | Formula (annual US dollars) | Question it answers |
|---|---|---|
| **Hospital net** | avoided penalty + payer savings returned − margin lost on avoided readmissions − program cost | What does the hospital P&L see? (CFO) |
| **Whole-system net** | hospital variable cost saved on avoided readmissions − program cost | Is this a good use of resources for payers and hospital together? |

In the whole-system view a penalty dollar the hospital avoids is a dollar Medicare no longer collects, and a payment the payer saves is revenue the hospital loses, so both cancel. Patients' health gains are real but are not valued in dollars in either view. **Benefit-cost ratio** = (avoided penalty + payer savings returned − lost margin) ÷ program cost: dollars back to the hospital per $1 spent. It is not ROI; $0.75 means the hospital loses 25 cents per $1.

### 3.2 Money per avoided readmission

Table 1. Money flows per avoided 30-day readmission (US dollars, base case, all payers).

| Item | Formula | Amount |
|---|---|---|
| Hospital cost of one readmission (C) | 2025 dollars, chosen between HCUP condition-level and all-condition Medicare costs (Table 2, C8) | $19,000 |
| Payer saves the payment (P) | 0.892 × C | $16,948 |
| Hospital loses P but saves its variable cost (V) | 0.80 × C | $15,200 |
| Hospital's lost margin | P − V | $1,748 (zero if the freed bed is refilled) |
| Payers and hospital together save | V | $15,200 |

Sources: Table 2 (C8–C10). MA plans are assumed to pay close to traditional Medicare rates.

### 3.3 FY2027+ rules: MA patients count in the score, not in the penalty base

From FY2027 CMS scores a 2-year window, counts MA patients in the ERR, and still charges the penalty only on FFS base operating DRG payments (FY2026 IPPS final rule; CMS FY2027 HRRP fact sheet). With 41% of New Jersey's Medicare patients in MA (RUPRI Center 2026), each enrolled patient, whatever the payer, moves the score about 59% as much as an FFS patient did under the FY2026 rules. The program enrolls by risk, not payer (a design choice, not a necessity), so cost scales with all Medicare patients (about 1.7 times the FFS volume) while the penalty base does not; enrolling 30% of FFS patients only would cut variable cost and relief by 41% but not the $50K fixed cost (hospital net −$40K a year, not −$33K).[^calc] Under the FY2026 rules the pilot would roughly break even (−$0.3K a year, $1.00 per $1); the broad program would still lose $509K a year (Table 3).[^fy26]

### 3.4 Regression to the mean: the baseline is a forecast

- Hospitals with the highest ERR today tend to look better later with no program. In CMS's actual payment cuts (2,894 hospitals in both years), each hospital's FY2027 cut ≈ 0.58 × its FY2026 cut + 0.16 percentage points (correlation 0.57): penalties drift back toward the average. The tenth of hospitals with the largest FY2026 cuts went from a mean cut of 1.38% to 0.96% (about −30%), and 40% of them lost more than half of it, while small cuts grew. The overall mean barely moved (0.346% to 0.356%; 0.439% to 0.423% among hospitals penalized in FY2026).[^pers] Part of the slope reflects the FY2027 rule change (MA patients, 2-year window) and the 12 months the two windows share (Jul 2023–Jun 2024). Joshi 2019 attributes 74–87% of the ERR improvement at penalized hospitals to regression to the mean.
- FY2029+ windows share no months with today's data, so the baseline keeps half of today's excess: forecast ERR = 1 + 0.5 × (ERR − 1), likewise for the observed rate (**persistence** 0.5; range 0.3–0.8). This roughly halves the penalty at stake ($644K a year for the group instead of the FY2026 estimate of $1.23M; $249K instead of $485K at the two pilot hospitals) but changes the avoidable penalty much less, because the program lowers the ERR by about the same amount either way: with persistence 1.0 the pilot would avoid $122K a year instead of $110K ($0.83 instead of $0.75 per $1).
- A before-and-after comparison would credit the program with improvement that would have happened anyway (Section 9.3).

### 3.5 Pass-through: smaller hospitals get partial credit

CMS's hierarchical model pulls low-volume hospitals toward 1.0 (COPSS-CMS 2012), so only part of an actual change in readmissions reaches the score. We fitted this **pass-through** on the FY2026 file as n ÷ (n + k), with k = 369 for heart failure and 414 for pneumonia (R² 0.997–0.998): about 20% of a change reaches the score at 100 discharges and about 80% at 1,500. At 1,019 heart failure cases it gives 0.73, close to the 0.70 reliability reported by Thompson 2016.

- **Basis.** For a program scored under the FY2027+ rules, n is the 2-year all-Medicare cohort: annual FFS discharges ÷ (1 − MA share) × 2, about 1.13 times the 3-year FFS count. On this basis the pilot rows get 0.673 (Inspira Mullica Hill, heart failure), 0.400 (Palisades, heart failure) and 0.447 (Palisades, pneumonia). On the 3-year FFS basis of the data window, used for benchmarking, the same rows get 0.645, 0.371 and 0.417. Under the broad design The University Hospital (Low volume) would get 9–15%.
- With full credit the pilot would appear to make +$26K a year ($1.20 per $1) instead of losing $33K.[^calc]

## 4. Assumptions

Low and high values are the triangular ranges used in the Monte Carlo (Section 7.5), or ±30% where marked. IDs match [assumptions.md](assumptions.md), which gives the reasoning and full citations; values are in `config.yaml`.

Table 2. Model inputs: base, low and high values, and main sources.

| ID | Input | Base | Low | High | Main source |
|---|---|---|---|---|---|
| C1 | Conditions enrolled | Broad: HF, PN, COPD, AMI, all hospital-conditions. Targeted: HF, PN above the threshold | – | – | Section 2 |
| C2 | Share of eligible patients (FFS and MA) enrolled | 30% pilot; 50% broad | 21%; 35% (±30%) | 39%; 65% (±30%) | Design choice; 50% is ambitious (transitional care management, TCM, was billed after 3–7% of eligible discharges; Bindman & Cox 2018) |
| C3 | Risk of enrolled patients vs condition average | 1.5× pilot; 1.0× broad | 1.2× | 1.8× | HOSPITAL score: top 38% by risk ≈ 1.65×, top 30% ≈ 1.76× (Donzé 2016); less for imperfect enrollment |
| C4 | Readmission reduction among enrolled (base effect) | 10% | 3% | 20% | RR 0.89: trials since 2002 (Leppin 2014), discharge planning (Cochrane 2022). Low: CCTP; Peikes 2009. High: all 42 trials, RR 0.82 (Leppin 2014) |
| C5 | Effect by condition (× base) | HF 1.2; PN, AMI 1.0; COPD 0.5; CABG, hip/knee 0.3 | – | – | AHRQ/Feltner 2014; Van Spall 2017; HF tempered from 15% to 12% after PACT-HF (Van Spall 2019); Balasubramanian 2025; Zhong 2022; Tobiano 2025 |
| C6 | Variable cost per enrolled patient (2024 $) | $400 | $250 | $700 | CPI-adjusted: Coleman 2006 $334–$362, CCTP ≈ $478, Kind 2012 ≈ $519, Nuckols 2017 $418–$733 |
| C7 | Fixed cost per hospital per year | $25,000 | $10,000 | $60,000 | Oversight and reporting: ≈ 390 RN hours at $45.00/h × 1.42 benefits load (BLS) |
| B3 | Payment per discharge (penalty size) | 100% (HF $8,523; others scaled by CMS median payment ratios) | 85% | 120% | FY2026 IPPS rates; CMS FY2026 supplemental file |
| C8 | Hospital cost of a readmission (2025 $) | $19,000 | $13,300 (±30%) | $24,700 (±30%) | Between HCUP condition-level Medicare costs (2013, Brief #196) × 1.318 = $16.1K–$19.1K for COPD, PN, HF and AMI, and the septicemia-heavy all-condition 2020 average ($18,100, Brief #307) × 1.161 ≈ $21.0K (BEA hospital prices)[^cost] |
| C9 | Payment ÷ hospital cost | 0.892 | – | – | MedPAC: FFS margin −12.1% (FY2024); also applied to MA |
| C10 | Variable share of hospital cost | 80% | 60% | 90% | MedPAC: 75–85%; short-run stress case 16% (Roberts 1999) |
| C11, C12 | Payer savings returned; freed beds refilled | 0%; no | – | 30%; yes (scenarios) | No shared-savings contract assumed; occupancy unknown |
| C13 | Persistence of today's ERR excess | 0.5 | 0.3 | 0.8 | Joshi 2019; CMS cuts: slope 0.58 with a +0.16-point intercept, partly from 12 overlapping months (Section 3.4) |
| C14 | MA share of Medicare patients | 41% | 30% | 55% | New Jersey 41.1% (RUPRI Center 2026), all 8 hospitals; national 54% (KFF 2025) for the national view |
| C15 | Pass-through | n ÷ (n + k), n = 2-year all-Medicare cohort | – | 100% (scenario) | FY2026 HRRP file (`src/shrinkage.py`); Thompson 2016 |
| C16, C17 | Timing | 2-year window from FY2027; start 2027-01-01; half strength for 12 months; FY2027–FY2032; 7% discount rate | – | – | 42 CFR 412.152; 7% is a judgment |
| B1, B2, B5 | CMS formula | FY2027+ rules; neutrality modifier 0.9627; national-median threshold; 3% cap | FY2026 rules (scenario) | – | 42 CFR 412.152 and 412.154; CMS FY2026 supplemental file |

## 5. Results

No design pays for itself on the hospital P&L without payer co-funding. The pilot comes closest at $0.75 per $1, and only a 30% shared-savings contract lifts it above $1.

### 5.1 Scenarios

Table 3. Scenarios, full-strength year (US$ thousands a year except readmissions and the ratio; FY2027+ rules unless noted). Expected penalty = FY2029+ forecast without a program, with regression to the mean (our FY2026 estimate: 1,231 for the group, 485 at the pilot hospitals). Avoided = steady state once the program fills the CMS window. Six-year = FY2027–FY2032 hospital net with the Section 6 phase-in, undiscounted; no scenario pays back by FY2032.

| Scenario | Cost | Expected penalty | Avoided | Readmissions avoided | Hospital net | Whole-system net | Benefit-cost ratio | Six-year hospital net |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Broad, all 8 | 1,124 | 644 | 292 | 42.4 | −906 | −479 | $0.19 | −5,584 |
| Targeted, all 8 | 475 | 644 | 218 | 21.1 | −294 | −154 | $0.38 | −2,184 |
| **Targeted pilot (2 hospitals)** | **130** | **249** | **110** | **7.3** | **−33** | **−20** | **$0.75** | **−501** |
| Pilot + 30% shared savings | 130 | 249 | 110 | 7.3 | +4 | −20 | $1.03 | −306 |
| Pilot, persistence 1.0 (no regression to the mean) | 130 | 485 | 122 | 8.1 | −23 | −8 | $0.83 | −479 |
| Pilot, freed beds refilled | 130 | 249 | 110 | 7.3 | −20 | −20 | $0.84 | −434 |
| Broad, FY2026 rules | 745 | 644 | 280 | 25.0 | −509 | −365 | $0.32 | −3,470 |

- **Targeting matters more than scale:** at the same 8 hospitals the targeted design costs 42% as much as the broad one and keeps 75% of its avoided penalty, doubling the return per $1 ($0.19 → $0.38); the two best-placed hospitals double it again.
- **Only shared savings gets above $1 per $1** (+$4K a year at 30%), and the six-year total is still −$306K because costs start in 2027 and relief in FY2029; paying back by FY2032 would need payers to return about 77%.[^payback]
- **Refilled beds or no regression to the mean help, but not enough** ($0.84, $0.83). **The FY2027 rules are not why the broad program fails:** under the FY2026 rules it still loses $509K a year.

### 5.2 Why the pilot falls short: economics per readmission avoided

Table 4. Per readmission avoided, full-strength year (US dollars, rounded to $10).[^unit]

| | Targeted pilot | Broad, all 8 |
|---|---:|---:|
| Patients enrolled | 28 | 54 |
| Program cost | $17,900 | $26,510 |
| Penalty avoided | $15,120 | $6,890 |
| Margin lost | $1,750 | $1,750 |
| **Hospital net** | **−$4,530** | **−$21,370** |

Our national estimates put the penalty at about $41,500 per excess heart failure readmission and $58,900 per excess pneumonia readmission, 4.9 and 5.9 times the payment for the stay (hip/knee: about 18 times). These multiples are relative to the payment for the stay, not its cost; MedPAC (June 2018) reported almost 5 for heart failure and more than 20 for hip/knee replacement under the pre-FY2019 formula. A program captures much less: CMS gives partial credit (pass-through 0.40–0.67 at the pilot hospitals, FY2027+ cohort basis), and MA patients enlarge the score's base but not the penalty's (Section 3.3). Meanwhile the program enrolls about 28 higher-risk patients per readmission prevented, at about $650 each including fixed costs.

### 5.3 The pilot hospital by hospital

Table 5. Targeted pilot by hospital, full-strength year (US$ thousands a year unless noted).

| Hospital (volume band) | Conditions | Patients/yr | Cost | FY2026 penalty | Expected | Avoided | Readmissions avoided/yr | Hospital net | Whole-system net | Benefit-cost ratio |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Inspira Mullica Hill (High) | HF | 114 | 70.5 | 373.1 | 191.0 | 75.5 | 4.5 | −2.8 | −2.8 | $0.96 |
| Palisades (Mid) | HF, PN | 87 | 59.8 | 111.7 | 58.5 | 34.6 | 2.8 | −30.2 | −16.8 | $0.50 |
| **Pilot total** | | **201** | **130.3** | **484.8** | **249.5** | **110.1** | **7.3** | **−33.0** | **−19.7** | **$0.75** |

Table 6. How the program moves each score (steady state; pass-through on the FY2027+ cohort basis). Peer percentile = share of peers (same ownership group and volume band) with a lower FY2026 ERR.

| Hospital | Condition | FY2026 ERR | Peer percentile | Forecast ERR, no program | ERR with program | Threshold | Pass-through | Enrolled/yr | Avoided/yr |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Inspira Mullica Hill | Heart failure | 1.173 | 98.9 | 1.087 | 1.046 | 0.999 | 0.673 | 114 | 4.5 |
| Palisades | Heart failure | 1.113 | 96.1 | 1.057 | 1.032 | 0.999 | 0.400 | 37 | 1.5 |
| Palisades | Pneumonia | 1.038 | 77.1 | 1.019 | 0.998 | 0.996 | 0.447 | 50 | 1.3 |

On national medians all three stay above the threshold after the program, so every point of ERR reduction counts; Palisades pneumonia ends just above it, and improvement below the threshold saves no penalty. On CMS's FY2026 peer-group medians (Palisades' group, the most dual-eligible: heart failure 1.016, pneumonia 1.010) Palisades pneumonia would end below the threshold: Palisades' expected penalty would be $34K, its net −$42K and the pilot's −$44K a year ($0.66 per $1).[^calc]

**Why these two hospitals.** They return the most per $1, which ranks hospitals on the penalty this program can address rather than on total penalty (ranking on last year's total tends to pick hospitals at their peak). The second site rests on the threshold proxy: on each hospital's own peer-group medians, Palisades by itself returns $0.30 per $1 (5th of 8, behind Princeton $0.54, Monmouth $0.35 and Ocean $0.31); Inspira stays first.

Table 7. Targeted design at each client hospital alone, ranked by benefit-cost ratio (full-strength year; US$ thousands a year).[^sites]

| Rank | Hospital (volume band) | FY2026 penalty | Hospital net | Benefit-cost ratio |
|---:|---|---:|---:|---:|
| 1 | Inspira Mullica Hill (High) | 373 | −2.8 | $0.96 |
| 2 | Palisades (Mid) | 112 | −30.2 | $0.50 |
| 3 | Princeton Plainsboro (High) | 384 | −61.2 | $0.36 |
| 4 | Monmouth (Mid) | 75 | −27.7 | $0.35 |
| 5 | Jersey City (Mid) | 86 | −33.2 | $0.32 |
| 6 | Ocean (High) | 148 | −81.0 | $0.14 |
| 7 | Virtua Willingboro (Low) | 43 | −29.6 | $0.14 |
| 8 | The University Hospital (Low) | 11 | −28.0 | $0.02 |

- Princeton Plainsboro has the group's largest estimated FY2026 penalty but ranks third: 65% of it ($249K) is hip/knee replacement, which this program does not address (Section 8).
- Most of the pilot's modeled value is at Inspira Mullica Hill, which alone would lose about $3K a year; its FY2027 CMS cut is about half our baseline there, so the site split needs checking before go-live (Table 14). Palisades adds $30K a year of net cost, 87 patients a year (76% more to measure) and a Mid volume setting.
- Even at a 20% effect only Inspira Mullica Hill would pay back alone ($1.92 per $1); Palisades would reach $0.70 and the other six $0.62 or less, with Princeton and Ocean worse than at 10% ($0.26 and $0.06): their targeted scores already end below the threshold at 10%, so each further readmission avoided costs $1,748 of margin and earns no relief.[^sites]

### 5.4 National view

Table 8. Where each design would pay back: all payment-eligible US hospitals, base case with the national MA share (54%), full-strength year.[^nat]

| Design | Hospitals where it would run | Hospital net > 0 | Whole-system net > 0 |
|---|---:|---:|---:|
| Broad | 2,688 | 0 (0%) | 0 (0%) |
| Targeted | 1,828 | 33 (1.8%) | 137 (7.5%) |

The result is not specific to the illustrative group. The 33 hospitals where the targeted design pays back are all High volume with large estimated FY2026 penalties (median about $1.0M, against $67K across all 1,828).

## 6. Timing: penalty relief lags program cost

The FY N penalty uses discharges from July N−4 to June N−2 and applies to payments from October N−1, 15 months after the window closes (42 CFR 412.152). The FY2027 (in effect now) and FY2028 windows are already closed. A January 2027 start covers 6 of the 24 months in the FY2029 window (25%), 18 in FY2030 (75%) and all 24 from FY2031; with the half-strength first year the effect is 12.5%, 50% and 87.5% of full strength in FY2029–FY2031, and full strength arrives in FY2032 (payments from October 2031). Program cost, lost margin and readmission savings start at once.

Table 9. Targeted pilot by fiscal year (US$ thousands). Effect share = program months in the CMS window, weighted by strength (50% in the first 12 months), ÷ 24.

| Fiscal year | CMS window | Program months | Effect share | Program cost | Penalty avoided | Margin lost | Hospital net | Cumulative hospital net | Whole-system net |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|
| FY2027 | Jul 2023–Jun 2025 | 0 | 0% | 67.6 | 0.0 | 4.8 | −72.4 | −72.4 | −26.1 |
| FY2028 | Jul 2024–Jun 2026 | 0 | 0% | 120.3 | 0.0 | 11.1 | −131.4 | −203.8 | −23.5 |
| FY2029 | Jul 2025–Jun 2027 | 6 | 12.5% | 130.3 | 13.8 | 12.7 | −129.3 | −333.1 | −19.7 |
| FY2030 | Jul 2026–Jun 2028 | 18 | 50% | 130.3 | 55.1 | 12.7 | −88.0 | −421.2 | −19.7 |
| FY2031 | Jul 2027–Jun 2029 | 24 | 87.5% | 130.3 | 96.3 | 12.7 | −46.7 | −467.9 | −19.7 |
| FY2032 | Jul 2028–Jun 2030 | 24 | 100% | 130.3 | 110.1 | 12.7 | −33.0 | −500.8 | −19.7 |
| **Total** | | | | **709.3** | **275.3** | **66.8** | **−500.8** | | **−128.2** |

FY2027 covers January–September 2027 only, at half strength. Over the six years the pilot prevents about 38 readmissions; from FY2028 on, the annual hospital net improves every year but stays negative (six-year NPV at 7%: −$439K).

## 7. Sensitivity

The pilot's hospital net stays negative under 17 of 18 one-at-a-time ±30% changes, and the exception only reaches break-even. The whole-system net is closer to zero and turns positive under 4 of the 18.

### 7.1 One input at a time, ±30% (pilot)

Table 10. Pilot hospital net and whole-system net with one input 30% down or up, all others at base (US$ thousands a year, full-strength year; base −33.0 and −19.7). The conclusion is the sign of the result.

| Input (base) | Value at −30% / +30% | Hospital net, −30% | Hospital net, +30% | Whole-system net, −30% | Whole-system net, +30% | Does the conclusion change? |
|---|---|---:|---:|---:|---:|---|
| Readmission reduction among enrolled (10%) | 7% / 13% | −62.2 | −7.5 | −52.9 | +13.5 | Hospital: no. Whole system: positive at +30% |
| Share of patients enrolled (30%) | 21% / 39% | −38.1 | −31.6 | −28.8 | −10.6 | No |
| Cost per enrolled patient ($400) | $280 / $520 | −8.9 | −57.1 | +4.4 | −43.8 | Hospital: no. Whole system: positive at −30% |
| Fixed cost per hospital ($25,000) | $17,500 / $32,500 | −18.0 | −48.0 | −4.7 | −34.7 | No |
| Payment per discharge, i.e., penalty size (100%) | 70% / 130% | −66.0 | ≈ 0 (+$66) | −19.7 | −19.7 | Hospital: break-even at +30%. Whole system: no (a transfer) |
| Persistence of today's excess (0.5) | 0.35 / 0.65 | −39.0 | −29.9 | −23.2 | −16.1 | No |
| MA share (41%) | 28.7% / 53.3% | −25.4 | −47.7 | −24.9 | −11.7 | No |
| Variable share of hospital cost (80%) | 56% / 100%[^vcs] | −66.2 | −20.2 | −52.9 | +8.0 | Hospital: no. Whole system: positive at +30% |
| Cost of a readmission ($19,000) | $13,300 / $24,700 | −29.1 | −36.8 | −52.9 | +13.5 | Hospital: no. Whole system: positive at +30% |

A higher MA share hurts the hospital but helps the whole system: for the same FFS volume the program enrolls more patients, each of whom prevents about $550 of hospital cost ($15,200 ÷ about 28 enrollees) for $400, but adds almost nothing to the penalty avoided, because the score's base grows with them and the penalty base does not.

### 7.2 Broad program

Under every ±30% change the broad program's hospital net stays negative (−$1.18M to −$0.63M a year), and so does its whole-system net (−$757K to −$202K; `bc_sensitivity_broad`).

### 7.3 Tornado ranking

Table 11. Swing in pilot hospital net between the −30% and +30% values, largest first (US$ thousands a year; variable share capped at 100%).

| Input | Swing |
|---|---:|
| Payment per discharge (penalty size) | 66.1 |
| Readmission reduction among enrolled | 54.6 |
| Cost per enrolled patient | 48.2 |
| Variable share of hospital cost | 45.9 |
| Fixed cost per hospital | 30.0 |
| MA share | 22.2 |
| Persistence of today's excess | 9.1 |
| Cost of a readmission | 7.6 |
| Share of patients enrolled | 6.4 |

Two of the top five, cost per patient and fixed cost, are costs the group controls and a pilot measures precisely. Payment per discharge and the variable share are better pinned down with the hospitals' own payment and cost-accounting data.

### 7.4 Break-even values

Table 12. Value each input must reach, one at a time with all others at base, for the result to reach zero (full-strength year). Effects are on the base-effect scale (C4); pooled across the pilot's enrolled patients they are 1.16 times larger (Section 9.3).[^be]

| Input | Pilot, hospital net | Pilot, whole-system net | Broad, hospital net | Base | Reference point |
|---|---|---|---|---|---|
| Readmission reduction among enrolled | ≥ 14.0% (≈ 16% pooled) | ≥ 11.8% | None: cost exceeds the entire expected penalty ($644K) | 10% | Recent trials: about 11% (RR 0.89; Leppin 2014, Cochrane 2022) |
| Readmission reduction, if payers return 30% of savings | ≥ 9.7% | – | – | 10% | Shared-savings scenario (Table 3) |
| Cost per enrolled patient | ≤ $236 | ≤ $302 | ≤ $8 | $400 | Cheapest published program: about $334–$362 in 2024 dollars (Care Transitions Intervention) |
| Share of payer savings returned | ≥ 27% | – (a transfer) | Not reachable: −$187K a year at 100% | 0% | 30%: +$4K a year |
| Share returned, to pay back by FY2032 | ≈ 77% | – | – | 0% | Start-up years carry cost before relief |

### 7.5 Monte Carlo

2,000 runs with a fixed seed (42), each drawing C3, C4, C6, C7, C10, C13, C14 and B3 at once from triangular (low, base, high) distributions. A rerun with the same seed reproduces the results exactly (pipeline check P5).

Table 13. Pilot results across 2,000 runs (US$ thousands a year, full-strength year). Whole-system figures computed from `bc_monte_carlo.parquet`; the rest are in `key_metrics.json`.

| | Hospital net | Whole-system net |
|---|---:|---:|
| Share of runs above zero | 11.9% | 22.7% |
| Median | −54 | −38 |
| 90% range (5th–95th percentile) | −127 to +19 | −116 to +53 |

The median run is worse than the base case (−$54K vs −$33K) because the cost ranges skew upward: $250–$700 per patient around $400, and $10K–$60K of fixed cost around $25K.

## 8. Risks: what could make the case better or worse

The main risks make the case worse; the main upsides (payer co-funding, refilled beds, billing and score spillovers) are not counted in the base case.

Table 14. Risks and upsides. Direction = effect on the pilot's hospital net.

| Factor | Direction | What we know | Handling |
|---|---|---|---|
| Trial effects shrink at scale | Worse | Pre-2002 trials averaged RR 0.56, later ones 0.89 (Leppin 2014); CCTP showed no hospital-wide effect; 13 of 15 Medicare care-coordination trials were null (Peikes 2009); PACT-HF was not significant. At a 3% effect the pilot loses about $101K a year ($0.22 per $1).[^calc] | Recent-trial effect in the base case; month-12 gate |
| Penalties are volatile | Either | Large FY2026 cuts shrank in FY2027 and small ones grew (Section 3.4); CMS's actual cut went from 0.87% to 0.23% ($94K on our payment base) at Inspira Mullica Hill and from 0.61% to 1.19% ($161K) at Palisades, which may partly reflect the rule change. The group's FY2027 cuts total about $0.40M against our FY2029+ baseline of $644K (Inspira $191K, Palisades $59K): the pilot pair's total holds ($255K vs $249K), its split does not. Under different rules and thresholds, FY2027 is a warning, not a replacement baseline.[^calc] A score that falls below the threshold on its own leaves no penalty to avoid. | Refresh with CMS's FY2027 condition-level data (early 2027) |
| Sepsis measure from FY2030 | Either | Enters payment in FY2030 (confidential reports for FY2028–FY2029); CMS estimated it would raise total HRRP penalties by about 47%. Its first window (Jul 2026–Jun 2028) is open. Not modeled: no hospital results yet. | Review the confidential reports |
| Freed beds refilled | Better | No margin lost: pilot −$20K a year ($0.84 per $1). | Check occupancy |
| Star rating and value-based purchasing | Better (not modeled) | The star rating's Readmission group (22% weight) includes excess days in acute care (EDAC) after AMI, heart failure and pneumonia stays, the CABG, COPD and hip/knee readmission measures and hospital-wide readmission. MSPB (value-based purchasing) counts 30-day post-discharge spending, readmissions included. | Not counted |
| Substitution and harm | Worse | Fewer readmissions can come with more ED visits and observation stays (Wadhera 2019). Heart failure mortality rose after HRRP; one study linked the rise to the program (Gupta 2018), another found it continued an existing trend (Khera 2018). | Month-12 safety test |
| Payer co-funding | Better | Payers save $16,948 per avoided readmission; returning 27% makes the pilot break even. Payers may decline or dispute which savings the program caused. | Term sheet before go-live |
| TCM billing | Better (not modeled) | Medicare pays $122–$299 per TCM service (CY2026, codes 99495 and 99496, by setting); the gain over a regular follow-up visit is uncertain. | Check billing with the clinics |
| Model limits | Either; on balance they flatter the program | Single-hospital dollars can be off by ±30% or more. Our FY2026 estimates exceed CMS's actual cuts at all 8 hospitals ($1.23M vs $1.04M with CMS's cuts on our payment base); the national-median threshold overstates penalties where many patients are dual-eligible (Palisades: 0.82% vs CMS's 0.61%). Payment assumes a wage index of 1.0; if New Jersey's is higher, an illustrative +15% still leaves the pilot at about −$16K a year.[^calc] One persistence factor covers all hospitals; MA is assumed to pay like FFS. | Ranges and Monte Carlo; the hospitals' CMS Hospital-Specific Reports |

**Not covered by this program:** hip/knee replacement at University Medical Center of Princeton at Plainsboro (FY2026 ERR 1.38, worse than 98.8% of peers). Its $249K is the FY2026 estimate, from 16 readmissions on 164 discharges over 3 years, about one excess readmission a year as CMS's score counts it. Forward exposure is likely lower: CMS's FY2027 cut for the hospital is 0.04%, and the baseline expects today's excess to fade (persistence 0.5). A review of its hip/knee readmissions is a cheaper first step.

## 9. Recommendation and decision rule

### 9.1 Recommendation

1. **Do not fund the group-wide program on financial grounds.** It would cost about $1.12M a year to avoid about $292K of penalty ($0.19 per $1), and it loses $479K a year even for payers and hospital together.
2. **If the group wants to act on readmissions as a quality issue, run a two-year pilot with a month-12 checkpoint** of the targeted design at Inspira Mullica Hill and Palisades: about $90K over the first 12 months at half enrollment (FY2027 budget: $68K) and $130K a year at full strength, preventing about 7 readmissions a year at the base effect.[^budget] Budget it as a quality investment with an expected hospital net of about −$33K a year, not as a cost saving. Before go-live, confirm both sites with each hospital's CMS Hospital-Specific Report and FY2027 condition-level data (early 2027): Inspira's FY2027 cut fell to 0.23%, about half our baseline in dollars; Palisades' rose to 1.19% (Section 5.3).
3. **Ask payers to co-fund before go-live:** the Medicare Advantage plans and ACO partners the group contracts with, for at least 27% of the payer savings the pilot generates ($33K of $123K a year). About 59% of those savings accrue to traditional Medicare, which shares savings only through its own programs (such as ACOs); from MA plans alone, $33K is about 65% of theirs.
4. **Separately, review hip/knee readmissions at Princeton Plainsboro** before committing money there, after checking CMS's FY2027 condition-level data (the hospital's FY2027 cut fell to 0.04%).

### 9.2 Pilot design

- **Sites and conditions:** Inspira Mullica Hill (heart failure); Palisades (heart failure and pneumonia). Components as in Section 2.
- **Patients:** Medicare patients 65+, FFS and MA, in the top 30% by readmission risk at discharge: about 100 in the first 12 months (half strength), about 200 a year after that.
- **Budget:** $400 variable cost per enrolled patient; $25,000 fixed cost per hospital per year.
- **Monthly measures:** 30-day all-cause readmissions, enrolled vs comparison, by payer; 30-day ED treat-and-release visits and observation stays; 30-day mortality; share of enrolled patients who received all three components; cost per enrolled patient.

### 9.3 Comparison group and power check

A before-and-after comparison would credit the program with regression to the mean: in the Camden hotspotting trial a naive pre-post comparison suggested a 38-point fall in readmissions, while the randomized comparison showed none (Finkelstein 2020). Use a concurrent comparison group: while only about half of eligible patients can be enrolled (first 12 months), offer places by a rule fixed in advance (for example, alternate discharge days), so those not offered a place form the comparison group; add similar higher-risk patients at the six non-pilot hospitals, risk-adjusted.

**What the pilot can and cannot show.** About 100 patients will be enrolled by month 12 and about 301 by month 24, with a baseline 30-day readmission risk of 31.3%. Heart failure gets 1.2 times the base effect, so the pooled reduction across enrolled patients is 1.16 times the base effect: about 12% expected (10% base) and about 16% needed to break even (14% base). With equal-sized groups, 80% power and a two-sided 5% test, the smallest reduction the pilot could reliably detect is about 52% at month 12 and 32% at month 24; confirming the break-even effect would take about 1,250 patients per group (2,480 for the base effect).[^power] So month 12 tests delivery, enrollment, cost and safety; the effect is judged at month 24, pooled across both hospitals and read alongside the published trials. Payer co-funding lowers the bar.

### 9.4 Decision rule

Table 15. Month 12 (stop or continue): continue into year 2 only if all four tests pass. The VP of Quality and the CFO decide on a readout from quality analytics.

| Test | Continue only if |
|---|---|
| Delivery | ≥ 80% of enrolled patients received all three components |
| Enrollment | ≥ 90 patients enrolled in months 1–12 |
| Cost | ≤ $400 variable cost per enrolled patient |
| Safety | no rise vs the comparison group in 30-day ED visits, observation stays, mortality or readmissions |

Table 16. Month 24 (keep or stop), on the pooled reduction in 30-day readmissions among about 301 enrolled patients vs the comparison group. Thresholds are the hospital break-even points of Table 12 on the pooled scale (1.16 × the base effect).

| Decision | Condition |
|---|---|
| Make the program permanent | Pooled reduction ≥ 16% at ≤ $400 per patient; or ≥ 12% with a signed agreement returning ≥ 27% of payer savings; or ≥ 12% at ≤ $236 per patient |
| Keep it as a quality program (leadership decision) | Reduction above 0% but below these levels: expected hospital net about −$33K a year at the base effect |
| Stop | No reduction (0% or less) |

**Extending beyond the two sites** needs payer co-funding in any case: the other six hospitals return $0.36 per $1 or less at the base effect, and $0.62 or less at a 20% effect.

### 9.5 Who owns what

Table 17. Owners of the pilot and related actions (illustrative roles, like the group itself).

| Owner | Responsible for |
|---|---|
| VP of Quality (sponsor) | Pilot charter; month-12 and month-24 decisions with the CFO |
| CFO | Budget ($90K for the first 12 months; $130K a year at full strength); co-funding terms |
| Managed-care contracting | Shared-savings term sheet with payers (target ≥ 27% of payer savings) before go-live |
| Nursing and care-management leads, pilot sites | Enrollment, the 72-hour nurse contact, booking the 7-day visit |
| Pharmacy, pilot sites | Medication review before discharge |
| Quality analytics | Comparison-group rule; monthly tracking by payer; readouts; refresh with CMS's FY2027 condition-level data (early 2027) |
| Orthopedic and quality leads, Princeton Plainsboro | Hip/knee readmission review (outside this program) |

## Notes

[^calc]: Computed for this document with `src.cost_model.evaluate` on the pilot, changing only the input named: full pass-through +$25.5K a year ($1.20 per $1; penalty avoided $169K); 3% effect −$101K ($0.22 per $1); payment +15% −$16.4K. Condition shares from `client.penalty_by_condition`: ($510,953 + $176,535) ÷ $1,231,071. FFS-only (reach 0.177) and peer-group thresholds (`cms_validation_thresholds.csv`): `business_case.robustness`. FY2027 dollars: our penalty × CMS FY2027 cut ÷ our FY2026 cut (`validation.client`).
[^fy26]: Broad: the `broad_fy2026_rules` scenario. Pilot: `evaluate` with MA share 0 and a 3-year window (cost $97K, penalty avoided $105K).
[^pers]: CMS Table 15 cuts for FY2026 and FY2027 (`cms_persistence_hospital.parquet`; `validation.persistence`): least-squares slope 0.578, intercept +0.0016, correlation 0.573, n = 2,894. Means computed from the same table.
[^payback]: `bc_phase_in.parquet` (pilot): payer savings ($123K a year at full strength) total $648K over FY2027–FY2032 (5.25 full-strength-equivalent years); a share s adds s × $648K to the cumulative −$501K, which reaches zero at s ≈ 77%.
[^unit]: Pilot: `business_case.pilot_unit_economics`. Broad column and enrollees: scenario totals in `key_metrics.json` ÷ readmissions avoided.
[^sites]: `evaluate` for each hospital alone (the ranking rule of `src.analysis.pilot_hospitals`) at a 10% and a 20% base effect; the eight nets sum to the "targeted, all 8" −$294K.
[^nat]: Counts in `key_metrics.json`; whole-system counts and the profile of the 33 hospitals from `bc_national_*.parquet` joined to `dim_hospital.parquet`.
[^vcs]: +30% of 80% would be 104%, above the 100% maximum, so the table caps it at 100%, as the tornado does (`bc_sensitivity.parquet`, `bc_tornado.parquet`). The cap does not change hospital net: no margin is lost once variable cost reaches the payment.
[^be]: `business_case.break_even` (payer share 26.7%), except 9.7% with 30% shared savings and the $302 whole-system cost (`src.cost_model.break_even`), and the broad −$187K at 100% shared savings (`evaluate`); 77%: note to Section 5.1.
[^power]: `business_case.pilot_power` in `key_metrics.json` (enrollees by hospital and condition: `bc_rows_targeted_pilot.parquet`): base-case pooled reduction 11.6% (7.3 avoided), minimum detectable reductions 52.2% and 31.9%. The pooled reduction weights each condition's effect by its expected readmissions: 14.0% × 1.16 ≈ 16%; 10% × 1.16 ≈ 12%.
[^budget]: $50K a year of fixed cost for the two sites plus half of the $80K full-strength variable cost in January–December 2027; FY2027 (January–September) is from Table 9.
[^cost]: As in assumptions.md (C8): 2013 condition-level costs of $12,186–$14,478 per Medicare readmission × 1.318 = $16,061–$19,082; $18,100 × 1.161 = $21,014. At $21,000 the pilot's whole-system net would be about −$8K a year and its hospital net about −$34K (`evaluate`).

## Sources

Project files: `src/cost_model.py` (model; see its docstring), `src/analysis.py`, `src/shrinkage.py`, `src/validate_cms.py`, `reports/tables/cms_validation_*.csv`, `config.yaml`, `seeds/condition_params.csv`.

Every other source cited above (the CMS rules, fact sheet, 42 CFR 412.152, FY2026 supplemental file and Table 15, RVU26D, CCTP evaluation; MedPAC 2025 and 2026; HCUP, BEA and BLS data; RUPRI Center (2026), Medicare Advantage Enrollment Update 2025; KFF 2025; and the studies cited by author and year) has its full reference, with a link where one exists, in [assumptions.md](assumptions.md).

Cited only here:
- 42 CFR 412.154: https://www.govinfo.gov/content/pkg/CFR-2024-title42-vol2/xml/CFR-2024-title42-vol2-sec412-154.xml
- CMS Table 15, FY2027 payment adjustment factors: https://www.cms.gov/files/zip/fy-2027-hospital-readmissions-reduction-program-payment-adjustment-factors.zip
- Star rating methodology, CY2021 OPPS/ASC final rule (85 FR 85866): https://www.govinfo.gov/content/pkg/FR-2020-12-29/html/2020-26819.htm
- CMS, MSPB Hospital measure information form (2025): https://qualitynet.cms.gov/files/68f92567ec89ae1f61aa31e8?filename=HIQR_MSBP_Hospital_MIF_2025.pdf
- MedPAC, June 2018 report, Ch. 1 (penalty multiplier): https://www.medpac.gov/wp-content/uploads/import_data/scrape_files/docs/default-source/reports/jun18_medpacreporttocongress_rev_nov2019_note_sec.pdf
- Tyler N et al. JAMA Netw Open 2023;6(11):e2344825: https://pmc.ncbi.nlm.nih.gov/articles/PMC10690480/
- Van Spall HGC et al. Eur J Heart Fail 2017;19(11):1427-1443: https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi?db=pubmed&id=28558095,30073240,28233442&rettype=abstract&retmode=text
- Finkelstein A et al. N Engl J Med 2020;382(2):152-162: https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi?db=pubmed&id=35199849,31467155,31914242&rettype=abstract&retmode=text
- Wadhera RK et al. BMJ 2019;366:l4563: https://pmc.ncbi.nlm.nih.gov/articles/PMC6689820/
- Gupta A et al. JAMA Cardiol 2018;3(1):44-53: https://jamanetwork.com/journals/jamacardiology/article-abstract/2663213
- Khera R et al. JAMA Netw Open 2018;1(5):e182777: https://jamanetwork.com/journals/jamanetworkopen/fullarticle/2703947
