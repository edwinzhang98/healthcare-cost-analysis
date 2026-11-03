# Benchmarking: Princeton (Plainsboro) vs similar hospitals

This document compares one hospital's readmission results, condition by condition, with hospitals of the same type, the same ownership group and the same HRRP volume band.

| | |
|---|---|
| **Target hospital** | University Medical Center of Princeton at Plainsboro (CCN 310010), Plainsboro, NJ. It has the largest estimated penalty in the illustrative client group. |
| **Client group** | 8 New Jersey hospitals drawn by a seeded, size-stratified rule (`src/client.py`, `config.yaml`). This is an illustrative client group, not an actual health system. No relationship with these hospitals is implied. |
| **Peers** | Payment-eligible acute care hospitals with the same ownership group and the same HRRP volume band (section 2). |
| **Data** | CMS FY2026 HRRP file (traditional Medicare patients aged 65+, discharges 2021-07-01 to 2024-06-30), joined to CMS Hospital General Information. |
| **Penalty dollars** | Our estimates, using CMS's formula with a national-median threshold. The method makes the same penalized / not-penalized call as CMS's actual FY2026 decisions for 97% of hospitals. |
| **Code** | `src/benchmarking.py` (`peer_ids`, `benchmark`, `peer_summary`). Page 4 of the dashboard shows the same view for any hospital and any peer definition. |

Numbers come from `reports/key_metrics.json`. Where a number is not in that file, a footnote says how it was computed.

## 1. Bottom line

- **Princeton (Plainsboro) readmits more than about 90% of similar hospitals.** Its readmission index is 1.070. The median for its 707 peers (non-profit, high-volume hospitals) is 0.997. Every condition CMS scored is above the penalty threshold, which is true of only 6% of peers. The estimated penalty is $384K a year, 2.6 times the peer median of $146K. Northeast-only peers readmit more, and against them the hospital ranks at the 80th percentile.
- **Most of the gap comes from a few hip/knee readmissions.** Hip/knee replacement has an ERR of 1.38, higher than 99% of peers. That ERR rests on 16 readmissions among 164 discharges over three years. About 9 were expected for these patients, so the excess is roughly 2 readmissions a year. This one condition carries an estimated $249K a year, 65% of the hospital's penalty. CMS's own FY2026 figures give the same split: about two-thirds of the hospital's 0.88% payment cut.
- **The other conditions are close to peers.** Heart attack (86th percentile) is the only other condition worse than most peers, and that status depends on about 2 readmissions over three years. Heart failure is at the 71st percentile. Because its volume is high, it still has the largest gap in patients: about 3 readmissions a year.
- **The hip/knee excess appears to have faded, so a case review fits better than a new program.** CMS's FY2027 cut for this hospital, based on July 2023 – June 2025 discharges, fell to 0.04%. Across the group, the strongest case for a follow-up program is heart failure at Inspira Mullica Hill and Palisades, then Jersey City.

## 2. Who the peers are

**Definition.** A peer is a hospital that meets all four conditions:

1. It is payment-eligible. That means it is not in Maryland (exempt from HRRP payment cuts) and is still listed in Hospital General Information.
2. It has an ERR for at least one condition. CMS publishes an ERR only when a condition has 25 or more eligible discharges (CMS HSR user guide).
3. It is in the same ownership group: Non-profit. `sql/04_stg_hospital_info.sql` groups CMS's detailed ownership values into Non-profit, For-profit and Government.
4. It is in the same HRRP volume band: High volume. A hospital is High volume with 1,000 or more eligible traditional-Medicare discharges for the six conditions over the three years, Mid volume with 400–999 and Low volume with fewer than 400.[^vol]

The hospitals are the same type by construction. HRRP applies only to short-term acute care hospitals paid under the inpatient prospective payment system. Critical access, psychiatric, rehabilitation, children's and long-term care hospitals are outside it (42 U.S.C. 1395ww(q)). In Hospital General Information, all 2,777 payment-eligible hospitals with a score are "Acute Care Hospitals". The target is never its own peer.

Table 1. How the peer group is built for Princeton (Plainsboro). Number of hospitals; FY2026 HRRP; payment-eligible hospitals with at least one scored condition.

| Step | Hospitals |
|---|---|
| Payment-eligible hospitals with at least one ERR, national | 2,777 |
| Same ownership group (Non-profit), excluding the target | 1,787 |
| **Same ownership group and HRRP volume band (High volume): default peers** | **707** |
| Default peers in the same census region (Northeast): robustness check, section 5a | 174 |

Over three years, the median peer had 1,628 eligible discharges (middle half: 1,260 to 2,243). The target had 1,496. Peers come from all four census regions (South 219, Midwest 202, Northeast 174, West 112), and 32 are in New Jersey. 96% have an emergency department. A peer enters the comparison for a condition only if it has an ERR for that condition. So the number of peers varies: 704 for heart failure and pneumonia, 702 for COPD, 689 for heart attack, 577 for hip/knee replacement and 520 for bypass surgery.

**Why HRRP volume band rather than beds.**

