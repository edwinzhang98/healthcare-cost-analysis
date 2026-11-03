"""HRRP readmission penalties: benchmarking and business case (Streamlit demo app).

Run from the repo root:  streamlit run dashboard/app.py
Pages follow the storyline: Overview -> Data & Sanity Checks -> National Picture ->
Hospital Benchmarking -> Penalty Exposure -> Intervention Business Case -> Recommendations.
Every page reads the cached tables in data/processed (built by `python run.py`).
"""
import sys
from pathlib import Path

import streamlit as st

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

st.set_page_config(page_title="HRRP Readmission Penalties", page_icon="📉", layout="wide",
                   initial_sidebar_state="expanded")

if not (ROOT / "data" / "processed" / "dim_hospital.parquet").exists():
    st.error("Cached data not found. Build it first from the repo root:  `python run.py --skip-notebooks`")
    st.stop()

VIEWS = ROOT / "dashboard" / "views"
pages = [
    st.Page(VIEWS / "p1_overview.py", title="1 · Overview", default=True),
    st.Page(VIEWS / "p2_data_checks.py", title="2 · Data & Sanity Checks", url_path="data-checks"),
    st.Page(VIEWS / "p3_national.py", title="3 · National Picture", url_path="national"),
    st.Page(VIEWS / "p4_benchmarking.py", title="4 · Hospital Benchmarking", url_path="benchmarking"),
    st.Page(VIEWS / "p5_penalty.py", title="5 · Penalty Exposure", url_path="penalty"),
    st.Page(VIEWS / "p6_business_case.py", title="6 · Intervention Business Case", url_path="business-case"),
    st.Page(VIEWS / "p7_recommendations.py", title="7 · Recommendations", url_path="recommendations"),
]
nav = st.navigation(pages)
with st.sidebar:
    st.caption("CMS Hospital Readmissions Reduction Program · FY2026 data "
               "(performance period Jul 2021–Jun 2024). Penalty dollars are estimates; "
               "the client group is illustrative, not an actual health system.")
nav.run()
