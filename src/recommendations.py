"""Key findings and recommendations built from key_metrics.json (one source for the dashboard and report)."""
from __future__ import annotations

from src.charts import money, pct


def cents(x: float) -> str:
    """Benefit-cost ratio as money back per $1, e.g. $0.75."""
    return f"${x:.2f}"


def payer_saving(m: dict) -> float:
    p = m["business_case"]["params_targeted"]
    return p["payment_to_cost"] * p["cost_per_readmission"]


def _short(name: str) -> str:
    return name.title().replace(" Of ", " of ").replace(" At ", " at ")


def peer_summary(m: dict) -> dict:
    grid = m["client"]["peer_percentiles"]
    above = [g for g in grid if (g["index_percentile"] or 0) > 50]
    worst5 = [g for g in grid if (g["index_percentile"] or 0) >= 80]
    hf = [g for g in grid if (g.get("HF") or 0) >= 90]
    pn = [g for g in grid if (g.get("PN") or 0) >= 75]
    copd = [g for g in grid if (g.get("COPD") or 0) >= 75]
    return {"n": len(grid), "above_median": len(above), "worst_fifth": len(worst5),
            "hf_worst": [_short(g["name"]) for g in hf], "pn_worse": len(pn), "copd_worse": len(copd)}


def findings(m: dict) -> list[str]:
    """Three headline findings (plain language) answering the VP's three questions."""
    cl, bc = m["client"], m["business_case"]
    sc = bc["scenarios"]
    broad, pilot = sc["broad_all"], sc["targeted_pilot"]
    be, mc = bc["break_even"], bc["monte_carlo"]
    ps = peer_summary(m)
    top2 = [h["name"] for h in cl["hospitals"][:2]]
    v = m.get("validation") or {}
    pv = v.get("persistence") or {}
    pers = pv.get("slope_fy2027_on_fy2026")
    pers_top = (pv.get("top_decile_mean_cut_fy2026"), pv.get("top_decile_mean_cut_fy2027"))
    return [
        (f"**Where the penalty comes from.** We estimate the group loses about {money(cl['total_penalty'])} a year to the "
         f"readmission penalty (FY2026 program). Two hospitals, {_short(top2[0])} and {_short(top2[1])}, carry "
         f"{pct(cl['top2_share'])} of it. Heart failure ({money(cl['penalty_by_condition']['HF'])}) and hip/knee "
         f"replacement ({money(cl['penalty_by_condition']['HIP_KNEE'])}) are the largest drivers."),
        (f"**How we compare.** {ps['above_median']} of {ps['n']} hospitals readmit more patients than their typical peer "
         f"(same ownership and Medicare volume), and {ps['worst_fifth']} are in the bottom 20% of similar hospitals. The "
         f"gaps are specific: heart failure at {', '.join(ps['hf_worst'])} (worse than 90% or more of peers); pneumonia "
         f"and COPD at {ps['pn_worse']} hospitals each; hip/knee at {_short(cl['target_hospital_name'])}. Part of this is "
         f"regional: New Jersey has the second-highest average readmission ratio of any state."),
        (f"**What a follow-up program can recover.** Less than it costs. Group-wide it would cost about "
         f"{money(broad['program_cost'])} a year and avoid about {money(broad['avoided_penalty'])} in penalties at full "
         f"strength (FY2032), about {cents(broad['benefit_cost_ratio'])} per $1; it cannot break even at any plausible "
         f"effect size. Even at the two best-placed hospitals it returns about {cents(pilot['benefit_cost_ratio'])} per $1 "
         f"(hospital net {money(pilot['hospital_net'])} a year). The pilot breaks even only if it cuts readmissions by at "
         f"least {pct(be['pilot_relative_reduction'])} (recent trials: about 10%), costs under "
         f"{money(be['pilot_cost_per_enrollee'])} per patient, or payers return about "
         f"{pct(be['pilot_hospital_share_of_savings'])} of their savings. Across {mc['runs']:,} simulated scenarios it pays "
         f"for itself for the hospital {pct(mc['p_hospital_net_positive'])} of the time. Penalties are also a moving target"
         + (f": they drift back toward the average, so hospitals with the biggest FY2026 cuts saw them shrink by about "
            f"{1 - pers_top[1] / pers_top[0]:.0%} in FY2027 while small cuts grew." if pers else ".")),
    ]


