"""Run the SQL models in ``sql/`` against the DuckDB warehouse.

Each SQL file is self-contained (it declares its inputs/outputs in the header and
sets its own parameter defaults), so it can be run on its own once its input
tables exist. This runner sets the DuckDB variables from config.yaml first.

Usage:
    python -m src.sql_runner                 # run every sql/NN_*.sql in order
    python -m src.sql_runner sql/05_fct_hospital_condition.sql
"""
from __future__ import annotations

import sys
from pathlib import Path

import duckdb

from src.config import ROOT, load_config

SQL_DIR = ROOT / "sql"


def connect(read_only: bool = False) -> duckdb.DuckDBPyConnection:
    cfg = load_config()
    wh = Path(cfg["data"]["warehouse"])
    wh.parent.mkdir(parents=True, exist_ok=True)
    con = duckdb.connect(str(wh), read_only=read_only)
    if not read_only:
        _set_variables(con, cfg)
    return con


def _set_variables(con: duckdb.DuckDBPyConnection, cfg: dict) -> None:
    pen = cfg["penalty_model"]
    variables = {
        "raw_dir": cfg["data"]["raw_dir"],
        "seed_dir": cfg["data"]["seed_dir"],
        "performance_years": pen["performance_years"],
        "penalty_cap_pct": pen["penalty_cap_pct"],
        "hrrp_payment_share": pen["hrrp_payment_share"],
        "neutrality_modifier": pen["neutrality_modifier"],
    }
    for name, value in variables.items():
        literal = f"'{value}'" if isinstance(value, str) else repr(value)
        con.execute(f"SET VARIABLE {name} = {literal}")


def sql_files() -> list[Path]:
    return sorted(SQL_DIR.glob("[0-9][0-9]_*.sql"))


def run_file(con: duckdb.DuckDBPyConnection, path: Path, verbose: bool = True):
    sql = Path(path).read_text(encoding="utf-8")
    result = con.execute(sql)
    if verbose:
        try:
            df = result.fetchdf()
            print(f"-- {Path(path).name}")
            print(df.to_string(index=False, max_rows=40))
        except Exception:  # last statement returned nothing
            print(f"-- {Path(path).name}: ok")
    return result


def run_all(verbose: bool = True) -> None:
    con = connect()
    try:
        for path in sql_files():
            run_file(con, path, verbose=verbose)
    finally:
        con.close()


if __name__ == "__main__":
    targets = [Path(p) for p in sys.argv[1:]]
    if not targets:
        run_all()
    else:
        con = connect()
        try:
            for t in targets:
                run_file(con, t if t.is_absolute() else ROOT / t)
        finally:
            con.close()
