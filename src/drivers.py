"""Where excess readmissions and penalties concentrate, and which hospital
characteristics stay associated with higher ERRs once the others are held equal.

Everything here is descriptive/associational. Hospital characteristics are not
randomly assigned, and several are related to how ERR itself is built (the
overall star rating includes readmission measures; MSPB episodes include
post-discharge readmission spending), so none of this is causal.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
import statsmodels.formula.api as smf

REFERENCE_LEVELS = {
    "ownership_group": "Non-profit",
    "size_band": "Mid volume",
    "census_region": "Midwest",
}

TERM_LABELS = {
    "C(ownership_group, Treatment('Non-profit'))[T.For-profit]": ("Ownership", "For-profit vs non-profit"),
    "C(ownership_group, Treatment('Non-profit'))[T.Government]": ("Ownership", "Government vs non-profit"),
    "C(size_band, Treatment('Mid volume'))[T.High volume]": ("Volume", "High vs mid HRRP volume"),
    "C(size_band, Treatment('Mid volume'))[T.Low volume]": ("Volume", "Low vs mid HRRP volume"),
    "C(census_region, Treatment('Midwest'))[T.Northeast]": ("Region", "Northeast vs Midwest"),
    "C(census_region, Treatment('Midwest'))[T.South]": ("Region", "South vs Midwest"),
    "C(census_region, Treatment('Midwest'))[T.West]": ("Region", "West vs Midwest"),
    "no_emergency_dept[T.True]": ("Emergency dept", "No emergency dept vs has one"),
    "mspb_per_005": ("Spending", "Spending index +0.05 (MSPB)"),
}


def regression_frame(hc: pd.DataFrame) -> pd.DataFrame:
    d = hc[hc["has_err"] & hc["is_payment_eligible"] & hc["mspb_ratio"].notna()].copy()
    d["err_points"] = (d["err"] - 1.0) * 100      # 1 point = 1% more readmissions than expected
    d["mspb_per_005"] = (d["mspb_ratio"] - 1.0) / 0.05
    d["no_emergency_dept"] = ~d["has_emergency_services"].astype(bool)
    return d


def adjusted_associations(hc: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    """OLS of ERR (in points) on hospital characteristics with condition fixed
    effects; standard errors clustered by hospital (each hospital contributes up
    to six rows)."""
    d = regression_frame(hc)
    formula = ("err_points ~ C(condition_code) + C(ownership_group, Treatment('Non-profit'))"
               " + C(size_band, Treatment('Mid volume')) + C(census_region, Treatment('Midwest'))"
               " + no_emergency_dept + mspb_per_005")
    fit = smf.ols(formula, data=d).fit(cov_type="cluster", cov_kwds={"groups": d["facility_id"]})
    ci = fit.conf_int()
    rows = []
    for term, (group, label) in TERM_LABELS.items():
        if term in fit.params.index:
            rows.append({"group": group, "term": label, "estimate": fit.params[term],
                         "ci_low": ci.loc[term, 0], "ci_high": ci.loc[term, 1], "p_value": fit.pvalues[term]})
    coefs = pd.DataFrame(rows)
    info = {"n_rows": int(fit.nobs), "n_hospitals": int(d["facility_id"].nunique()),
            "r_squared": float(fit.rsquared), "formula": formula}
    return coefs, info


def concentration_curve(pen_hosp: pd.DataFrame) -> pd.DataFrame:
    """Cumulative share of estimated penalty dollars by hospitals ranked high to low."""
    h = pen_hosp[pen_hosp["is_payment_eligible"]].sort_values("penalty_est_annual", ascending=False)
    total = h["penalty_est_annual"].sum()
    out = pd.DataFrame({
        "hospital_rank_share": np.arange(1, len(h) + 1) / len(h),
        "cum_penalty_share": h["penalty_est_annual"].cumsum().to_numpy() / total,
    })
    return out


def top_share(curve: pd.DataFrame, q: float) -> float:
    return float(curve.loc[curve["hospital_rank_share"] <= q, "cum_penalty_share"].max())


def condition_mix(segments: pd.DataFrame) -> pd.DataFrame:
    """National share of discharges, excess readmissions and penalty $ by condition."""
    c = segments[(segments["segment_dimension"] == "National") & (segments["condition_code"] != "ALL")].copy()
    for col, new in [("discharges_annual", "share_discharges"),
                     ("excess_readmissions_annual_pos", "share_excess_readmissions"),
                     ("penalty_annual", "share_penalty")]:
        c[new] = c[col] / c[col].sum()
    return c


def segment_table(segments: pd.DataFrame, dimension: str, condition: str = "ALL") -> pd.DataFrame:
    s = segments[(segments["segment_dimension"] == dimension) & (segments["condition_code"] == condition)].copy()
    nat = segments[(segments["segment_dimension"] == "National") & (segments["condition_code"] == condition)].iloc[0]
    s["share_discharges"] = s["discharges_annual"] / nat["discharges_annual"]
    s["share_excess_readmissions"] = s["excess_readmissions_annual_pos"] / nat["excess_readmissions_annual_pos"]
    s["share_penalty"] = s["penalty_annual"] / nat["penalty_annual"]
    s["excess_per_1000_discharges"] = 1000 * s["excess_readmissions_annual_net"] / s["discharges_annual"]
    return s