def build(m: dict) -> list[dict]:
    cl, bc, nat = m["client"], m["business_case"], m["national"]
    sc = bc["scenarios"]
    broad, pilot, shared = sc["broad_all"], sc["targeted_pilot"], sc["targeted_pilot_risk30"]
    be, pw = bc["break_even"], bc["pilot_power"]
    pilots = " and ".join(_short(n) for n in cl["pilot_hospital_names"])
    tgt = cl["benchmark_target"]
    hk = tgt.get("HIP_KNEE", {})
    hk_pen = cl.get("target_penalty_by_condition", {}).get("HIP_KNEE", 0)
    v = m.get("validation") or {}
    cms27 = next((c for c in v.get("client", []) if c["facility_id"] == cl["target_hospital"]), {})
    hk_risk = ("CMS's FY2027 cut for this hospital (in effect now) fell to "
               f"{pct(cms27.get('cms_reduction_fy2027'), 2)}, so the problem may already be easing"
               if cms27.get("cms_reduction_fy2027") is not None else "Small numbers")
    return [
        {
            "what": "Do not fund a group-wide post-discharge follow-up program on financial grounds.",
            "who": "VP of Quality and CFO (budget decision)",
            "impact": (f"Avoids about {money(broad['program_cost'])} a year of spending that would recover about "
                       f"{money(broad['avoided_penalty'])} in penalties a year at full strength (FY2032; about {cents(broad['benefit_cost_ratio'])} per $1). "
                       f"Even counting the readmission costs saved by payers it loses "
                       f"{money(-broad['combined_net'])} a year."),
            "measure": "Revisit after the pilot readout.",
            "risk": "Patients at the other hospitals don't get the program for now. Readmissions are a quality issue, not only a cost.",
        },
        {
            "what": (f"If leadership wants to reduce readmissions anyway, as a quality goal rather than a financial one, "
                     f"run a 12-month pilot at {pilots}, where heart failure is worst and each program dollar returns the "
                     f"most, for higher-risk heart failure and pneumonia patients: medication review before discharge, a "
                     f"nurse contact within 72 hours and a clinic visit within 7 days. Not phone calls alone: trials show "
                     f"no measurable effect from calls alone. Princeton's penalty is mostly hip/knee, which follow-up visits "
                     f"barely move (see the hip/knee item)."),
            "who": "Chief nursing officers and care-management leads at the two hospitals",
            "impact": (f"About {money(pilot['program_cost'])} a year for about {pilot['readmissions_avoided']:.0f} fewer "
                       f"readmissions and about {money(pilot['avoided_penalty'])} a year less penalty at full strength "
                       f"(FY2032). On base assumptions it still loses about {money(-pilot['hospital_net'])} a year for the "
                       f"hospital, and nothing comes back before late 2028."),
            "measure": (f"Month 12 (stop or continue): at least 80% of enrolled patients get all three steps, cost stays at "
                        f"or under $400 per patient, and ED visits, observation stays and deaths do not rise against a "
                        f"comparison group. Month 24 (keep or stop): readmissions among enrolled patients, pooled across both "
                        f"hospitals, fall about 16% (the pooled equivalent of the {pct(be['pilot_relative_reduction'])} break-even) at $400 per "
                        f"patient, or about 12% with at least "
                        f"{pct(be['pilot_hospital_share_of_savings'])} payer co-funding or a cost at or under "
                        f"{money(be['pilot_cost_per_enrollee'])}. About {pw['enrolled_first_24_months']:.0f} patients cannot "
                        f"prove such an effect statistically (that needs about {pw['n_per_group_for_break_even_effect']:,.0f} "
                        f"per group), so read the result alongside published trials."),
            "risk": ("Program effects usually shrink outside trials; CMS scores react only after two years and swing from "
                     "year to year; a before-and-after comparison would credit the program with natural improvement."),
        },
        {
            "what": ("Ask the Medicare Advantage plans and ACO partners the group contracts with to co-fund the pilot "
                     "through shared savings, and sign terms first."),
            "who": "CFO and managed-care contracting",
            "impact": (f"Payers save about {money(payer_saving(m))} per avoided readmission. If about "
                       f"{pct(be['pilot_hospital_share_of_savings'])} comes back to us, the pilot breaks even "
                       f"(at 30%: {money(shared['hospital_net'])} a year)."),
            "measure": "Term sheet signed before the pilot starts; savings reported quarterly.",
            "risk": ("Plans may decline or dispute which savings the program caused; ACO shared savings are settled on "
                     "total cost of care at the ACO level, not per readmission, so the share must be written into the terms."),
        },
        {
            "what": (f"Check hip/knee replacement at {_short(cl['target_hospital_name'])} before committing money: "
                     f"in FY2026 its ratio was {hk.get('err', float('nan')):.2f}, worse than "
                     f"{hk.get('percentile', float('nan')):.0f}% of peers."),
            "who": "Orthopedics chair with the quality team",
            "impact": (f"Hip/knee drove about {money(hk_pen)} a year of that hospital's estimated FY2026 penalty, from "
                       "roughly two extra readmissions a year. CMS charges about "
                       f"{money(nat['conditions']['HIP_KNEE']['penalty_per_excess_readmission'])} per hip/knee readmission "
                       "above the threshold, so a case review is cheap compared with the stakes."),
            "measure": "Review every hip/knee readmission from the last two years; re-check against FY2027 data in early 2027.",
            "risk": hk_risk + ".",
        },
        {
            "what": "Track readmissions monthly and refresh this analysis when CMS posts FY2027 hospital data (early 2027).",
            "who": "Quality analytics",
            "impact": ("CMS scores lag by two years and swing from year to year, so monthly tracking catches problems early. "
                       "Sepsis enters the penalty in FY2030 (FY2027 IPPS final rule)."),
            "measure": "Monthly dashboard by hospital and condition; updated penalty estimates each CMS release.",
            "risk": "From FY2027 the measures include Medicare Advantage patients, so old and new scores are not directly comparable.",
        },
    ]
