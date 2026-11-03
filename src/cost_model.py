"""Business case for a post-discharge follow-up program (transitional care).

What the program does in the model
----------------------------------
For the hospitals and conditions it targets, a share of discharged Medicare
patients (``reach``) is enrolled, and enrolled patients' 30-day readmission risk
falls by ``relative_reduction`` (scaled by condition: the trial evidence is
stronger for heart failure, weaker for COPD and surgery). Two benefits follow:

1. Fewer readmissions (real events): enrolled x readmission rate x reduction.
2. A lower CMS score (ERR) and therefore a smaller HRRP penalty. CMS shrinks
   small hospitals' results toward average, so only part of the real change
   reaches the ERR (``src.shrinkage``):
       new ERR = ERR - pass_through x (reach x risk x reduction) x observed / expected

Baseline: what would happen without the program
-----------------------------------------------
Penalties regress toward the mean: hospitals with the highest ERR today tend to
look better in later windows even if nothing changes (published HRRP research;
CMS's actual FY2027 cut is about 0.58 x the FY2026 cut + 0.16 points: big cuts shrink,
small ones grow). So the
FY2029-FY2032 baseline is a forecast, not today's penalty:
       forecast ERR = 1 + persistence x (ERR - 1)       (same for the observed rate)
persistence = 1 reproduces "today's penalty continues".

Rules that apply to a program starting in 2027 (FY2027 onward)
--------------------------------------------------------------
* The CMS window is 2 years (July N-4 to June N-2), not 3.
* Medicare Advantage (MA) patients count in the ERR, but the penalty is still
  charged only on traditional (fee-for-service) Medicare payments. A program
  that enrolls by risk rather than payer serves MA patients too: enrollment and
  cost scale with all Medicare patients (FFS volume / (1 - ma_share)), the penalty base
  does not. Setting ma_share = 0 reproduces the FY2026 rules.

Money per avoided readmission (one consistent set, from two MedPAC figures)
--------------------------------------------------------------------------
C = hospital cost of a readmission (HCUP)         payment P = payment_to_cost x C
V = variable cost = variable_cost_share x C       lost margin = P - V
Payers save P, the hospital loses P but saves V, so together they save V.

Perspectives
------------
hospital  : avoided penalty
            + share x P x readmissions avoided   (share of payer savings returned to the hospital,
                                                  e.g., shared-savings / ACO contracts)
            - lost margin x readmissions avoided (fee-for-service payment lost minus variable
                                                  cost saved; 0 if freed beds are refilled)
            - program cost
combined  : V x readmissions avoided - program cost   (payers + hospital together; the penalty
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
    effect_multipliers: tuple = (("HF", 1.2), ("PN", 1.0), ("AMI", 1.0), ("COPD", 0.5),
                                 ("CABG", 0.3), ("HIP_KNEE", 0.3))
    risk_multiplier: float = 1.0              # enrolled patients' readmission risk vs the condition average
                                              # (>1 when the program enrolls higher-risk patients first)
    cost_per_enrollee: float = 400.0
    fixed_cost_per_hospital: float = 25_000.0
    cost_per_readmission: float = 19_000.0   # hospital cost of one readmission (C)
    payment_to_cost: float = 0.892            # Medicare payment / cost (FFS margin -12.1%)
    variable_cost_share: float = 0.80         # share of cost that disappears when a stay is avoided
    hospital_share_of_savings: float = 0.0    # share of payer savings returned to the hospital (shared savings)
    beds_refilled: bool = False               # if freed beds are refilled, no margin is lost
    persistence: float = 0.5                  # share of today's ERR excess expected to persist (regression to mean)
    ma_share: float = 0.41                    # share of Medicare patients in MA (counted in ERR from FY2027)
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

    @property
    def payment_per_readmission(self) -> float:
        return self.payment_to_cost * self.cost_per_readmission

    @property
    def variable_cost_per_readmission(self) -> float:
        return self.variable_cost_share * self.cost_per_readmission

    @property
    def lost_margin_per_readmission(self) -> float:
        return 0.0 if self.beds_refilled else max(self.payment_per_readmission - self.variable_cost_per_readmission, 0.0)

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
    # baseline forecast for FY2029+ (regression to the mean), then the program effect on top
    base_err = np.where(m.has_err, 1.0 + p.persistence * (m.err - 1.0), m.err)
    base_obs = np.clip(m.expected + p.persistence * (m.observed - m.expected), 0.0, 100.0)
    new_err = base_err - lam * r_eff * effect_scale * base_obs / m.expected

    enrollees = np.where(tgt, cohort_annual * p.reach, 0.0)
    avoided = np.where(tgt, cohort_annual * base_obs / 100.0 * r_eff, 0.0)

    pen_today = _penalties(m, m.err, p)
    pen_before = _penalties(m, base_err, p)
    pen_after = _penalties(m, new_err, p)

    h, n = m.hosp_idx, m.n_hosp
    runs = np.bincount(h, weights=tgt.astype(float), minlength=n) > 0
    var_cost = np.bincount(h, weights=enrollees * p.cost_per_enrollee, minlength=n)
    fixed = np.where(runs, p.fixed_cost_per_hospital, 0.0)
    readm_avoided = np.bincount(h, weights=avoided, minlength=n)
    payer_savings = readm_avoided * p.payment_per_readmission
    shared = p.hospital_share_of_savings * payer_savings
    lost = readm_avoided * p.lost_margin_per_readmission
    system_savings = readm_avoided * p.variable_cost_per_readmission
    avoided_penalty = pen_before - pen_after
    cost = var_cost + fixed
    hosp = pd.DataFrame({
        "facility_id": m.facility_id,
        "program_runs": runs,
        "enrollees": np.bincount(h, weights=enrollees, minlength=n),
        "program_cost": cost,
        "penalty_today": pen_today,
        "penalty_before": pen_before,
        "penalty_after": pen_after,
        "avoided_penalty": avoided_penalty,
        "readmissions_avoided": readm_avoided,
        "payer_savings": payer_savings,
        "savings_shared_with_hospital": shared,
        "lost_margin": lost,
        "system_savings": system_savings,
        "hospital_net": avoided_penalty + shared - lost - cost,
        "combined_net": system_savings - cost,
    })
    rows = pd.DataFrame({
        "facility_id": m.facility_id[h], "condition_code": m.condition_code, "targeted": tgt,
        "err": np.where(m.has_err, m.err, np.nan), "baseline_err": np.where(m.has_err, base_err, np.nan),
        "new_err": np.where(m.has_err, new_err, np.nan),
        "threshold": m.threshold, "pass_through": lam, "enrollees": enrollees, "readmissions_avoided": avoided,
    })
    tot = hosp.drop(columns=["facility_id", "program_runs"]).sum()
    totals = {k: float(v) for k, v in tot.items()}
    totals["n_hospitals_running"] = int(runs.sum())
    benefit = totals["avoided_penalty"] + totals["savings_shared_with_hospital"] - totals["lost_margin"]
    totals["hospital_benefit"] = benefit
    totals["benefit_cost_ratio"] = benefit / totals["program_cost"] if totals["program_cost"] > 0 else np.nan
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
             discount_rate: float = 0.07) -> pd.DataFrame:
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
        shared = steady["savings_shared_with_hospital"] * eff
        lost = steady["lost_margin"] * eff
        system = steady["system_savings"] * eff
        hospital_net = pen + shared - lost - cost
        rows.append({
            "fiscal_year": fy, "cms_window": f"{w0:%b %Y}–{w1:%b %Y}",
            "program_share_of_cms_window": in_window, "program_cost": cost,
            "avoided_penalty": pen, "savings_shared_with_hospital": shared, "lost_margin": lost,
            "system_savings": system, "readmissions_avoided": steady["readmissions_avoided"] * eff,
            "hospital_net": hospital_net, "combined_net": system - cost,
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
    "persistence": "How much of today's excess persists (regression to the mean)",
    "ma_share": "Medicare Advantage share of patients",
    "variable_cost_share": "Share of hospital cost that is variable",
    "cost_per_readmission": "Cost of a readmission",
    "hospital_share_of_savings": "Share of payer savings returned to the hospital",
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
        if name in ("persistence", "variable_cost_share"):
            hi_v = min(hi_v, 1.0)
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
