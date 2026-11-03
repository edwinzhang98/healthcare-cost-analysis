"""Run the whole pipeline with one command.

    python run.py                    # SQL models -> cached tables -> analysis -> report, memo, notebooks
    python run.py --skip-notebooks   # faster: everything except executing the notebooks
    python run.py --validate         # also fetch CMS's FY2026/FY2027 penalty files and run the external check

Steps
  1. sql/01-09 build the DuckDB warehouse from the CMS CSVs (path in config.yaml / .env)
  2. export the tables the app needs to data/processed/*.parquet
  3. optional external check vs CMS's actual penalties (src/validate_cms.py; uses
     data/external/ if the files are there, downloads them with --validate)
  4. analysis: shrinkage fit, drivers, benchmarking, penalty sensitivity, business case,
     Monte Carlo (fixed seed) -> data/processed + reports/key_metrics.json
  5. reports/report.html (standalone) and reports/memo.html
  6. execute notebooks/*.ipynb and export them to reports/*.html
"""
from __future__ import annotations

import argparse
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))


def step(name: str, fn, timings: list) -> None:
    t0 = time.time()
    print(f"\n==> {name}", flush=True)
    fn()
    timings.append((name, time.time() - t0))
    print(f"    done in {time.time() - t0:.1f}s", flush=True)


def run_notebooks() -> None:
    out_dir = ROOT / "reports"
    for nb in sorted((ROOT / "notebooks").glob("[0-9][0-9]_*.ipynb")):
        print(f"    executing {nb.name}", flush=True)
        subprocess.run([sys.executable, "-m", "jupyter", "nbconvert", "--to", "notebook", "--execute", "--inplace",
                        "--ExecutePreprocessor.timeout=900", "--ExecutePreprocessor.kernel_name=python3", str(nb)],
                       check=True, cwd=ROOT)
        subprocess.run([sys.executable, "-m", "jupyter", "nbconvert", "--to", "html", "--output-dir", str(out_dir),
                        str(nb)], check=True, cwd=ROOT)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--skip-notebooks", action="store_true", help="do not execute the notebooks")
    ap.add_argument("--validate", action="store_true", help="download CMS penalty files and run the external check")
    args = ap.parse_args()

    from src import analysis, data, memo, report, sql_runner, validate_cms
    from src.config import load_config

    cfg = load_config()
    raw = Path(cfg["data"]["raw_dir"])
    missing = [f for f in cfg["data"]["files"].values() if not (raw / f).exists()]
    if missing:
        sys.exit(f"Raw CMS files not found in {raw}: {missing}\n"
                 "Set CMS_RAW_DIR in .env (see .env.example) or data.raw_dir in config.yaml.")

    timings: list = []
    t_all = time.time()
    step("1/6 SQL models (DuckDB)", lambda: sql_runner.run_all(verbose=False), timings)
    step("2/6 Export cached tables", data.export_tables, timings)

    def _validate():
        if args.validate:
            validate_cms.download()
        if validate_cms.run() is None:
            print("    skipped (no CMS validation files); committed summaries in reports/tables are kept")
    step("3/6 External check vs CMS actual penalties", _validate, timings)
    step("4/6 Analysis and key metrics", analysis.build, timings)
    step("5/6 HTML report and memo", lambda: (report.build(), memo.build()), timings)
    if not args.skip_notebooks:
        step("6/6 Execute and export notebooks", run_notebooks, timings)
    else:
        print("\n==> 6/6 notebooks skipped (--skip-notebooks)")

    print("\nPipeline finished in {:.1f}s".format(time.time() - t_all))
    for name, secs in timings:
        print(f"  {secs:6.1f}s  {name}")
    print("\nNext: streamlit run dashboard/app.py")


if __name__ == "__main__":
    main()
