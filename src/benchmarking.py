"""Benchmark one hospital against comparable hospitals ("peers").

Peers = payment-eligible hospitals with the same ownership group and size band
(HRRP only covers acute care hospitals, so hospital type is already the same).
Optionally also the same census region. The target hospital is never its own peer.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

DEFAULT_PEER_KEYS = ("ownership_group", "size_band")
PEER_KEY_LABELS = {
    "ownership_group": "Same ownership",
    "size_band": "Same size",
    "census_region": "Same region",
    "has_emergency_services": "Same emergency-department status",
}


def peer_ids(dim: pd.DataFrame, facility_id: str, keys=DEFAULT_PEER_KEYS) -> pd.Index:
    target = dim.set_index("facility_id").loc[facility_id]
    mask = dim["is_payment_eligible"] & (dim["facility_id"] != facility_id) & (dim["n_conditions_with_err"] > 0)
    for k in keys:
        mask &= dim[k] == target[k]
    return pd.Index(dim.loc[mask, "facility_id"])


def benchmark(hc: pd.DataFrame, dim: pd.DataFrame, facility_id: str,
              keys=DEFAULT_PEER_KEYS, min_peers: int = 10) -> pd.DataFrame:
    """One row per condition: target ERR vs the peer distribution."""
    peers = peer_ids(dim, facility_id, keys)
    rows = []
    t_all = hc[hc["facility_id"] == facility_id].set_index("condition_code")
    for cond, t in t_all.iterrows():
        pr = hc[(hc["condition_code"] == cond) & hc["facility_id"].isin(peers) & hc["has_err"]]["err"]
        n = int(pr.size)
        row = {
            "condition_code": cond,
            "condition_label": t["condition_label"],
            "has_err": bool(t["has_err"]),
            "target_err": t["err"] if t["has_err"] else np.nan,
            "national_threshold": t["penalty_threshold_err"],
            "discharges_annual": t["discharges_est_annual"],
            "expected_rate_pct": t["expected_rate_pct"],
            "n_peers": n,
            "peer_p10": pr.quantile(0.10) if n else np.nan,
            "peer_p25": pr.quantile(0.25) if n else np.nan,
            "peer_median": pr.median() if n else np.nan,
            "peer_p75": pr.quantile(0.75) if n else np.nan,
            "peer_p90": pr.quantile(0.90) if n else np.nan,
            "small_peer_group": n < min_peers,
        }
        if t["has_err"] and n:
            row["percentile_vs_peers"] = float((pr < t["err"]).mean() * 100)
            row["gap_vs_peer_median"] = t["err"] - row["peer_median"]
            # readmissions per year the hospital would avoid by matching the peer median
            row["readmissions_vs_peer_median"] = (t["discharges_est_annual"] * t["expected_rate_pct"] / 100
                                                  * (t["err"] - row["peer_median"]))
        else:
            row["percentile_vs_peers"] = np.nan
            row["gap_vs_peer_median"] = np.nan
            row["readmissions_vs_peer_median"] = np.nan
        rows.append(row)
    out = pd.DataFrame(rows)
    out["status"] = np.select(
        [~out["has_err"], out["percentile_vs_peers"] >= 75, out["percentile_vs_peers"] <= 25],
        ["Too few cases to score", "Worse than most peers", "Better than most peers"],
        default="In line with peers")
    return out


def peer_summary(dim: pd.DataFrame, pen_hosp: pd.DataFrame, facility_id: str,
                 keys=DEFAULT_PEER_KEYS) -> dict:
    """Hospital-level comparison: readmission index and penalty vs peers."""
    peers = peer_ids(dim, facility_id, keys)
    d = dim.merge(pen_hosp[["facility_id", "penalty_est_annual", "payment_reduction_pct", "is_penalized"]],
                  on="facility_id", how="left")
    t = d[d["facility_id"] == facility_id].iloc[0]
    p = d[d["facility_id"].isin(peers)]
    return {
        "n_peers": int(len(p)),
        "target_index": float(t["readmission_index"]) if pd.notna(t["readmission_index"]) else np.nan,
        "peer_median_index": float(p["readmission_index"].median()) if len(p) else np.nan,
        "index_percentile": float((p["readmission_index"] < t["readmission_index"]).mean() * 100) if len(p) else np.nan,
        "target_penalty": float(t["penalty_est_annual"]) if pd.notna(t["penalty_est_annual"]) else 0.0,
        "peer_median_penalty": float(p["penalty_est_annual"].median()) if len(p) else np.nan,
        "peer_share_penalized": float(p["is_penalized"].mean()) if len(p) else np.nan,
    }
