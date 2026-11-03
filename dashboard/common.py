"""Shared helpers for the Streamlit pages: layout, cached data, formatting."""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pandas as pd
import streamlit as st

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src import analysis, charts, client, cost_model as cm, data  # noqa: E402
from src.config import load_config  # noqa: E402

money, pct = charts.money, charts.pct
CONDITION_LABELS = charts.CONDITION_LABELS
CONDITION_ORDER = charts.CONDITION_ORDER
PLOTLY_CONFIG = {"displaylogo": False, "modeBarButtonsToRemove": ["lasso2d", "select2d", "autoScale2d"]}

CSS = """
<style>
.block-container {padding-top: 2.2rem; max-width: 1180px;}
h1 {font-size: 1.65rem !important; font-weight: 650 !important; margin-bottom: 0.1rem !important;}
h2 {font-size: 1.2rem !important; font-weight: 620 !important; margin-top: 1.4rem !important;}
h3 {font-size: 1.02rem !important; font-weight: 600 !important;}
.question {font-size: 1.02rem; color: #52514e; margin: 0 0 1.1rem 0; padding: 0.55rem 0.8rem;
           border-left: 3px solid #2a78d6; background: #f3f2ee; border-radius: 0 4px 4px 0;}
.note {font-size: 0.86rem; color: #52514e;}
.kpi-label {font-size: 0.82rem; color: #52514e; margin-bottom: 0.1rem;}
.kpi-value {font-size: 1.6rem; font-weight: 620; color: #0b0b0b; line-height: 1.2;}
.kpi-sub {font-size: 0.8rem; color: #898781;}
.kpi {padding: 0.6rem 0.8rem; border: 1px solid rgba(11,11,11,0.10); border-radius: 6px; background: #fcfcfb; height: 100%;}
.badge {display:inline-block; padding: 0 6px; border-radius: 3px; font-size: 0.78rem; font-weight: 600;}
[data-testid="stMetricValue"] {font-size: 1.5rem;}
[data-testid="stExpander"] summary p {font-weight: 600;}
</style>
"""


def esc(text: str) -> str:
    """Escape $ so Streamlit doesn't render "$1M ... $2M" as LaTeX math."""
    return str(text).replace("$", "&#36;")


def md(text: str, **_) -> None:
    st.markdown(esc(text), unsafe_allow_html=True)


def page(title: str, question: str) -> None:
    st.markdown(CSS, unsafe_allow_html=True)
    st.title(title)
    st.markdown(esc(f'<div class="question">{question}</div>'), unsafe_allow_html=True)


def how_to_read(markdown_text: str) -> None:
    st.divider()
    with st.expander("How to read this page", expanded=False):
        st.markdown(esc(markdown_text), unsafe_allow_html=True)


def kpis(items: list[tuple[str, str, str]]) -> None:
    """items: (label, value, sub-text)."""
    cols = st.columns(len(items))
    for col, (label, value, sub) in zip(cols, items):
        col.markdown(esc(f'<div class="kpi"><div class="kpi-label">{label}</div><div class="kpi-value">{value}</div>'
                         f'<div class="kpi-sub">{sub}</div></div>'), unsafe_allow_html=True)


def chart(fig, key: str | None = None) -> None:
    st.plotly_chart(fig, width="stretch", config=PLOTLY_CONFIG, key=key)


def show_data(df: pd.DataFrame, label: str = "Show the numbers behind this chart", **kwargs) -> None:
    with st.expander(label, expanded=False):
        st.dataframe(df, width="stretch", hide_index=True, **kwargs)


# ----------------------------------------------------------------- cached data
@st.cache_data(show_spinner=False)
def table(name: str) -> pd.DataFrame:
    return data.table(name)


@st.cache_data(show_spinner=False)
def hospital_conditions() -> pd.DataFrame:
    return data.hospital_conditions()


@st.cache_data(show_spinner=False)
def metrics() -> dict:
    return json.loads((ROOT / "reports" / "key_metrics.json").read_text())


@st.cache_data(show_spinner=False)
def config() -> dict:
    return load_config()


@st.cache_data(show_spinner=False)
def payments() -> pd.Series:
    return analysis.payments()


@st.cache_data(show_spinner=False)
def shrinkage_k() -> pd.Series:
    return table("shrinkage_k").set_index("condition_code")["k"]


@st.cache_resource(show_spinner=False)
def all_model_inputs() -> cm.ModelInputs:
    hc = hospital_conditions()
    return cm.ModelInputs.build(hc[hc["is_payment_eligible"]], payments(), shrinkage_k())


@st.cache_data(show_spinner=False)
def hospital_names() -> dict[str, str]:
    names = table("dim_hospital").set_index("facility_id")["facility_name"].to_dict()
    names.update(client.display_names())
    return names


def short_name(name: str, n: int = 34) -> str:
    if not name.isupper():          # already a display name
        return name if len(name) <= n else name[: n - 1] + "…"
    name = name.title().replace("Of ", "of ").replace("At ", "at ").replace("And ", "and ")
    return name if len(name) <= n else name[: n - 1] + "…"


def client_ids() -> list[str]:
    return client.client_ids()


def hospital_options(include_all: bool = True) -> list[str]:
    """Client hospitals first, then every payment-eligible hospital with at least one score."""
    dim = table("dim_hospital")
    ids = client_ids()
    rest = dim[(dim["n_conditions_with_err"] > 0) & ~dim["facility_id"].isin(ids)].sort_values("facility_name")
    return ids + (rest["facility_id"].tolist() if include_all else [])


def hospital_label(fid: str) -> str:
    dim = table("dim_hospital").set_index("facility_id")
    r = dim.loc[fid]
    tag = " · client group" if fid in client_ids() else ""
    return f"{short_name(r['facility_name'], 46)} ({r['city'].title() if isinstance(r['city'], str) else ''}, {r['state']}){tag}"


def status_badge(status: str) -> str:
    color = charts.STATUS[status]
    ink = "#0b0b0b" if status == "WARN" else "#ffffff"
    return f'<span class="badge" style="background:{color};color:{ink}">{charts.STATUS_ICON[status]} {status}</span>'


def preset_params(name: str) -> cm.ProgramParams:
    return analysis.program_params(name)
