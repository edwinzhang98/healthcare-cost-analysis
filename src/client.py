"""The illustrative client group used to answer the "our group" questions.

CMS data has no health-system membership, so the client group is drawn with a
transparent rule: payment-eligible hospitals in one state with at least three
reported conditions, stratified by size, sampled with a fixed seed. The drawn
IDs are stored in config.yaml; ``check_client_group`` confirms the rule still
reproduces them. This is NOT an actual health system.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from src.config import load_config


def draw_client_group(dim: pd.DataFrame, state: str, plan: dict[str, int], seed: int,
                      min_conditions: int = 3) -> list[str]:
    pool_all = dim[dim["is_payment_eligible"] & (dim["state"] == state)
                   & (dim["n_conditions_with_err"] >= min_conditions)]
    rng = np.random.default_rng(seed)
    picks: list[str] = []
    for band, k in plan.items():
        pool = pool_all[pool_all["size_band"] == band].sort_values("facility_id")
        idx = rng.choice(len(pool), size=min(k, len(pool)), replace=False)
        picks += pool.iloc[sorted(idx)]["facility_id"].tolist()
    return picks


def client_config() -> dict:
    return load_config()["client_group"]


def client_ids() -> list[str]:
    return [str(x) for x in client_config()["facility_ids"]]


def target_hospital_id() -> str:
    return str(client_config()["target_hospital"])


def check_client_group(dim: pd.DataFrame) -> bool:
    cfg = client_config()
    drawn = draw_client_group(dim, cfg["state"], cfg["size_plan"], cfg["seed"], cfg["min_conditions"])
    return drawn == client_ids()