- **Beds are not in the data.** None of the three CMS files has a bed count.
- **Volume shapes the score.** CMS's model pulls hospitals with few cases toward an ERR of 1.00 (section 5c). In the FY2026 results, ERRs have a standard deviation of 0.095 in the High volume band and 0.059 in the Low volume band.[^sd] Compared with low-volume hospitals, a high-volume hospital would look extreme partly because its score is pulled less. Within one band, the scores rest on similar amounts of data.
- **Volume band is not hospital size.** The band counts traditional-Medicare patients aged 65+ treated for six conditions, so payer mix and service lines matter as much as size. For example, University Hospital (Newark), a state-owned hospital in the client group, is in the Low volume band with 147 eligible discharges over three years. In New Jersey, 41% of Medicare beneficiaries were in Medicare Advantage in 2025 (RUPRI 2026), and the FY2026 scores leave them out.
- **Ownership and volume do different jobs.** We adjusted for condition, region, emergency department and spending. After that, for-profit hospitals average 1.4 ERR points above non-profits (95% CI 0.9 to 2.0), and one ERR point (0.01) is about 1% more readmissions than expected. High- and mid-volume hospitals differ by only 0.04 points (95% CI −0.41 to 0.49). Matching on ownership removes a difference in averages. Matching on volume removes a difference in spread.

Region is not part of the default definition. CMS sets penalty thresholds nationally, within dual-eligible peer groups, so national peers show the hospital the way CMS sees it. Section 5a gives the regional view.

## 3. Condition by condition

Table 2. Princeton (Plainsboro) ERR against its 707 peers, by condition, sorted from worst to best percentile. ERR = predicted ÷ expected readmission rate, where 1.00 means as expected for the hospital's patients. Percentile = share of peers with a lower ERR. National penalty threshold = national median ERR for the condition. FY2026 HRRP, discharges July 2021 – June 2024.

| Condition | ERR | Peer 25th pct | Peer median | Peer 75th pct | Percentile among peers | National penalty threshold | Status |
|---|---|---|---|---|---|---|---|
| Hip/knee replacement | 1.3835 | 0.897 | 1.001 | 1.107 | 98.8 | 0.991 | Worse than most peers |
| Heart attack (AMI) | 1.0763 | 0.954 | 1.000 | 1.047 | 86.4 | 0.999 | Worse than most peers |
| COPD | 1.0337 | 0.966 | 0.997 | 1.034 | 74.9 | 0.997 | In line with peers (at the cut-off) |
| Heart failure | 1.0354 | 0.942 | 0.987 | 1.045 | 71.2 | 0.999 | In line with peers |
| Pneumonia | 1.0048 | 0.952 | 0.995 | 1.056 | 55.4 | 0.996 | In line with peers |
| Bypass surgery (CABG) | not scored | 0.930 | 0.991 | 1.051 | – | 1.001 | No CMS result for this period |

The status follows `benchmark()`. At the 75th percentile or higher, a condition is worse than most peers. At the 25th or lower, it is better than most peers. Anything in between is in line with peers.

Table 3. The same gaps in patients and dollars. Counts cover the 3-year window unless marked "per year". The penalty is our estimate in dollars per year under FY2026 rules.

| Condition | Eligible discharges | Readmissions (observed) | Expected readmissions[^exp] | Readmissions per year vs peer median (score) | Actual readmissions per year to reach peer median[^act] | Estimated penalty per year |
|---|---|---|---|---|---|---|
| Hip/knee replacement | 164 | 16 | 8.8 | 1.1 | 2.4 | $249K |
| Heart attack (AMI) | 119 | 21 | 16.0 | 0.4 | 1.7 | $39K |
| COPD | 171 | 35 | 31.5 | 0.4 | 1.3 | $15K |
| Heart failure | 716 | 138 | 130.9 | 2.1 | 3.2 | $71K |
| Pneumonia | 326 | 49 | 48.5 | 0.2 | 0.4 | $9K |
| Bypass surgery (CABG) | – | – | – | – | – | $0 |
| **Total** | **1,496** | **259** | **235.7** | **4.2** | **9.0** | **$384K** |

The score column is annual eligible discharges × expected rate × (ERR − peer median), as computed by `benchmark()`. It measures the gap as the CMS score sees it. CMS credits only part of an actual change (pass-through, section 5c). Closing the gap therefore means avoiding more actual readmissions: the score gap divided by the pass-through.

**What each row says.**

