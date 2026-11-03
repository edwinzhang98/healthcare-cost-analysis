"""Build and read the cached analysis tables (data/processed/*.parquet).

The SQL models in sql/ build a DuckDB warehouse; ``export_tables`` copies the
tables the notebooks and dashboard need into parquet so pages only ever read a
cache and never recompute the pipeline.
"""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path

import pandas as pd

from src.config import load_config, processed_path
from src.sql_runner import connect

EXPORT_TABLES = [
    "dim_hospital",
    "fct_hospital_condition",
    "mart_penalty_condition",
    "mart_penalty_hospital",
    "mart_segment_summary",
    "dq_check_results",
    "seed_condition_params",
]

CONDITION_ORDER = ["HF", "PN", "COPD", "AMI", "CABG", "HIP_KNEE"]


def export_tables() -> None:
    out_dir = Path(load_config()["data"]["processed_dir"])
    out_dir.mkdir(parents=True, exist_ok=True)
    con = connect(read_only=True)
    try:
        for name in EXPORT_TABLES:
            con.execute(f"COPY {name} TO '{out_dir / (name + '.parquet')}' (FORMAT parquet)")
    finally:
        con.close()


def save_table(df: pd.DataFrame, name: str) -> Path:
    path = processed_path(name)
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(path, index=False)
    return path


@lru_cache(maxsize=None)
def _read(name: str) -> pd.DataFrame:
    return pd.read_parquet(processed_path(name))


def table(name: str) -> pd.DataFrame:
    """Read a cached table (returns a copy so callers can modify it)."""
    return _read(name).copy()


def condition_params() -> pd.DataFrame:
    return table("seed_condition_params").set_index("condition_code")


def condition_labels() -> dict[str, str]:
    return condition_params()["condition_label"].to_dict()


def hospital_conditions() -> pd.DataFrame:
    """Hospital x condition rows joined to hospital attributes (analysis base)."""
    fct = table("fct_hospital_condition")
    dim = table("dim_hospital")
    cols = ["facility_id", "facility_name", "city", "census_region", "ownership_group",
            "size_band", "star_rating", "star_rating_label", "mspb_ratio", "mspb_band",
            "has_emergency_services", "emergency_services_label", "eligible_discharges_3yr",
            "is_maryland", "in_hospital_info"]
    return fct.merge(dim[cols], on="facility_id", how="left")
