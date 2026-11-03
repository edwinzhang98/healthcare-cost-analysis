"""Business case for a post-discharge follow-up program (transitional care).

What the program does in the model
----------------------------------
For the hospitals and conditions it targets, a share of discharged Medicare
patients (``reach``) is enrolled, and enrolled patients' 30-day readmission risk
falls by ``relative_reduction``. Two kinds of benefit follow:

1. Fewer readmissions (real events): enrolled x readmission rate x reduction.
   Under fee-for-service their cost mostly falls on the payer (traditional
   Medicare or a Medicare Advantage plan); the hospital keeps only
   ``hospital_share_of_savings`` (e.g., through risk-based contracts).
2. A lower CMS score (ERR) and therefore a smaller HRRP penalty. CMS shrinks
   small hospitals' results toward average, so only part of the real change
   reaches the ERR (``src.shrinkage``):
       new ERR = ERR - pass_through x (reach x reduction) x observed / expected

Rules that apply to a program starting in 2027 (FY2027 onward)
--------------------------------------------------------------
* The CMS window is 2 years (July N-4 to June N-2), not 3.
* Medicare Advantage (MA) patients count in the ERR, but the penalty is still
  charged only on traditional (fee-for-service) Medicare payments. So to move
  the score, the program must serve MA patients too: enrollment and cost scale
  with all Medicare patients (FFS volume / (1 - ma_share)), the penalty base
  does not. Setting ma_share = 0 reproduces the FY2026 rules.
Baseline exposure = the FY2026 estimate (latest hospital-level data), assumed to
persist if nothing changes.

Perspectives
------------
hospital  : avoided penalty
            + share x readmission cost avoided            (readmissions the hospital is at risk for)
            - (1 - share) x lost margin x readmissions    (fee-for-service: the hospital loses the
                                                            payment but saves only variable cost)
            - program cost
combined  : readmission cost avoided - program cost   (payers + hospital together; the penalty
            and fee-for-service payments are transfers between them, so they net out)
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, replace
from datetime import date

import numpy as np
import pandas as pd

from src.shrinkage import pass_through


@dataclass(frozen=True)
class ProgramParams:
    target_conditions: tuple = ("HF", "PN", "COPD", "AMI")
    targeting: str = "above_threshold"        # "above_threshold" | "all"
    reach: float = 0.50
    relative_reduction: float = 0.10          # base effect (pneumonia / heart attack); see EFFECT_MULTIPLIERS
    effect_multipliers: tuple = (("HF", 1.5), ("PN", 1.0), ("AMI", 1.0), ("COPD", 0.5),
                                 ("CABG", 0.3), ("HIP_KNEE", 0.3))
    risk_multiplier: float = 1.0              # enrolled patients' readmission risk vs the condition average
                                              # (>1 when the program enrolls higher-risk patients first)
    cost_per_enrollee: float = 400.0
    fixed_cost_per_hospital: float = 25_000.0
    cost_per_readmission: float = 19_000.0
    hospital_share_of_savings: float = 0.0    # share of avoided readmissions whose cost the hospital bears (risk contracts)
    lost_margin_per_readmission: float = 1_750.0  # FFS: payment lost minus variable cost saved, per avoided readmission
    ma_share: float = 0.50                    # share of Medicare patients in MA (counted in ERR from FY2027)
    pass_through_mode: str = "volume"         # "volume" | "full"
    payment_scale: float = 1.0
    penalty_cap_pct: float = 0.03
    hrrp_payment_share: float = 0.133
    neutrality_modifier: float = 0.9627
    data_years: float = 3.0                   # length of the window in our data (FY2026: 36 months)
    window_years: float = 2.0                 # CMS window from FY2027

    def to_dict(self) -> dict:
        d = asdict(self)
        d["target_conditions"] = list(self.target_conditions)
        d["effect_multipliers"] = dict(self.effect_multipliers)
        return d

    def condition_effect(self, condition_codes: np.ndarray) -> np.ndarray:
        """Relative readmission reduction among enrolled patients, by condition
        (evidence is strongest for heart failure, weakest for COPD and surgery)."""
        mult = dict(self.effect_multipliers)
        return np.minimum(np.array([self.relative_reduction * mult.get(c, 1.0) for c in condition_codes]), 0.9)


@dataclass
class ModelInputs:
    """Numpy arrays for one set of hospitals (all of their condition rows)."""
    facility_id: np.ndarray
    condition_code: np.ndarray
    hosp_idx: np.ndarray
    n_hosp: int
    has_err: np.ndarray
    payment_eligible: np.ndarray
    above_threshold: np.ndarray
    err: np.ndarray
    threshold: np.ndarray
    expected: np.ndarray
    observed: np.ndarray
    discharges_3yr: np.ndarray        # FFS eligible discharges in the FY2026 window (observed or imputed)
    payment_per_discharge: np.ndarray
    k: np.ndarray

    @classmethod
    def build(cls, hc: pd.DataFrame, payments: pd.Series, k_by_condition: pd.Series,
              thresholds: pd.Series | None = None) -> "ModelInputs":
        hc = hc.reset_index(drop=True)
        codes, uniques = pd.factorize(hc["facility_id"])
        thr = (hc["condition_code"].map(thresholds) if thresholds is not None
               else hc["penalty_threshold_err"]).to_numpy(float)
        err = hc["err"].to_numpy(float)
        exp_ = hc["expected_rate_pct"].to_numpy(float)
        pred = hc["predicted_rate_pct"].to_numpy(float)
        disc = hc["discharges_est"].fillna(0).to_numpy(float)
        k = hc["condition_code"].map(k_by_condition).to_numpy(float)
        # observed rate: published where available, otherwise implied by undoing CMS shrinkage
        lam = np.where(disc > 0, pass_through(disc, k), 1.0)
        implied_obs = exp_ + (pred - exp_) / np.where(lam > 0, lam, 1.0)
        obs = hc["observed_rate_pct"].to_numpy(float)
        obs = np.where(np.isnan(obs), implied_obs, obs)
        obs = np.clip(np.nan_to_num(obs, nan=0.0), 0.0, 100.0)
        has = hc["has_err"].fillna(False).to_numpy(bool)
        return cls(
            facility_id=np.asarray(uniques), condition_code=hc["condition_code"].to_numpy(),
            hosp_idx=codes, n_hosp=len(uniques), has_err=has,
            payment_eligible=hc["is_payment_eligible"].fillna(False).to_numpy(bool),
            above_threshold=has & (err > thr), err=np.nan_to_num(err, nan=0.0), threshold=thr,
            expected=np.nan_to_num(exp_, nan=1.0), observed=obs, discharges_3yr=disc,
            payment_per_discharge=hc["condition_code"].map(payments).to_numpy(float), k=k,
        )

    def subset(self, facility_ids) -> "ModelInputs":
        keep = np.isin(self.facility_id[self.hosp_idx], list(facility_ids))
        codes, uniques = pd.factorize(self.facility_id[self.hosp_idx][keep])
        return ModelInputs(
            facility_id=np.asarray(uniques), condition_code=self.condition_code[keep], hosp_idx=codes,
            n_hosp=len(uniques), has_err=self.has_err[keep], payment_eligible=self.payment_eligible[keep],
            above_threshold=self.above_threshold[keep], err=self.err[keep], threshold=self.threshold[keep],
            expected=self.expected[keep], observed=self.observed[keep],
            discharges_3yr=self.discharges_3yr[keep], payment_per_discharge=self.payment_per_discharge[keep],
            k=self.k[keep])


def _penalties(m: ModelInputs, err: np.ndarray, p: ProgramParams) -> np.ndarray:
    """Hospital-level annual penalty (with 3% cap) for given ERR values.
    The penalty base is traditional-Medicare (FFS) payments only."""
    pay = np.where(m.has_err, m.discharges_3yr / p.data_years * m.payment_per_discharge * p.payment_scale, 0.0)
    elig = m.has_err & m.payment_eligible
    contrib = np.where(elig, p.neutrality_modifier * pay * np.maximum(err - m.threshold, 0.0), 0.0)
    unc = np.bincount(m.hosp_idx, weights=contrib, minlength=m.n_hosp)
    cap = p.penalty_cap_pct * np.bincount(m.hosp_idx, weights=pay, minlength=m.n_hosp) / p.hrrp_payment_share
    return np.minimum(unc, cap)


def targeted_mask(m: ModelInputs, p: ProgramParams) -> np.ndarray:
    in_scope = np.isin(m.condition_code, list(p.target_conditions)) & m.has_err
    if p.targeting == "above_threshold":
        in_scope &= m.above_threshold
    return in_scope


def evaluate(m: ModelInputs, p: ProgramParams, effect_scale: float = 1.0) -> dict:
    """Steady-state annual results. effect_scale (0-1) scales the program effect on the
    ERR only (used for the year-by-year phase-in of the CMS window)."""
    tgt = targeted_mask(m, p)
    risk = min(p.risk_multiplier, 1.0 / max(p.reach, 1e-9))   # cannot avoid more readmissions than exist
    # share of the condition's readmissions avoided = reach x risk of enrollees x reduction among them
    r_eff = np.where(tgt, p.reach * risk * p.condition_effect(m.condition_code), 0.0)
    ffs_annual = m.discharges_3yr / p.data_years
    cohort_annual = ffs_annual / (1.0 - p.ma_share)          # all Medicare patients counted in the ERR
    n_window = cohort_annual * p.window_years
    if p.pass_through_mode == "volume":
        lam = np.where(n_window > 0, pass_through(n_window, m.k), 0.0)
    else:
        lam = np.where(n_window > 0, 1.0, 0.0)
    new_err = m.err - lam * r_eff * effect_scale * m.observed / m.expected

    enrollees = np.where(tgt, cohort_annual * p.reach, 0.0)
    avoided = np.where(tgt, cohort_annual * m.observed / 100.0 * r_eff, 0.0)

    pen_before = _penalties(m, m.err, p)
    pen_after = _penalties(m, new_err, p)

    h, n = m.hosp_idx, m.n_hosp
    runs = np.bincount(h, weights=tgt.astype(float), minlength=n) > 0
    var_cost = np.bincount(h, weights=enrollees * p.cost_per_enrollee, minlength=n)
    fixed = np.where(runs, p.fixed_cost_per_hospital, 0.0)
    readm_avoided = np.bincount(h, weights=avoided, minlength=n)
    readm_savings = readm_avoided * p.cost_per_readmission
    avoided_penalty = pen_before - pen_after
    cost = var_cost + fixed
    hosp = pd.DataFrame({
        "facility_id": m.facility_id,
        "program_runs": runs,
        "enrollees": np.bincount(h, weights=enrollees, minlength=n),
        "program_cost": cost,
        "penalty_before": pen_before,
        "penalty_after": pen_after,
        "avoided_penalty": avoided_penalty,
        "readmissions_avoided": readm_avoided,
        "readmission_savings": readm_savings,
        "lost_margin": (1 - p.hospital_share_of_savings) * readm_avoided * p.lost_margin_per_readmission,
        "hospital_net": (avoided_penalty + p.hospital_share_of_savings * readm_savings
                         - (1 - p.hospital_share_of_savings) * readm_avoided * p.lost_margin_per_readmission - cost),
        "combined_net": readm_savings - cost,
    })
    rows = pd.DataFrame({
        "facility_id": m.facility_id[h], "condition_code": m.condition_code, "targeted": tgt,
        "err": np.where(m.has_err, m.err, np.nan), "new_err": np.where(m.has_err, new_err, np.nan),
        "threshold": m.threshold, "pass_through": lam, "enrollees": enrollees, "readmissions_avoided": avoided,
    })
    tot = hosp.drop(columns=["facility_id", "program_runs"]).sum()
    totals = {k: float(v) for k, v in tot.items()}
    totals["n_hospitals_running"] = int(runs.sum())
    benefit = (totals["avoided_penalty"] + p.hospital_share_of_savings * totals["readmission_savings"]
               - totals["lost_margin"])
    totals["hospital_benefit"] = benefit
    totals["hospital_roi"] = benefit / totals["program_cost"] if totals["program_cost"] > 0 else np.nan
    totals["cost_per_readmission_avoided"] = (totals["program_cost"] / totals["readmissions_avoided"]
                                              if totals["readmissions_avoided"] > 0 else np.nan)
    return {"hospitals": hosp, "rows": rows, "totals": totals}


# ---------------------------------------------------------------- phase-in
def _months(start: date, n: int) -> list[date]:
    out, y, mo = [], start.year, start.month
    for _ in range(n):
        out.append(date(y, mo, 1))
        mo += 1
        if mo > 12:
            y, mo = y + 1, 1
    return out


def fiscal_year(d: date) -> int:
    return d.year + 1 if d.month >= 10 else d.year


def hrrp_window(fy: int) -> tuple[date, date, int]:
    """CMS performance window used for FY penalties: (start, end, months).
    FY2027 onward: July (FY-4) to June (FY-2), 24 months. Through FY2026: 36 months."""
    if fy >= 2027:
        return date(fy - 4, 7, 1), date(fy - 2, 6, 30), 24
    return date(fy - 5, 7, 1), date(fy - 2, 6, 30), 36


def phase_in(m: ModelInputs, p: ProgramParams, start: date = date(2027, 1, 1),
             first_fy: int = 2027, n_years: int = 6, ramp_first_year: float = 0.5,
             discount_rate: float = 0.03) -> pd.DataFrame:
    """Year-by-year cash view. Readmission savings and costs start with the program;
    penalty relief only arrives as program months enter the CMS window."""
    steady = evaluate(m, p)["totals"]
    months = _months(start, 12 * (n_years + 6))
    weight = {mo: (ramp_first_year if i < 12 else 1.0) for i, mo in enumerate(months)}
    fixed_total = steady["n_hospitals_running"] * p.fixed_cost_per_hospital
    rows = []
    for i, fy in enumerate(range(first_fy, first_fy + n_years)):
        fy_months = [mo for mo in months if fiscal_year(mo) == fy]
        eff = sum(weight[mo] for mo in fy_months) / 12.0
        active = len(fy_months) / 12.0
        w0, w1, wm = hrrp_window(fy)
        in_window = sum(weight[mo] for mo in months if w0 <= mo <= w1) / wm
        pen = evaluate(m, p, effect_scale=in_window)["totals"]["avoided_penalty"] if in_window > 0 else 0.0
        cost = fixed_total * active + (steady["program_cost"] - fixed_total) * eff
        readm = steady["readmission_savings"] * eff
        lost = steady["lost_margin"] * eff
        hospital_net = pen + p.hospital_share_of_savings * readm - lost - cost
        rows.append({
            "fiscal_year": fy, "cms_window": f"{w0:%b %Y}–{w1:%b %Y}",
            "program_share_of_cms_window": in_window, "program_cost": cost,
            "avoided_penalty": pen, "readmission_savings": readm, "lost_margin": lost,
            "readmissions_avoided": steady["readmissions_avoided"] * eff,
            "hospital_net": hospital_net, "combined_net": readm - cost,
            "discount_factor": 1 / (1 + discount_rate) ** i,
        })
    df = pd.DataFrame(rows)
    df["hospital_net_cum"] = df["hospital_net"].cumsum()
    df["combined_net_cum"] = df["combined_net"].cumsum()
    df["hospital_npv_cum"] = (df["hospital_net"] * df["discount_factor"]).cumsum()
    return df


# ---------------------------------------------------------------- sensitivity
TORNADO_PARAMS = {
    "relative_reduction": "Readmission reduction among enrolled",
    "reach": "Share of patients enrolled",
    "cost_per_enrollee": "Cost per enrolled patient",
    "fixed_cost_per_hospital": "Fixed cost per hospital",
    "payment_scale": "Medicare payment per discharge (penalty size)",
    "ma_share": "Medicare Advantage share of patients",
    "lost_margin_per_readmission": "Lost fee-for-service margin per avoided readmission",
    "cost_per_readmission": "Cost per readmission",
    "hospital_share_of_savings": "Hospital share of readmission savings",
}


def tornado(m: ModelInputs, p: ProgramParams, pct: float = 0.30, metric: str = "hospital_net") -> pd.DataFrame:
    base = evaluate(m, p)["totals"][metric]
    out = []
    for name, label in TORNADO_PARAMS.items():
        val = getattr(p, name)
        if val == 0:
            continue
        lo_v, hi_v = val * (1 - pct), val * (1 + pct)
        if name in ("reach", "ma_share", "hospital_share_of_savings"):
            hi_v = min(hi_v, 0.95)
        lo = evaluate(m, replace(p, **{name: lo_v}))["totals"][metric]
        hi = evaluate(m, replace(p, **{name: hi_v}))["totals"][metric]
        out.append({"parameter": name, "label": label, "base_value": val,
                    "low_value": lo_v, "high_value": hi_v,
                    "metric_at_low": lo, "metric_at_high": hi, "base_metric": base,
                    "swing": abs(hi - lo),
                    "sign_flips": bool(np.sign(lo) != np.sign(base) or np.sign(hi) != np.sign(base))})
    return pd.DataFrame(out).sort_values("swing", ascending=False).reset_index(drop=True)


def break_even(m: ModelInputs, p: ProgramParams, param: str = "relative_reduction",
               metric: str = "hospital_net", lo: float = 0.0, hi: float = 1.0) -> float | None:
    """Value of `param` at which `metric` = 0 (bisection; metric must be monotonic)."""
    f = lambda v: evaluate(m, replace(p, **{param: v}))["totals"][metric]
    flo, fhi = f(lo), f(hi)
    if np.sign(flo) == np.sign(fhi):
        return None
    for _ in range(60):
        mid = (lo + hi) / 2
        fm = f(mid)
        if np.sign(fm) == np.sign(flo):
            lo, flo = mid, fm
        else:
            hi = mid
    return (lo + hi) / 2


def grid(m: ModelInputs, p: ProgramParams, x_param: str, x_values, y_param: str, y_values,
         metric: str = "hospital_net") -> pd.DataFrame:
    rows = []
    for xv in x_values:
        for yv in y_values:
            t = evaluate(m, replace(p, **{x_param: xv, y_param: yv}))["totals"]
            rows.append({x_param: xv, y_param: yv, metric: t[metric]})
    return pd.DataFrame(rows)


def monte_carlo(m: ModelInputs, p: ProgramParams, ranges: dict[str, tuple[float, float, float]],
                n: int = 2000, seed: int = 42) -> pd.DataFrame:
    """Probabilistic sensitivity analysis: draw each uncertain input from a
    triangular(low, base, high) distribution. Fixed seed => reproducible."""
    rng = np.random.default_rng(seed)
    draws = {k: rng.triangular(lo, mode, hi, size=n) for k, (lo, mode, hi) in ranges.items()}
    out = []
    for i in range(n):
        t = evaluate(m, replace(p, **{k: float(v[i]) for k, v in draws.items()}))["totals"]
        out.append({**{k: float(v[i]) for k, v in draws.items()},
                    "hospital_net": t["hospital_net"], "combined_net": t["combined_net"],
                    "avoided_penalty": t["avoided_penalty"], "program_cost": t["program_cost"]})
    return pd.DataFrame(out)