- **Hip/knee replacement.** CMS shows the actual counts for this condition: 16 readmissions on 164 discharges. That is a 9.8% rate, against 5.4% expected for these patients. Over three years that is about 7 more readmissions than expected, roughly 2 a year. At this volume the score credits about half of the gap. The ERR is still 1.38, higher than 99% of peers. The penalty formula multiplies the gap above the threshold by the payments for all of the hospital's hip/knee discharges. So these few readmissions cost an estimated $249K a year. Nationally, each hip/knee readmission above the threshold costs about $217K a year in penalty. That is 11 times the $19,000 a readmission costs to treat. MedPAC measures it differently but reaches the same conclusion: one excess hip/knee readmission draws a penalty more than 20 times the cost of the initial admission (MedPAC 2018). With about 7 fewer readmissions over the three years (2.4 a year), the hospital would have been at the peer median. That would have removed all but about $7K of this condition's penalty.
- **Heart attack.** 21 readmissions on 119 discharges (17.6%), against 16 expected. With so few cases, the score credits only about a quarter of the gap. The result is an ERR of 1.08, the 86th percentile and $39K a year. The status could easily change. With two fewer readmissions over three years, the hospital would be at about the 74th percentile, in line with peers.[^cnt]
- **COPD.** 35 readmissions on 171 discharges, against 31.5 expected. The ERR of 1.03 is at the 74.9th percentile, just under the cut-off for "worse than most peers". It crosses 75 under three of the five other peer definitions in Table 6. About 4 fewer readmissions over three years would bring it to the peer median. $15K a year.
- **Heart failure.** 138 readmissions on 716 discharges (19.3%), against 131 expected. An ERR of 1.04 at the 71st percentile is not unusual among peers. Because volume is high, this is still the largest gap in patients: about 2 readmissions a year as the score counts them, about 3 a year in actual readmissions. An actual improvement also shows up in the score most here (pass-through 0.66). The evidence for follow-up programs is also strongest for heart failure (AHRQ 2014). $71K a year.
- **Pneumonia.** 49 readmissions on 326 discharges, about as expected (48.5). The ERR of 1.005 is just above the threshold of 0.996, which adds $9K a year. Nothing to act on.
- **Bypass surgery.** CMS reports no result for this hospital in this period. Its footnote 5 means "results not available for this reporting period" (CMS footnote crosswalk). No score, so no penalty.

![Dashboard page 4: Princeton (Plainsboro) ERR by condition against its 707 peers](img/04_benchmarking.png)

*Figure 1. Page 4 of the dashboard (Hospital Benchmarking) for Princeton (Plainsboro), default peers. Each row is one condition. Gray dots are the 707 peers' ERRs, and the box marks the middle half. The blue diamond is the hospital and the red tick is the national penalty threshold. Further right is worse. FY2026 HRRP, discharges July 2021 – June 2024.*

## 4. Hospital-level summary

Table 4. Princeton (Plainsboro) against its 707 peers, all conditions combined. Readmission index = discharge-weighted mean ERR across the conditions CMS scored. Penalty = our annual estimate under FY2026 rules. Percentile = share of peers with a lower value.

| Measure | Princeton (Plainsboro) | Peer median | Peer 25th–75th pct | Percentile among peers |
|---|---|---|---|---|
| Readmission index | 1.070 | 0.997 | 0.959–1.036 | 89.8 |
| Estimated penalty, $ per year | $384K | $146K | $47K–$292K | 82.3 |
| Estimated payment cut, % of base operating DRG payments | 1.08% | 0.34% | – | – |
| Scored conditions above the penalty threshold | 5 of 5 | 3 | – | – |

- **In this peer group, a penalty is normal but a penalty this large is not.** We estimate that 92% of peers are penalized, against 84% of scored hospitals nationally. Princeton's estimated penalty is 2.6 times the peer median. Only 6% of peers have every scored condition above the threshold.
- **The penalty ranks lower than the index (82nd vs 90th percentile).** Many peers treat more traditional-Medicare patients (peer median 1,628 discharges over three years, against 1,496). So the same ERR gap costs them more.
- **CMS's actual figures point the same way.** CMS cut this hospital's FY2026 payments by 0.88%, where we estimate 1.08%. Its FY2027 cut was 0.04%.[^cms] Our estimate is higher mainly because of payment weights, not the threshold. This hospital's six conditions are a smaller share of its Medicare payments than the national median we assume (CMS file: 0.096 vs 0.133).

## 5. Robustness

### 5a. Peers from the same region

Table 5. Princeton (Plainsboro) against national peers and against Northeast-only peers. Both groups have the same ownership group and HRRP volume band. Peer medians are ERRs, except the index (discharge-weighted mean ERR) and the penalty ($ per year). Percentile = share of peers with a lower value. FY2026 HRRP.[^peers]

| Measure | National peers | Peer median | Percentile | Northeast peers | Peer median | Percentile |
|---|---|---|---|---|---|---|
| Readmission index | 707 | 0.997 | 89.8 | 174 | 1.005 | 79.9 |
| Hip/knee replacement | 577 | 1.001 | 98.8 | 149 | 0.972 | 99.3 |
| Heart attack (AMI) | 689 | 1.000 | 86.4 | 163 | 1.010 | 84.0 |
| COPD | 702 | 0.997 | 74.9 | 172 | 1.015 | 62.8 |
| Heart failure | 704 | 0.987 | 71.2 | 172 | 0.994 | 68.0 |
| Pneumonia | 704 | 0.995 | 55.4 | 172 | 1.008 | 48.8 |
| Estimated penalty | 707 | $146K | 82.3 | 174 | $176K | 71.8 |

The 174 Northeast peers are in New York (45), Pennsylvania (40), New Jersey (32), Massachusetts (29), Connecticut (14), New Hampshire (8), Rhode Island (3), Maine (2) and Vermont (1).

