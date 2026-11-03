# 01 · Request and scope

## The request (verbatim)

> **From:** VP of Quality, hospital group
>
> 「我们集团有几家医院又要被 CMS 扣再入院罚款了。到底是哪些医院、哪些病种在拖后腿？和同类医院比我们差在哪？如果投一个出院随访项目，能省回多少？」
>
> *English:* "Several of our hospitals are about to be hit with CMS readmission penalties again. Which hospitals and which conditions are dragging us down? Where do we fall short compared with similar hospitals? If we invest in a post-discharge follow-up program, how much could we recover?"

In practice, this kind of request turns into four standard pieces of work: a **benchmarking analysis**, a **penalty exposure estimate**, a **business case** for the intervention, and a **dashboard plus memo** for leadership.

## Who decides what, and when

| | |
|---|---|
| **Decision-maker** | VP of Quality (sponsor), with the CFO, who has to approve the budget. |
| **Decision** | Whether to fund a post-discharge follow-up program, and if so, **at which hospitals and for which conditions**, at what budget. |
| **Decision point** | The next annual budget cycle. Program design needs to be settled before the program can start in early 2027 (assumed start: 2027-01-01). |
| **What would change the decision** | (1) Penalty exposure concentrated in a few hospitals and conditions → a targeted program; spread thin → a broad program, or no program. (2) The program pays back from penalties alone, or only once readmission costs are counted → the funding argument changes. (3) The payback depends on assumptions nobody can pin down → pilot first and measure before scaling. |

## Clarified analysis questions

The vague request is rewritten as five questions that the data can answer:

1. **Where is the problem?** Across US acute care hospitals, which conditions, regions, ownership types and hospital sizes account for most excess readmissions and most penalty dollars? *(National Picture)*
2. **How do we compare?** For each of our hospitals, how does its excess readmission ratio (ERR) for each condition compare with peer hospitals of the same ownership type and size? *(Hospital Benchmarking)*
3. **What is at stake?** How much does each hospital in our group lose to the HRRP penalty per year, which conditions drive it, and how far is each condition from the penalty threshold? *(Penalty Exposure)*
4. **Does the program pay back?** If we fund a post-discharge follow-up program for the conditions where we are above the threshold, what does it cost, how many readmissions and how many penalty dollars does it avoid, when do the savings arrive, and what has to be true for it to break even? *(Intervention Business Case)*
5. **What should we do?** Who should do what, the expected impact, how to measure it, and the risks. *(Recommendations)*

## Problem statement (used at the top of the README and the dashboard)

> The VP of Quality of a multi-hospital group has to decide whether to fund a post-discharge follow-up program, and where to deploy it, before the next budget cycle. This analysis uses CMS's public data on 3,055 hospitals to show which hospitals and conditions drive the group's readmission penalties, how each hospital compares with similar hospitals, how much is at stake each year, and under which assumptions a follow-up program pays for itself. That lets the decision rest on hospital- and condition-level numbers instead of the system-wide average.

## Scope

**In scope:** the six HRRP conditions (heart failure, pneumonia, COPD, heart attack, bypass surgery, hip/knee replacement); the FY2026 HRRP program year (performance period 2021-07-01 to 2024-06-30); hospital-level analysis for all hospitals in the CMS files; an illustrative client group of hospitals (see `docs/00_plan.md`), used to answer the "our group" questions.

**Out of scope:** patient-level prediction (the data is hospital-level, not patient-level); causal claims about *why* a hospital has high readmissions; other CMS value-based programs (Value-Based Purchasing, HAC Reduction Program); Medicare Advantage patients, who are not in the HRRP measures for this period.

## Important caveat on "our group"

CMS files do not say which hospitals belong to which health system. To answer the "our group" questions, the analysis uses an **illustrative client group**, defined by a transparent, reproducible rule (`docs/00_plan.md`, `config.yaml`). It is **not** an actual health system, and nothing here implies any relationship with the hospitals involved. Every page of the dashboard can be switched to any hospital or group of hospitals.
