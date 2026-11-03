"""HRRP penalty estimate (Python twin of sql/07_mart_penalty_estimate.sql).

The SQL mart is the base case. This module recomputes the same formula with
adjustable inputs so the dashboard can answer what-if questions (different
threshold, payment level, discharge imputation, or lower ERRs after an
intervention). ``src.quality`` checks that both give the same base-case answer.

HRRP formula (FY2019 onward, simplified to what our data supports):
    reduction % = sum_c (payments_c / total payments) * max(ERR_c - threshold_c, 0)
                  (only conditions with 25+ eligible discharges, i.e. with an ERR)
    adjustment factor = 1 - min(reduction %, 3%)
    penalty $ (per year) = reduction % * total base operating payments
                         = sum_c payments_c * max(ERR_c - threshold_c, 0)   (below the cap)
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd


@dataclass(frozen=True)
class PenaltyParams:
    penalty_cap_pct: float = 0.03
    hrrp_payment_share: float = 0.10
    threshold_method: str = "national_median"   # "national_median" | "one"
    payment_scale: float = 1.0                   # multiplies every condition's payment
    discharges_case: str = "base"                # "base" | "low" | "high" imputation


DISCHARGE_COLS = {"base": "discharges_est", "low": "discharges_est_low", "high": "discharges_est_high"}


def penalty_thresholds(fct: pd.DataFrame, method: str = "national_median") -> pd.Series:
    """Threshold ERR per condition (proxy for CMS's peer-group median)."""
    conds = sorted(fct["condition_code"].unique())
    if method == "one":
        return pd.Series(1.0, index=conds, name="threshold")
    elig = fct[fct["has_err"] & fct["is_payment_eligible"]]
    return elig.groupby("condition_code")["err"].median().rename("threshold")


def estimate(
    fct: pd.DataFrame,
    payments: pd.Series,
    params: PenaltyParams = PenaltyParams(),
    err: pd.Series | None = None,
    thresholds: pd.Series | None = None,
    performance_years: float = 3.0,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Estimate annual HRRP penalties.

    fct       : hospital x condition rows (fct_hospital_condition columns)
    payments  : base operating DRG payment per discharge, indexed by condition_code
    err       : optional replacement ERR values (same index as fct) for what-ifs
    thresholds: optional threshold ERR per condition (defaults to params.threshold_method)
    Returns (condition-level frame, hospital-level frame).
    """
    df = fct[["facility_id", "condition_code", "has_err", "is_payment_eligible"]].copy()
    df["err"] = fct["err"] if err is None else err
    if thresholds is None:
        thresholds = penalty_thresholds(fct, params.threshold_method)
    df["threshold"] = df["condition_code"].map(thresholds)
    disc_3yr = fct[DISCHARGE_COLS[params.discharges_case]]
    df["discharges_annual"] = disc_3yr / performance_years
    df["payment_per_discharge"] = df["condition_code"].map(payments) * params.payment_scale

    has = df["has_err"].fillna(False).astype(bool)
    elig = has & df["is_payment_eligible"].fillna(False).astype(bool)
    df["condition_payments"] = np.where(has, df["discharges_annual"] * df["payment_per_discharge"], 0.0)
    df["excess_ratio"] = np.where(has, np.maximum(df["err"] - df["threshold"], 0.0), 0.0)
    df["penalty_uncapped"] = np.where(elig, df["condition_payments"] * df["excess_ratio"], 0.0)

    hosp = df.groupby("facility_id", as_index=False).agg(
        is_payment_eligible=("is_payment_eligible", "max"),
        hrrp_condition_payments=("condition_payments", "sum"),
        penalty_uncapped=("penalty_uncapped", "sum"),
        n_conditions_penalized=("penalty_uncapped", lambda s: int((s > 0).sum())),
    )
    hosp["est_total_payments"] = hosp["hrrp_condition_payments"] / params.hrrp_payment_share
    hosp["penalty_cap"] = params.penalty_cap_pct * hosp["est_total_payments"]
    hosp["penalty"] = np.minimum(hosp["penalty_uncapped"], hosp["penalty_cap"])
    hosp["hits_cap"] = hosp["penalty_uncapped"] > hosp["penalty_cap"]
    hosp["is_penalized"] = hosp["is_payment_eligible"].astype(bool) & (hosp["penalty_uncapped"] > 0)
    hosp["reduction_pct"] = np.where(hosp["est_total_payments"] > 0,
                                     hosp["penalty"] / hosp["est_total_payments"], 0.0)

    scale = hosp.set_index("facility_id")
    factor = np.where(scale["penalty_uncapped"] > 0, scale["penalty"] / scale["penalty_uncapped"].where(
        scale["penalty_uncapped"] > 0, 1.0), 0.0)
    factor = pd.Series(factor, index=scale.index)
    df["penalty"] = df["penalty_uncapped"] * df["facility_id"].map(factor).fillna(0.0)
    return df, hosp


def summarize(hosp: pd.DataFrame) -> dict:
    pen = hosp[hosp["is_penalized"]]
    return {
        "n_hospitals_payment_eligible": int(hosp["is_payment_eligible"].sum()),
        "n_hospitals_penalized": int(len(pen)),
        "n_hospitals_at_cap": int(hosp["hits_cap"].sum()),
        "total_penalty": float(hosp["penalty"].sum()),
        "median_reduction_pct_penalized": float(pen["reduction_pct"].median()) if len(pen) else 0.0,
        "mean_penalty_penalized": float(pen["penalty"].mean()) if len(pen) else 0.0,
    }