- **Regional peers readmit more.** Their median readmission index is 1.005, against 0.997 nationally. Their median ERR is higher for every condition except hip/knee. This matches the national picture. The Northeast has the highest mean ERR of the four census regions (1.009, 95% CI 1.005–1.013). New Jersey's is the second-highest of 51 states (1.028). After adjustment, Northeast hospitals average about 1 ERR point above Midwest hospitals (+0.98, 95% CI 0.30–1.67). These are associations. The data cannot tell whether the cause is patient mix the risk model misses, local care patterns or something else.
- **Against regional peers the hospital looks less unusual overall.** Its index falls from the 90th to the 80th percentile, and COPD drops from the cut-off to the 63rd percentile. Hip/knee and heart attack stay worse than most peers. Northeast peers have a lower hip/knee median (0.972), so hip/knee looks slightly worse.
- **The two views answer different questions.** The national view is how CMS sees the hospital. The regional view answers "are we unusual for our area?" They agree on the conditions that matter.

Table 6. Princeton (Plainsboro) percentile among peers under six peer definitions. Percentile = share of peers with a lower ERR (for the index, the discharge-weighted mean ERR). FY2026 HRRP.[^peers]

| Peer definition | Peers | Index | Hip/knee | Heart attack | COPD | Heart failure | Pneumonia |
|---|---|---|---|---|---|---|---|
| All payment-eligible hospitals | 2,776 | 91.4 | 98.2 | 88.0 | 78.3 | 72.2 | 55.9 |
| Same ownership group only | 1,787 | 92.7 | 98.4 | 88.7 | 78.3 | 74.3 | 57.8 |
| Same HRRP volume band only | 936 | 88.6 | 98.4 | 85.9 | 73.7 | 69.0 | 54.2 |
| **Same ownership group and volume band (default)** | **707** | **89.8** | **98.8** | **86.4** | **74.9** | **71.2** | **55.4** |
| Default plus same emergency-department status | 679 | 89.4 | 98.7 | 86.3 | 75.0 | 70.9 | 54.9 |
| Default plus same census region | 174 | 79.9 | 99.3 | 84.0 | 62.8 | 68.0 | 48.8 |

Hip/knee and heart attack are worse than most peers under every definition. COPD lands on either side of the 75 cut-off, depending on the definition. Heart failure and pneumonia never reach it. The index stays in the top fifth under every definition except regional peers.

### 5b. National threshold vs CMS's peer-group threshold

CMS does not compare a hospital with the national median. It uses the median ERR of the hospital's peer group. There are five equal-sized peer groups (quintiles), defined by the share of a hospital's stays for patients eligible for both Medicare and Medicaid ("dual-eligible") (CMS HRRP methodology; CMS FY2026 supplemental file). Our files do not include the groups, so this analysis uses the national median for each condition.

Table 7. Penalty threshold for Princeton (Plainsboro): the national median ERR used here vs the median of its CMS peer group, by condition. The hospital is in group 1, the lowest dual-eligible share. FY2026; peer-group medians from CMS's FY2026 HRRP supplemental file.[^cms]

| Condition | Princeton ERR | National median (used here) | CMS peer group 1 median | Above threshold: ours / CMS's file |
|---|---|---|---|---|
| Hip/knee replacement | 1.3835 | 0.9910 | 0.9939 | Yes / Yes |
| Heart attack (AMI) | 1.0763 | 0.9994 | 0.9961 | Yes / Yes |
| COPD | 1.0337 | 0.9969 | 0.9965 | Yes / Yes |
| Heart failure | 1.0354 | 0.9989 | 0.9929 | Yes / Yes |
| Pneumonia | 1.0048 | 0.9957 | 0.9908 | Yes / Yes |

- **For this hospital the difference is small.** CMS placed it in peer group 1: 11.9% of its stays were for dual-eligible patients, which puts it in the lowest fifth. The group 1 medians are slightly below the national medians for heart failure, pneumonia and heart attack, and slightly above for hip/knee. All five conditions are above either threshold, and CMS's own file flags all five. With the group 1 medians, this hospital's estimated penalty would be about $17K a year (4%) higher.
- **Percentile ranks do not use the threshold.** Sections 3, 5a and 6 are unaffected. Only the "above threshold" flag and the penalty dollars depend on it.
- **The caveat matters for hospitals that serve many low-income patients.** In peer group 5 the medians are higher (heart failure 1.016, pneumonia 1.010). A national threshold therefore overstates how far such a hospital sits above its own threshold. Three client hospitals are in group 5: Palisades, Jersey City and University Hospital (Newark). For each, our FY2026 estimate exceeds CMS's actual cut: 0.82% vs 0.61%, 0.49% vs 0.32% and 0.34% vs 0.05%.

### 5c. Shrinkage: low-volume results sit near 1.00

Table 8. How much of Princeton's own readmission experience shows up in its ERR, by condition. Raw ratio = observed ÷ expected readmission rate. Pass-through = n ÷ (n + k): n is eligible discharges over three years, and k is fitted for each condition from the published data (`src/shrinkage.py`). FY2026 HRRP.[^shr]

