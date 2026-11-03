"""How much of a real change in readmissions shows up in a hospital's CMS score.

CMS estimates each hospital's readmission performance with a hierarchical model,
which pulls (shrinks) low-volume hospitals toward the national average. So for
the same real improvement, a small hospital's ERR moves less than a large one's.

We measure this from the published data. For hospitals where CMS shows the
actual readmission count, compare
    observed deviation  = observed rate  - expected rate
    published deviation = predicted rate - expected rate
The published deviation is close to  pass_through * observed deviation, where
    pass_through(n) = n / (n + k)      n = eligible discharges in the 3-year window
and k is fitted per condition (larger k = more shrinkage).
"""
from __future__ import annotations

import numpy as np
import pandas as pd
from scipy.optimize import curve_fit


def fit_k(fct: pd.DataFrame) -> pd.DataFrame:
    """Fit k per condition on rows with published counts. Returns one row per condition."""
    rows = []
    rep = fct[fct["reporting_status"] == "reported"].copy()
    rep["dev_obs"] = rep["observed_rate_pct"] - rep["expected_rate_pct"]
    rep["dev_pub"] = rep["predicted_rate_pct"] - rep["expected_rate_pct"]
    for cond, g in rep.groupby("condition_code"):
        x = np.vstack([g["discharges"].to_numpy(float), g["dev_obs"].to_numpy(float)])
        y = g["dev_pub"].to_numpy(float)
        (k,), cov = curve_fit(lambda X, k: X[0] / (X[0] + k) * X[1], x, y, p0=[300.0])
        pred = x[0] / (x[0] + k) * x[1]
        r2 = 1 - np.sum((y - pred) ** 2) / np.sum((y - y.mean()) ** 2)
        rows.append({
            "condition_code": cond,
            "k": float(k),
            "k_se": float(np.sqrt(cov[0, 0])),
            "n_rows": int(len(g)),
            "r_squared": float(r2),
            "pass_through_at_100": 100 / (100 + k),
            "pass_through_at_500": 500 / (500 + k),
            "pass_through_at_1500": 1500 / (1500 + k),
        })
    return pd.DataFrame(rows)


def pass_through(discharges_3yr: np.ndarray | pd.Series, k: np.ndarray | pd.Series) -> np.ndarray:
    n = np.asarray(discharges_3yr, dtype=float)
    return n / (n + np.asarray(k, dtype=float))


def binned_check(fct: pd.DataFrame, n_bins: int = 5) -> pd.DataFrame:
    """Slope of published vs observed deviation within volume bins (for the chart)."""
    rep = fct[fct["reporting_status"] == "reported"].copy()
    rep["dev_obs"] = rep["observed_rate_pct"] - rep["expected_rate_pct"]
    rep["dev_pub"] = rep["predicted_rate_pct"] - rep["expected_rate_pct"]
    out = []
    for cond, g in rep.groupby("condition_code"):
        g = g.assign(bin=pd.qcut(g["discharges"], n_bins, duplicates="drop"))
        for b, gb in g.groupby("bin", observed=True):
            if len(gb) < 5:
                continue
            slope = float(np.polyfit(gb["dev_obs"], gb["dev_pub"], 1)[0])
            out.append({"condition_code": cond, "median_discharges": float(gb["discharges"].median()),
                        "slope": slope, "n_rows": int(len(gb))})
    return pd.DataFrame(out)
