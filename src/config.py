"""Project configuration: paths and model parameters.

Everything configurable lives in ``config.yaml`` at the repo root. The raw data
location can be overridden without editing that file by setting ``CMS_RAW_DIR``
in the environment or in a ``.env`` file (see ``.env.example``).
"""
from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path

import yaml
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATH = ROOT / "config.yaml"


@lru_cache(maxsize=1)
def load_config() -> dict:
    """Read config.yaml, apply .env / environment overrides, resolve paths."""
    load_dotenv(ROOT / ".env", override=False)
    with open(CONFIG_PATH, encoding="utf-8") as fh:
        cfg = yaml.safe_load(fh)

    data = cfg["data"]
    raw_dir = Path(os.environ.get("CMS_RAW_DIR") or data["raw_dir"]).expanduser()
    data["raw_dir"] = str(raw_dir if raw_dir.is_absolute() else (ROOT / raw_dir).resolve())   # relative = from repo root
    for key in ("processed_dir", "warehouse"):
        data[key] = str((ROOT / data[key]).resolve())
    data["seed_dir"] = str((ROOT / data["seed_dir"]).resolve())

    out = cfg["outputs"]
    for key in list(out):
        out[key] = str((ROOT / out[key]).resolve())
    return cfg


def processed_path(name: str) -> Path:
    """Path of a cached table in data/processed (parquet)."""
    return Path(load_config()["data"]["processed_dir"]) / f"{name}.parquet"


def raw_file(key: str) -> Path:
    cfg = load_config()["data"]
    return Path(cfg["raw_dir"]) / cfg["files"][key]