| Condition | Eligible discharges (3 yr) | Raw ratio | Pass-through | Published ERR | 1 + pass-through × (raw ratio − 1) |
|---|---|---|---|---|---|
| Heart failure | 716 | 1.054 | 0.66 | 1.0354 | 1.036 |
| Hip/knee replacement | 164 | 1.811 | 0.46 | 1.3835 | 1.374 |
| Pneumonia | 326 | 1.011 | 0.44 | 1.0048 | 1.005 |
| COPD | 171 | 1.112 | 0.30 | 1.0337 | 1.034 |
| Heart attack (AMI) | 119 | 1.312 | 0.24 | 1.0763 | 1.076 |

- **The published score already discounts small samples.** Princeton's raw heart attack rate is 31% above expected, but its ERR shows 8%, because with 119 cases the hospital's own data get only about a quarter of the weight. The fitted formula reproduces each published ERR to within 0.01.
- **At low volume, every hospital sits near 1.00.** That is why peers are matched on volume band (section 2), and why small hospitals rarely look extreme. A CMS-commissioned statistical white paper describes the same effect: a hospital with almost no cases is reported close to the national standard (COPSS-CMS 2012). MedPAC notes that small hospitals are judged mostly on the national mean and get only partial credit for improvement (MedPAC 2013).
- **An actual improvement reaches the score only in part.** At this hospital, about two-thirds of it shows up for heart failure and a quarter for heart attack. The business case uses these pass-through rates.
- **The medical conditions' scores are not very reliable at these volumes.** Thompson et al. (2016) estimate the cases needed over three years for a reliability of 0.70: about 1,019 for heart failure, 605 for heart attack, 559 for COPD, 442 for pneumonia and only about 9 for hip/knee. Princeton is below those levels for all four medical conditions, so those percentiles carry more noise than the decimals suggest. Hip/knee results are more reliable per case, so the FY2026 hip/knee excess was probably more than chance. It still rests on 16 events in one window, and the FY2027 cut suggests it did not continue.[^fy27]

## 6. The whole client group side by side

Table 9. Each client hospital's percentile among its peers (same ownership group and HRRP volume band), by condition. The 8 hospitals form the illustrative NJ client group, not an actual health system. Percentile = share of peers with a lower ERR. **Bold** = 75 or higher (worse than most peers); – = not scored. Index = discharge-weighted mean ERR across the conditions CMS scored. The penalty is our annual estimate. FY2026 HRRP.

| Hospital | Volume band, ownership | Peers | Index | Index pct | Heart failure | Pneumonia | COPD | Heart attack | Bypass | Hip/knee | Est. penalty per year |
|---|---|---|---|---|---|---|---|---|---|---|---|
| Princeton (Plainsboro) | High, Non-profit | 707 | 1.070 | **89.8** | 71.2 | 55.4 | 74.9 | **86.4** | – | **98.8** | $384K |
| Inspira Mullica Hill | High, Non-profit | 707 | 1.069 | **89.4** | **98.9** | 50.0 | 43.7 | **86.9** | – | – | $373K |
| Ocean | High, Non-profit | 707 | 0.974 | 34.5 | 13.5 | 55.0 | 23.1 | 69.2 | – | **92.0** | $148K |
| Palisades | Mid, Non-profit | 595 | 1.063 | **91.4** | **96.1** | **77.1** | 67.4 | – | – | – | $112K |
| Jersey City | Mid, Non-profit | 595 | 1.040 | **81.7** | **93.4** | 69.3 | **94.9** | 65.7 | 10.7 | – | $86K |
| Monmouth | Mid, Non-profit | 595 | 1.016 | 63.7 | 29.0 | **86.0** | **88.4** | 69.6 | – | 46.4 | $75K |
| Virtua Willingboro | Low, Non-profit | 483 | 1.031 | **84.7** | 33.7 | **81.9** | **100.0** | – | – | – | $43K |
| University Hospital (Newark) | Low, Government | 192 | 1.021 | **75.5** | 40.3 | **88.6** | **76.0** | – | – | – | $11K |

- **7 of 8 hospitals have a readmission index above their peer median, and 5 are in the worst fifth:** Princeton, Inspira Mullica Hill, Palisades, Jersey City and Virtua Willingboro. Only Ocean is better than its typical peer, and its one weak spot is hip/knee. Three results in the group are better than most peers: heart failure (13.5) and COPD (23.1) at Ocean, and bypass surgery at Jersey City (10.7).
- **15 of the 33 scored hospital-condition results are at or above the 75th percentile.** That is close to twice the one in four expected for a typical group. These 15 results carry 84% of the group's estimated $1.2M penalty.
- **Heart failure: Inspira Mullica Hill (98.9), Palisades (96.1), Jersey City (93.4).** Inspira's heart failure alone carries an estimated $320K a year, the largest single item in the group.
- **COPD: Virtua Willingboro (100.0), Jersey City (94.9), Monmouth (88.4), University Hospital (76.0).** Princeton is just below (74.9). The flagged volumes are small (34–107 discharges over three years), and so are the dollars ($2K–$26K a year each).
- **Hip/knee: Princeton (98.8) and Ocean (92.0).** Ocean had 1–10 hip/knee readmissions, which CMS does not show (CMS HSR user guide). Its discharge count is therefore imputed.
- **Pneumonia and heart attack.** Pneumonia is flagged at University Hospital (88.6), Monmouth (86.0), Virtua Willingboro (81.9) and Palisades (77.1). Heart attack is flagged at Inspira Mullica Hill (86.9) and Princeton (86.4).
- **Most of the picture holds against Northeast-only peers.** 6 of 8 hospitals stay above their regional median. 13 of the 15 flags hold; Palisades pneumonia and University Hospital COPD drop out. Only Palisades stays in the worst fifth on the index. Princeton (79.9) and Inspira (79.3) fall just below the cut-off. University Hospital has only 10 regional peers, too few for a stable percentile.[^peers]
- **CMS's actual cuts moved a lot between FY2026 and FY2027.** They fell at five hospitals: Princeton 0.88% → 0.04%, Inspira Mullica Hill 0.87% → 0.23%, Ocean 0.21% → 0.02%, Monmouth 0.30% → 0.07% and Virtua Willingboro 0.34% → 0.12%. University Hospital stayed at 0.05%. They rose at Palisades (0.61% → 1.19%) and Jersey City (0.32% → 0.51%).

## 7. What this means for action

Table 10. Hospital-condition pairs to look at first. Percentiles are among peers, national / Northeast-only. Discharges and readmissions cover three years. The penalty is our annual estimate. The CMS cut is the hospital's actual payment cut across all conditions.

| Order | Hospital – condition | Percentile (national / Northeast) | Discharges (readmissions), 3 yr | Est. penalty per year | CMS cut FY2026 → FY2027 | Suggested step |
|---|---|---|---|---|---|---|
| 1 | Inspira Mullica Hill – heart failure | 98.9 / 97.1 | 671 (163) | $320K | 0.87% → 0.23% | Pilot site for heart failure and pneumonia follow-up |
| 2 | Palisades – heart failure; pneumonia | 96.1 / 97.6; 77.1 / 71.5 | 218 (56); 296 (54) | $68K; $40K | 0.61% → 1.19% | Pilot site |
| 3 | Jersey City – heart failure; COPD | 93.4 / 89.4; 94.9 / 89.4 | 191 (50); 67 (18) | $51K; $13K | 0.32% → 0.51% | Next site if the pilot meets its targets |
| 4 | Princeton (Plainsboro) – hip/knee | 98.8 / 99.3 | 164 (16) | $249K | 0.88% → 0.04% | Orthopedic case review of recent readmissions; no new program |
| 5 | Ocean – hip/knee | 92.0 / 89.3 | 82 imputed (1–10, not shown by CMS) | $78K | 0.21% → 0.02% | Include in the same review |
| Watch | The other 8 flagged results: heart attack at Inspira Mullica Hill and Princeton; pneumonia and COPD at Monmouth, Virtua Willingboro and University Hospital | 76.0–100.0 national | 34–259 each | $2K–$57K each | Fell or flat at all five hospitals | Track monthly; no separate program |

**Why this order.**

1. **Size and persistence of the gap, not just rank.** Inspira's heart failure gap is the largest in the group, in patients and in dollars. As the score counts it, the hospital is about 8 readmissions a year above the peer median, which means about 12 actual readmissions. Palisades and Jersey City have smaller gaps. But their CMS cuts rose in FY2027, so their excess at the hospital level continued into the newer window (two years of data, now including Medicare Advantage patients). Inspira's cut fell, so part of its FY2026 excess may already be fading. The business-case baseline already assumes that only half of today's excess persists without a program.
2. **Whether the score can respond.** Heart failure at these three hospitals has pass-through of 0.34 to 0.65. COPD at Jersey City (67 discharges) has about 0.14, so even a successful COPD program would barely move the score.
3. **Whether a follow-up program is the right tool.** The evidence for transitional care is strongest for heart failure (AHRQ 2014). For COPD, it shows no effect on 30-day all-cause readmission (Zhong et al. 2022). For surgery it is inconclusive (Tobiano et al. 2025). Phone calls alone show no effect (Boggan et al. 2025). Hip/knee readmissions call for a surgical case review instead, looking at complications, infections and where patients went after discharge.
4. **Consistency across peer definitions.** Every main item in Table 10 (orders 1–5) stays at or above the 89th percentile against Northeast-only peers. The one exception is Palisades pneumonia (71.5).

This ranking agrees with the business case, which chose Inspira Mullica Hill and Palisades on a different basis: where a heart failure and pneumonia program returns the most per dollar. Even there the pilot returns about $0.75 per $1 on the hospital P&L (benefit-cost ratio 0.75). So it is a test of the program, not a source of savings (`docs/business_case.md`).

**How to read percentiles responsibly.**

- **A percentile is a rank, not a size.** Princeton's 99th percentile on hip/knee is about 2 extra readmissions a year. Its 71st percentile on heart failure is about 3. Read the rank together with the counts and dollars next to it.
- **Small samples move ranks.** One fewer heart attack readmission over three years would move Princeton from the 86th to the 82nd percentile, and two fewer to the 74th. Results near the 25 and 75 cut-offs can change status on one or two patients.
- **Shrinkage pulls small hospitals toward 1.00.** Low-volume results understate actual differences, and improvements show up in the score only in part (section 5c).
- **Regression to the mean.** A result that is extreme in one window tends to be less extreme in the next, with or without action. In CMS's actual payment cuts, FY2027 kept on average about 0.58 of each hospital's FY2026 cut. 40% of the hospitals in the top tenth lost more than half of their cut (`reports/tables/cms_validation_persistence.csv`). For hospitals penalized in FY2013, Joshi et al. (2019) attribute 74–87% of the later ERR improvement to regression to the mean. A hospital at the 99th percentile today will most likely rank lower next time, whatever it does. So no program should take credit for an improvement until it has been checked against a comparison group.
- **Report the peer definition with the number.** Switching from national to Northeast peers moved Princeton's index from the 90th to the 80th percentile.
- **Program years are not comparable.** FY2026 used three years of traditional-Medicare patients. From FY2027 CMS uses two years and adds Medicare Advantage patients (FY2026 IPPS final rule). Re-run this benchmark when CMS posts FY2027 hospital-level results, expected in early 2027 (CMS FY2027 fact sheet).
- **Being worse than peers shows where to look, not why.** The CMS risk model does not adjust for social risk (CMS measure methodology). Hospital-level data cannot separate quality of care from patient differences the model does not capture.

## Reproduce

```python
from src import benchmarking, client, data

hc, dim = data.hospital_conditions(), data.table("dim_hospital")
ph = data.table("mart_penalty_hospital")
t = client.target_hospital_id()            # "310010"

benchmarking.benchmark(hc, dim, t)         # Tables 2-3 (cached as data/processed/benchmark_target.parquet)
benchmarking.peer_summary(dim, ph, t)      # Table 4
benchmarking.benchmark(hc, dim, t, ("ownership_group", "size_band", "census_region"))   # Table 5
```

On page 4 of the dashboard, ticking "Census region" reproduces the regional view.

## Sources

- **42 U.S.C. 1395ww(q):** hospitals subject to HRRP. https://www.govinfo.gov/content/pkg/USCODE-2023-title42/html/USCODE-2023-title42-chap7-subchapXVIII-partE-sec1395ww.htm
- **CMS HRRP methodology:** HRRP Payment Reduction Methodology infographic, FY2027 (peer-group median threshold). https://www.cms.gov/files/document/fy-2027-hrrp-infographic-pdf.pdf
- **CMS FY2026 supplemental file:** FY2026 HRRP Supplemental Data File (peer groups, peer-group median ERRs, DRG payment ratios, condition penalty flags). https://www.cms.gov/files/zip/fy2026-hospital-readmissions-reduction-program-supplemental-data-file.zip
- **CMS Table 15:** FY2026 and FY2027 HRRP payment adjustment factors. https://www.cms.gov/files/zip/fy-2026-hospital-readmissions-reduction-program-payment-adjustment-factors.zip and https://www.cms.gov/files/zip/fy-2027-hospital-readmissions-reduction-program-payment-adjustment-factors.zip
- **FY2026 IPPS final rule:** FY 2026 IPPS/LTCH PPS Final Rule, 90 FR 36536 (Medicare Advantage patients and a 2-year window from FY2027). https://www.govinfo.gov/content/pkg/FR-2025-08-04/html/2025-14681.htm
- **CMS FY2027 fact sheet:** Hospital Readmissions Reduction Program FY 2027 Fact Sheet (FY2027 hospital-level data due in early 2027). https://www.cms.gov/files/document/fy-2027-hrrp-fact-sheet-pdf.pdf
- **CMS HSR user guide:** FY 2026 HRRP Hospital-Specific Report User Guide (25-discharge minimum; readmission counts shown only at 11 or more). https://qualitynet.cms.gov/files/6893aac2728800f196e92cb1?filename=FY-2026-HRRP-HSR-User-Guide.pdf
- **CMS footnote crosswalk:** Provider Data Catalog Footnote Crosswalk. https://data.cms.gov/provider-data/sites/default/files/resources/f29bb7c812e242f6edfef0a4b7d0eaca_1760630713/Footnote_Crosswalk.csv
- **CMS measure methodology:** 2025 Condition-Specific Readmission Measures Updates and Specifications Report (no social-risk adjustment). https://qualitynet.cms.gov/files/6a0b7d2db58870567d25f40b?filename=2025_Rdmsn_MeasureMethodology.zip
- **COPSS-CMS 2012:** Ash et al., Statistical Issues in Assessing Hospital Performance. https://www.cms.gov/medicare/quality-initiatives-patient-assessment-instruments/hospitalqualityinits/downloads/statistical-issues-in-assessing-hospital-performance.pdf
- **MedPAC 2013:** June 2013 Report to the Congress, Ch. 4, Refining the hospital readmissions reduction program. https://www.medpac.gov/wp-content/uploads/import_data/scrape_files/docs/default-source/reports/jun13_ch04.pdf
- **MedPAC 2018:** June 2018 Report to the Congress, Ch. 1 (penalty multiplier by condition). https://www.medpac.gov/wp-content/uploads/import_data/scrape_files/docs/default-source/reports/jun18_medpacreporttocongress_rev_nov2019_note_sec.pdf
- **Thompson et al. 2016:** Reliability of 30-Day Readmission Measures Used in the HRRP. Health Serv Res 51(6). https://pmc.ncbi.nlm.nih.gov/articles/PMC5134200/
- **Joshi et al. 2019:** Regression to the Mean in the Medicare HRRP. JAMA Intern Med 179(9). https://pmc.ncbi.nlm.nih.gov/articles/PMC6596330/
- **AHRQ 2014:** Comparative Effectiveness Review 133, Transitional Care Interventions To Prevent Readmissions for People With Heart Failure. https://www.ncbi.nlm.nih.gov/sites/books/NBK209244/table/discussion.t2/?report=objectonly
- **Zhong et al. 2022:** Peri-discharge complex interventions for COPD readmissions. Int J Integr Care 22(1). https://pmc.ncbi.nlm.nih.gov/articles/PMC8815439/
- **Tobiano et al. 2025:** Surgical transitional care interventions: a scoping review. Int J Nurs Stud Adv 8. https://pmc.ncbi.nlm.nih.gov/articles/PMC12136900/
- **Boggan et al. 2025:** Synchronous post-discharge contacts. Ann Intern Med 178(2). https://pubmed.ncbi.nlm.nih.gov/39805113/
- **RUPRI 2026:** Medicare Advantage Enrollment Update 2025 (New Jersey: 41.1%). https://rupri.public-health.uiowa.edu/publications/policybriefs/2026/MA_Enrollment_2025.pdf

## Notes on numbers computed for this document

The numbered notes below explain how each number not in `reports/key_metrics.json` was computed from the cached tables in `data/processed/` and `reports/tables/`, using the project code.

[^vol]: Volume uses estimated discharges where CMS hides the counts, which happens when a condition has 1–10 readmissions (`sql/05_fct_hospital_condition.sql`). None of Princeton's discharges are imputed.

[^sd]: Standard deviation of ERR across payment-eligible hospital-condition results that have an ERR, by HRRP volume band: 0.095 for High volume (n = 5,137), 0.076 for Mid volume (n = 3,933) and 0.059 for Low volume (n = 2,416). Computed from `data.hospital_conditions()`.

[^exp]: Expected readmissions = eligible discharges × CMS's expected readmission rate. This is the number an average hospital would have with the same patients. Computed from `fct_hospital_condition`.

[^act]: The score gap per year divided by the pass-through, where pass-through = n ÷ (n + k) (Table 8) and k comes from `data/processed/shrinkage_k.parquet`. Stated in FY2026 terms: traditional-Medicare patients and a 3-year window.

[^cnt]: New ERR = ERR − pass-through × (readmissions removed ÷ expected readmissions), with the percentile recomputed against the same 689 peers. With one fewer readmission the hospital would be at the 81.6th percentile, with two fewer at the 74.3rd, and with five fewer at the peer median.

[^cms]: CMS's actual cuts come from `reports/tables/cms_validation_client.csv` (CMS Table 15, FY2026 and FY2027). The peer group comes from `data/processed/cms_validation_hospital.parquet`, and peer-group medians from `reports/tables/cms_validation_thresholds.csv`. Condition flags and DRG payment ratios come from CMS's FY2026 supplemental file, read with `src.validate_cms.load_supplemental()`. The hip/knee share of CMS's cut is the hip/knee term, DRG ratio × (ERR − peer-group median) × 0.9627, divided by the sum of that term over all conditions: 0.59 of 0.88 percentage points. The CMS payment ratios for this hospital's five scored conditions sum to 0.096. With those ratios and our national thresholds, the cut would be 0.85%. With CMS's peer-group medians it is 0.88%, CMS's actual figure. The $17K change in section 5b comes from rerunning our penalty formula with the group 1 medians in place of the national medians.

[^peers]: Computed with `benchmarking.benchmark()` and `peer_summary()` using the peer keys shown. Northeast peers use `("ownership_group", "size_band", "census_region")`. Penalty medians and percentiles come from `mart_penalty_hospital`, restricted to the same peers.

[^shr]: Raw ratio and pass-through are computed from `fct_hospital_condition` (observed and expected rates, eligible discharges) and `shrinkage_k.parquet`. The fitted k values are 369 for heart failure, 192 for hip/knee, 414 for pneumonia, 396 for COPD and 370 for heart attack.

[^fy27]: For the hospital's whole FY2027 cut to be 0.04%, the hip/knee term alone, DRG ratio × (ERR − peer-group median) × 0.9628, can be no more than 0.0004. With the FY2026 hip/knee payment ratio (0.0156), that puts the hip/knee ERR within about 0.03 of its peer-group median, where it was 0.39 above in FY2026. This assumes the payment ratio stayed similar in FY2027. CMS has not yet published FY2027 condition-level results.
