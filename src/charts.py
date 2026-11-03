"""Plotly figure builders shared by the Streamlit app, the notebooks and the HTML
report, so every view shows the same chart.

Conventions: the title states the takeaway, the subtitle says what is measured
(with units and scope). Thin marks, one axis per chart, hairline grid, colors by
role (categorical by fixed condition order; diverging blue = better / red = worse
around a neutral midpoint; status colors only for pass/warn/fail).
"""
from __future__ import annotations

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import plotly.io as pio

# ----------------------------------------------------------------- palette
SURFACE = "#fcfcfb"
INK = "#0b0b0b"
INK_2 = "#52514e"
MUTED = "#898781"
GRID = "#e1e0d9"
BASELINE = "#c3c2b7"
NEUTRAL = "#c3c2b7"
NEUTRAL_LIGHT = "#e1e0d9"
MIDPOINT = "#f0efec"
BLUE, ORANGE, AQUA, YELLOW, MAGENTA, GREEN, VIOLET, RED = (
    "#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#008300", "#6250d6", "#e34948")
SERIES = [BLUE, ORANGE, AQUA, YELLOW, MAGENTA, GREEN, VIOLET, RED]
BLUE_RAMP = ["#cde2fb", "#b7d3f6", "#9ec5f4", "#86b6ef", "#6da7ec", "#5598e7",
             "#3987e5", "#2a78d6", "#256abf", "#1c5cab", "#184f95", "#104281", "#0d366b"]
STATUS = {"PASS": "#0ca30c", "WARN": "#fab219", "FAIL": "#d03b3b"}
STATUS_ICON = {"PASS": "✓", "WARN": "!", "FAIL": "✕"}

# Color follows the condition everywhere (fixed order, never re-ranked)
CONDITION_ORDER = ["HF", "PN", "COPD", "AMI", "CABG", "HIP_KNEE"]
CONDITION_COLORS = dict(zip(CONDITION_ORDER, SERIES[:6]))
CONDITION_LABELS = {
    "HF": "Heart failure", "PN": "Pneumonia", "COPD": "COPD", "AMI": "Heart attack (AMI)",
    "CABG": "Bypass surgery (CABG)", "HIP_KNEE": "Hip/knee replacement",
}

DIVERGING = [[0.0, BLUE], [0.5, MIDPOINT], [1.0, RED]]
SEQUENTIAL = [[i / (len(BLUE_RAMP) - 1), c] for i, c in enumerate(BLUE_RAMP)]
FONT = "system-ui, -apple-system, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif"

pio.templates["hrrp"] = go.layout.Template(layout=go.Layout(
    font=dict(family=FONT, size=13, color=INK),
    paper_bgcolor=SURFACE, plot_bgcolor=SURFACE, colorway=SERIES,
    title=dict(x=0, xanchor="left", y=0.97, yanchor="top", font=dict(size=16, color=INK)),
    margin=dict(l=12, r=24, t=88, b=48),
    xaxis=dict(gridcolor=GRID, linecolor=BASELINE, zerolinecolor=BASELINE, showline=True,
               ticks="", title=dict(font=dict(size=12, color=INK_2)), tickfont=dict(color=INK_2),
               automargin=True),
    yaxis=dict(gridcolor=GRID, linecolor=BASELINE, zerolinecolor=BASELINE, showline=False,
               ticks="", title=dict(font=dict(size=12, color=INK_2)), tickfont=dict(color=INK_2),
               automargin=True),
    legend=dict(orientation="h", yanchor="bottom", y=1.0, xanchor="left", x=0,
                font=dict(size=12, color=INK_2), bgcolor="rgba(0,0,0,0)", title=dict(text="")),
    hoverlabel=dict(bgcolor="white", bordercolor=GRID, font=dict(family=FONT, size=12, color=INK)),
    barcornerradius=4,
    bargap=0.35,
))
pio.templates.default = "hrrp"


def _wrap(text: str, width: int) -> tuple[str, int]:
    """Insert <br> so long titles wrap instead of being cut off; returns (text, n_lines)."""
    words, lines, cur = text.split(" "), [], ""
    for w in words:
        if cur and len(cur) + 1 + len(w) > width:
            lines.append(cur)
            cur = w
        else:
            cur = f"{cur} {w}".strip()
    lines.append(cur)
    return "<br>".join(lines), len(lines)


def _has_legend(fig: go.Figure) -> bool:
    named = [t for t in fig.data if t.name and t.showlegend is not False and t.type not in ("heatmap", "contour")]
    return len(named) >= 2 and fig.layout.legend.y in (None, 1.0, 1.02)


def _title(fig: go.Figure, title: str, subtitle: str | None = None, height: int | None = None) -> go.Figure:
    ttxt, tl = _wrap(title, 78)
    t = dict(text=f"<b>{ttxt}</b>")
    sl = 0
    if subtitle:
        stxt, sl = _wrap(subtitle, 118)
        t["subtitle"] = dict(text=stxt, font=dict(size=12, color=INK_2))
    fig.update_layout(title=t)
    top = 36 + 22 * tl + 17 * sl + (30 if _has_legend(fig) else 8)
    fig.update_layout(margin=dict(t=max(top, fig.layout.margin.t or 0) if fig.layout.margin.t and fig.layout.margin.t > 100 else top))
    if height:
        fig.update_layout(height=height + max(0, top - 88))
    return fig


def money(x: float, decimals: int = 1) -> str:
    """$1.2M / $350K / $900 style."""
    if x is None or (isinstance(x, float) and np.isnan(x)):
        return "n/a"
    sign = "-" if x < 0 else ""
    a = abs(x)
    if a >= 1e9:
        return f"{sign}${a / 1e9:.{decimals}f}B"
    if a >= 1e6:
        return f"{sign}${a / 1e6:.{decimals}f}M"
    if a >= 1e3:
        return f"{sign}${a / 1e3:.0f}K"
    return f"{sign}${a:,.0f}"


def pct(x: float, decimals: int = 0) -> str:
    return "n/a" if x is None or pd.isna(x) else f"{100 * x:.{decimals}f}%"


# ----------------------------------------------------------------- data & sanity
def join_funnel(steps: pd.DataFrame, title: str, subtitle: str) -> go.Figure:
    """steps: columns step, n (top to bottom)."""
    d = steps.iloc[::-1]
    fig = go.Figure(go.Bar(
        x=d["n"], y=d["step"], orientation="h", marker_color=BLUE, width=0.5,
        text=[f"{v:,.0f}" for v in d["n"]], textposition="outside", cliponaxis=False,
        hovertemplate="%{y}: %{x:,.0f} hospitals<extra></extra>"))
    fig.update_xaxes(title_text="Hospitals", showgrid=True, range=[0, d["n"].max() * 1.15])
    fig.update_yaxes(showgrid=False)
    return _title(fig, title, subtitle, height=340)


STATUS_LABELS = {
    "reported": "Published",
    "counts_suppressed": "Score published, counts hidden (imputed)",
    "too_few_cases": "Too few cases (<25), no score",
    "not_available": "Not available",
    "no_cases": "No cases",
}
STATUS_COLORS = {"reported": BLUE, "counts_suppressed": "#86b6ef", "too_few_cases": NEUTRAL,
                 "not_available": NEUTRAL_LIGHT, "no_cases": MUTED}


def reporting_status(fct: pd.DataFrame, title: str, subtitle: str) -> go.Figure:
    t = (fct.groupby(["condition_code", "reporting_status"]).size().rename("n").reset_index())
    t["share"] = t["n"] / t.groupby("condition_code")["n"].transform("sum")
    fig = go.Figure()
    order = [c for c in CONDITION_ORDER if c in t["condition_code"].unique()][::-1]
    for status, label in STATUS_LABELS.items():
        s = t[t["reporting_status"] == status].set_index("condition_code").reindex(order)
        fig.add_trace(go.Bar(
            y=[CONDITION_LABELS[c] for c in order], x=s["share"].fillna(0), name=label,
            orientation="h", marker=dict(color=STATUS_COLORS[status], line=dict(color=SURFACE, width=2)),
            customdata=s["n"].fillna(0), width=0.55,
            hovertemplate=f"%{{y}}<br>{label}: %{{x:.0%}} (%{{customdata:,.0f}} hospitals)<extra></extra>"))
    fig.update_layout(barmode="stack", barcornerradius=0, legend=dict(orientation="h", y=-0.22, yanchor="top",
                                                                      traceorder="normal"),
                      margin=dict(b=110))
    fig.update_xaxes(tickformat=".0%", title_text="Share of hospitals in the HRRP file", range=[0, 1])
    fig.update_yaxes(showgrid=False)
    return _title(fig, title, subtitle, height=460)


def err_distribution(fct: pd.DataFrame, title: str, subtitle: str) -> go.Figure:
    d = fct[fct["has_err"] & fct["is_payment_eligible"]]
    fig = go.Figure()
    for c in CONDITION_ORDER[::-1]:
        x = d.loc[d["condition_code"] == c, "err"]
        fig.add_trace(go.Box(x=x, name=CONDITION_LABELS[c], orientation="h", boxpoints=False,
                             marker_color=BLUE, line=dict(width=1.5), fillcolor="rgba(42,120,214,0.10)",
                             hoverinfo="x", showlegend=False))
    fig.add_vline(x=1.0, line=dict(color=INK_2, width=1))
    fig.add_annotation(x=1.0, y=1.0, yref="paper", text="1.00 = as expected", showarrow=False,
                       yanchor="bottom", font=dict(size=11, color=INK_2))
    fig.update_xaxes(title_text="Excess readmission ratio (ERR)")
    fig.update_yaxes(showgrid=False)
    return _title(fig, title, subtitle, height=400)


def shrinkage_curves(bins: pd.DataFrame, k: pd.DataFrame, title: str, subtitle: str) -> go.Figure:
    fig = go.Figure()
    n = np.linspace(25, 3000, 200)
    kk = k.set_index("condition_code")["k"]
    for c in CONDITION_ORDER:
        if c not in kk.index:
            continue
        col = CONDITION_COLORS[c]
        fig.add_trace(go.Scatter(x=n, y=n / (n + kk[c]), mode="lines", name=CONDITION_LABELS[c],
                                 line=dict(color=col, width=2), legendgroup=c,
                                 hovertemplate=f"{CONDITION_LABELS[c]}<br>%{{x:,.0f}} discharges: "
                                               f"%{{y:.0%}} of a real change shows in the score<extra></extra>"))
        b = bins[bins["condition_code"] == c]
        fig.add_trace(go.Scatter(x=b["median_discharges"], y=b["slope"], mode="markers", legendgroup=c,
                                 showlegend=False, marker=dict(color=col, size=8, line=dict(color=SURFACE, width=2)),
                                 hovertemplate=f"{CONDITION_LABELS[c]} (measured)<br>median %{{x:,.0f}} discharges: "
                                               f"%{{y:.0%}}<extra></extra>"))
    fig.update_xaxes(title_text="Eligible discharges over the 3-year window", range=[0, 3000])
    fig.update_yaxes(title_text="Share of a real change that reaches the CMS score", tickformat=".0%",
                     range=[0, 1])
    return _title(fig, title, subtitle, height=440)


def dq_status_table_colors(status: pd.Series) -> list[str]:
    return [STATUS[s] for s in status]


# ----------------------------------------------------------------- national picture
def condition_mix(mix: pd.DataFrame, title: str, subtitle: str) -> go.Figure:
    order = [c for c in CONDITION_ORDER if c in mix["condition_code"].values][::-1]
    m = mix.set_index("condition_code").reindex(order)
    labels = [CONDITION_LABELS[c] for c in order]
    fig = go.Figure()
    for col, name, color in [("share_discharges", "Share of eligible discharges", NEUTRAL),
                             ("share_excess_readmissions", "Share of excess readmissions", BLUE),
                             ("share_penalty", "Share of estimated penalty $", ORANGE)]:
        fig.add_trace(go.Bar(y=labels, x=m[col], name=name, orientation="h", marker_color=color,
                             hovertemplate="%{y}<br>" + name + ": %{x:.1%}<extra></extra>"))
    fig.update_layout(barmode="group", bargap=0.3, bargroupgap=0.12)
    fig.update_xaxes(tickformat=".0%", title_text="Share of national total (payment-eligible hospitals)")
    fig.update_yaxes(showgrid=False)
    return _title(fig, title, subtitle, height=460)


TILE_GRID = {
    "AK": (0, 0), "ME": (0, 11), "WI": (1, 6), "VT": (1, 10), "NH": (1, 11),
    "WA": (2, 1), "ID": (2, 2), "MT": (2, 3), "ND": (2, 4), "MN": (2, 5), "IL": (2, 6), "MI": (2, 7),
    "NY": (2, 9), "MA": (2, 10),
    "OR": (3, 1), "NV": (3, 2), "WY": (3, 3), "SD": (3, 4), "IA": (3, 5), "IN": (3, 6), "OH": (3, 7),
    "PA": (3, 8), "NJ": (3, 9), "CT": (3, 10), "RI": (3, 11),
    "CA": (4, 1), "UT": (4, 2), "CO": (4, 3), "NE": (4, 4), "MO": (4, 5), "KY": (4, 6), "WV": (4, 7),
    "VA": (4, 8), "MD": (4, 9), "DE": (4, 10),
    "AZ": (5, 2), "NM": (5, 3), "KS": (5, 4), "AR": (5, 5), "TN": (5, 6), "NC": (5, 7), "SC": (5, 8),
    "DC": (5, 9),
    "OK": (6, 4), "LA": (6, 5), "MS": (6, 6), "AL": (6, 7), "GA": (6, 8),
    "HI": (7, 0), "TX": (7, 4), "FL": (7, 9),
}


def state_tile_map(states: pd.DataFrame, value_col: str, title: str, subtitle: str,
                   colorbar_title: str, diverging_mid: float | None = None, fmt: str = ".3f",
                   hover_cols: dict[str, str] | None = None) -> go.Figure:
    """US tile-grid map (every state the same size, works offline).
    states: columns state, <value_col>, n_hospitals (+ any hover_cols)."""
    rows, cols = 8, 12
    z = np.full((rows, cols), np.nan)
    text = np.full((rows, cols), "", dtype=object)
    hover = np.full((rows, cols), "", dtype=object)
    s = states.set_index("state")
    for st, (r, c) in TILE_GRID.items():
        if st in s.index and pd.notna(s.loc[st, value_col]):
            v = s.loc[st, value_col]
            z[r, c] = v
            text[r, c] = st
            extra = ""
            for col, lab in (hover_cols or {}).items():
                val = s.loc[st, col]
                extra += f"<br>{lab}: {val}"
            hover[r, c] = f"<b>{st}</b><br>{colorbar_title}: {format(v, fmt)}{extra}"
        elif st == "MD":
            text[r, c] = "MD"
            hover[r, c] = "<b>MD</b><br>Exempt from HRRP payment cuts (state all-payer model)"
    kw = dict(colorscale=DIVERGING, zmid=diverging_mid) if diverging_mid is not None else dict(colorscale=SEQUENTIAL)
    fig = go.Figure(go.Heatmap(
        z=z, text=text, texttemplate="%{text}", textfont=dict(size=12, color=INK),
        customdata=hover, hovertemplate="%{customdata}<extra></extra>", xgap=3, ygap=3,
        colorbar=dict(title=dict(text=colorbar_title, side="right", font=dict(size=12, color=INK_2)),
                      thickness=12, len=0.75, tickfont=dict(color=INK_2), outlinewidth=0),
        hoverongaps=False, **kw))
    # Maryland drawn as a neutral tile (excluded from penalty analysis)
    if "MD" in TILE_GRID and ("MD" not in s.index or pd.isna(s.loc["MD", value_col]) if "MD" in s.index else True):
        r, c = TILE_GRID["MD"]
        fig.add_shape(type="rect", x0=c - 0.47, x1=c + 0.47, y0=r - 0.47, y1=r + 0.47,
                      line=dict(color=BASELINE, width=1), fillcolor=SURFACE, layer="below")
    fig.update_xaxes(visible=False, showgrid=False, range=[-0.6, cols - 0.4])
    fig.update_yaxes(visible=False, showgrid=False, autorange="reversed", scaleanchor="x", scaleratio=1)
    fig.update_layout(margin=dict(l=8, r=8, t=88, b=8))
    return _title(fig, title, subtitle, height=470)


def segment_dots(seg: pd.DataFrame, title: str, subtitle: str, reference: float | None = None,
                 order: list[str] | None = None, x_title: str = "Average ERR (95% interval)") -> go.Figure:
    """Mean ERR with 95% interval per segment; hollow marker = fewer than 30 results."""
    d = seg.copy()
    if order:
        d["__o"] = d["segment_value"].map({v: i for i, v in enumerate(order)})
        d = d.sort_values("__o", ascending=False)
    else:
        d = d.sort_values("mean_err")
    small = d["small_sample_flag"].fillna(False).astype(bool)
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=d["mean_err"], y=d["segment_value"], mode="markers",
        error_x=dict(type="data", symmetric=False, array=d["mean_err_ci_high"] - d["mean_err"],
                     arrayminus=d["mean_err"] - d["mean_err_ci_low"], color=BLUE, thickness=2, width=0),
        marker=dict(size=10, color=np.where(small, SURFACE, BLUE), line=dict(color=BLUE, width=2),
                    symbol="circle"),
        customdata=np.stack([d["n_hospitals"], d["n_results"], d["share_above_threshold"]], axis=-1),
        hovertemplate="<b>%{y}</b><br>Average ERR %{x:.3f}<br>%{customdata[0]:,} hospitals, "
                      "%{customdata[1]:,} results<br>Above threshold: %{customdata[2]:.0%}<extra></extra>",
        showlegend=False))
    if reference is not None:
        fig.add_vline(x=reference, line=dict(color=INK_2, width=1))
        fig.add_annotation(x=reference, y=1.0, yref="paper", text=f"National {reference:.3f}",
                           showarrow=False, yanchor="bottom", font=dict(size=11, color=INK_2))
    fig.update_xaxes(title_text=x_title)
    fig.update_yaxes(showgrid=False, type="category")
    h = max(260, 70 + 34 * len(d))
    return _title(fig, title, subtitle, height=h)


def coefficient_plot(coefs: pd.DataFrame, title: str, subtitle: str) -> go.Figure:
    d = coefs.iloc[::-1]
    sig = (d["ci_low"] > 0) | (d["ci_high"] < 0)
    fig = go.Figure(go.Scatter(
        x=d["estimate"], y=d["term"], mode="markers",
        error_x=dict(type="data", symmetric=False, array=d["ci_high"] - d["estimate"],
                     arrayminus=d["estimate"] - d["ci_low"], color=BLUE, thickness=2, width=0),
        marker=dict(size=10, color=np.where(sig, BLUE, SURFACE), line=dict(color=BLUE, width=2)),
        customdata=d["p_value"],
        hovertemplate="<b>%{y}</b><br>%{x:+.2f} ERR points<br>p = %{customdata:.3f}<extra></extra>"))
    fig.add_vline(x=0, line=dict(color=INK_2, width=1))
    fig.update_xaxes(title_text="Difference in ERR points (1 point = 1% more readmissions than expected), 95% CI")
    fig.update_yaxes(showgrid=False)
    return _title(fig, title, subtitle, height=420)


def concentration(curve: pd.DataFrame, title: str, subtitle: str, marks=(0.1, 0.2)) -> go.Figure:
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=[0, 1], y=[0, 1], mode="lines", line=dict(color=NEUTRAL, width=1),
                             hoverinfo="skip", showlegend=False))
    fig.add_trace(go.Scatter(x=curve["hospital_rank_share"], y=curve["cum_penalty_share"], mode="lines",
                             line=dict(color=BLUE, width=2), showlegend=False,
                             hovertemplate="Top %{x:.0%} of hospitals carry %{y:.0%} of penalty $<extra></extra>"))
    for q in marks:
        y = float(curve.loc[curve["hospital_rank_share"] <= q, "cum_penalty_share"].max())
        fig.add_trace(go.Scatter(x=[q], y=[y], mode="markers", showlegend=False,
                                 marker=dict(size=9, color=BLUE, line=dict(color=SURFACE, width=2)),
                                 hoverinfo="skip"))
        fig.add_annotation(x=q, y=y, text=f"Top {q:.0%} → {y:.0%}", showarrow=False, xanchor="left",
                           yanchor="top", xshift=8, font=dict(size=12, color=INK))
    fig.update_xaxes(tickformat=".0%", title_text="Hospitals, ranked from highest to lowest estimated penalty",
                     range=[0, 1])
    fig.update_yaxes(tickformat=".0%", title_text="Cumulative share of penalty dollars", range=[0, 1.02])
    return _title(fig, title, subtitle, height=420)


# ----------------------------------------------------------------- benchmarking
def benchmark_strip(bench: pd.DataFrame, peer_rows: pd.DataFrame, target_name: str,
                    title: str, subtitle: str) -> go.Figure:
    """Peer ERR distribution per condition (box + dots) with the target hospital marked."""
    order = [c for c in CONDITION_ORDER if c in bench["condition_code"].values][::-1]
    labels = {c: CONDITION_LABELS[c] for c in order}
    fig = go.Figure()
    for c in order:
        x = peer_rows.loc[peer_rows["condition_code"] == c, "err"]
        if x.empty:
            continue
        fig.add_trace(go.Box(x=x, y=[labels[c]] * len(x), orientation="h", name="Peer hospitals",
                             legendgroup="peers", showlegend=bool(c == order[-1]),
                             boxpoints="all", jitter=0.5, pointpos=0, marker=dict(color=NEUTRAL, size=5),
                             line=dict(color=MUTED, width=1), fillcolor="rgba(195,194,183,0.15)",
                             hoverinfo="x"))
    b = bench[bench["has_err"]].set_index("condition_code").reindex([c for c in order if c in
                                                                    bench[bench["has_err"]]["condition_code"].values])
    fig.add_trace(go.Scatter(
        x=b["target_err"], y=[labels[c] for c in b.index], mode="markers", name=target_name,
        marker=dict(symbol="diamond", size=14, color=BLUE, line=dict(color=SURFACE, width=2)),
        customdata=np.stack([b["percentile_vs_peers"], b["peer_median"], b["n_peers"]], axis=-1),
        hovertemplate="<b>%{y}</b><br>" + target_name + ": ERR %{x:.3f}<br>Peer median %{customdata[1]:.3f} "
                      "(%{customdata[2]:.0f} peers)<br>Higher than %{customdata[0]:.0f}% of peers<extra></extra>"))
    thr = bench.set_index("condition_code").reindex(order)["national_threshold"]
    fig.add_trace(go.Scatter(
        x=thr.values, y=[labels[c] for c in order], mode="markers", name="Penalty threshold (national median)",
        marker=dict(symbol="line-ns", size=16, line=dict(color=RED, width=2)),
        hovertemplate="Penalty threshold %{x:.3f}<extra></extra>"))
    fig.update_xaxes(title_text="Excess readmission ratio (ERR) — right is worse")
    fig.update_yaxes(showgrid=False, categoryorder="array", categoryarray=[labels[c] for c in order])
    fig.update_layout(boxmode="overlay")
    return _title(fig, title, subtitle, height=440)


# ----------------------------------------------------------------- penalty exposure
def penalty_by_hospital(cond: pd.DataFrame, names: dict[str, str], title: str, subtitle: str) -> go.Figure:
    """Stacked horizontal bars: estimated annual penalty by hospital and condition."""
    tot = cond.groupby("facility_id")["penalty"].sum().sort_values()
    ylab = [names.get(f, f) for f in tot.index]
    fig = go.Figure()
    for c in CONDITION_ORDER:
        s = cond[cond["condition_code"] == c].set_index("facility_id")["penalty"].reindex(tot.index).fillna(0)
        if s.sum() == 0:
            continue
        fig.add_trace(go.Bar(y=ylab, x=s, name=CONDITION_LABELS[c], orientation="h",
                             marker=dict(color=CONDITION_COLORS[c], line=dict(color=SURFACE, width=2)),
                             hovertemplate="%{y}<br>" + CONDITION_LABELS[c] + ": $%{x:,.0f}<extra></extra>"))
    fig.add_trace(go.Scatter(y=ylab, x=tot.values, mode="text", text=[money(v) for v in tot.values],
                             textposition="middle right", showlegend=False, hoverinfo="skip",
                             textfont=dict(color=INK, size=12)))
    fig.update_layout(barmode="stack", barcornerradius=0, legend=dict(traceorder="normal"))
    fig.update_xaxes(title_text="Estimated penalty per year (US$)", tickprefix="$", tickformat="~s",
                     range=[0, tot.max() * 1.22 if tot.max() > 0 else 1])
    fig.update_yaxes(showgrid=False)
    return _title(fig, title, subtitle, height=max(320, 90 + 46 * len(tot)))


def threshold_heatmap(rows: pd.DataFrame, names: dict[str, str], title: str, subtitle: str) -> go.Figure:
    """Hospital x condition grid of ERR minus threshold (blue = below = no penalty; red = above)."""
    d = rows.copy()
    d["gap"] = d["err"] - d["threshold"]
    order_h = (d.groupby("facility_id")["gap"].apply(lambda s: s.clip(lower=0).sum())
               .sort_values(ascending=False).index.tolist())
    conds = [c for c in CONDITION_ORDER if c in d["condition_code"].unique()]
    z = d.pivot(index="facility_id", columns="condition_code", values="gap").reindex(index=order_h, columns=conds)
    text = z.map(lambda v: "" if pd.isna(v) else f"{v:+.3f}")
    lim = float(np.nanmax(np.abs(z.values))) if np.isfinite(np.nanmax(np.abs(z.values))) else 0.1
    fig = go.Figure(go.Heatmap(
        z=z.values, x=[CONDITION_LABELS[c] for c in conds], y=[names.get(f, f) for f in z.index],
        text=text.values, texttemplate="%{text}", textfont=dict(size=12, color=INK),
        colorscale=DIVERGING, zmid=0, zmin=-lim, zmax=lim, xgap=2, ygap=2, hoverongaps=False,
        colorbar=dict(title=dict(text="ERR − threshold", side="right", font=dict(size=12, color=INK_2)),
                      thickness=12, outlinewidth=0, tickfont=dict(color=INK_2)),
        hovertemplate="%{y}<br>%{x}: %{z:+.3f} vs threshold<extra></extra>"))
    fig.update_yaxes(autorange="reversed", showgrid=False)
    fig.update_xaxes(showgrid=False, side="top", showline=False)
    fig.update_layout(margin=dict(l=12, r=24, t=120, b=24))
    return _title(fig, title, subtitle, height=max(320, 140 + 44 * len(z)))


# ----------------------------------------------------------------- business case
def waterfall(t: dict, share: float, title: str, subtitle: str) -> go.Figure:
    steps = [("Avoided HRRP penalty", t["avoided_penalty"]),
             ("Payer savings shared back", t.get("savings_shared_with_hospital", 0.0)),
             ("Lost fee-for-service margin", -t.get("lost_margin", 0.0)),
             ("Program cost", -t["program_cost"])]
    steps = [s_ for s_ in steps if abs(s_[1]) > 0.5 or s_[0] in ("Avoided HRRP penalty", "Program cost")]
    net = sum(v for _, v in steps)
    fig = go.Figure(go.Waterfall(
        orientation="v", measure=["relative"] * len(steps) + ["total"],
        x=[s[0] for s in steps] + ["Net per year (hospital)"],
        y=[s[1] for s in steps] + [net],
        text=[money(s[1]) for s in steps] + [money(net)], textposition="outside",
        increasing=dict(marker=dict(color=BLUE)), decreasing=dict(marker=dict(color=RED)),
        totals=dict(marker=dict(color=INK_2)), connector=dict(line=dict(color=BASELINE, width=1)),
        hovertemplate="%{x}: %{text}<extra></extra>", cliponaxis=False))
    fig.update_yaxes(title_text="US$ per year (steady state)", tickprefix="$", tickformat="~s")
    fig.update_xaxes(showgrid=False)
    return _title(fig, title, subtitle, height=420)


def phase_in_chart(df: pd.DataFrame, share: float, title: str, subtitle: str) -> go.Figure:
    fy = [f"FY{y}" for y in df["fiscal_year"]]
    fig = go.Figure()
    fig.add_trace(go.Bar(x=fy, y=df["avoided_penalty"], name="Avoided penalty", marker_color=BLUE,
                         hovertemplate="%{x}<br>Avoided penalty: $%{y:,.0f}<extra></extra>"))
    if df.get("savings_shared_with_hospital", pd.Series([0])).sum() > 0:
        fig.add_trace(go.Bar(x=fy, y=df["savings_shared_with_hospital"], name="Payer savings shared back",
                             marker_color=AQUA,
                             hovertemplate="%{x}<br>Payer savings shared back: $%{y:,.0f}<extra></extra>"))
    fig.add_trace(go.Bar(x=fy, y=-df["program_cost"], name="Program cost", marker_color=RED,
                         hovertemplate="%{x}<br>Program cost: $%{y:,.0f}<extra></extra>"))
    if df.get("lost_margin", pd.Series([0])).sum() > 0:
        fig.add_trace(go.Bar(x=fy, y=-df["lost_margin"], name="Lost fee-for-service margin", marker_color=ORANGE,
                             hovertemplate="%{x}<br>Lost margin: $%{y:,.0f}<extra></extra>"))
    fig.add_trace(go.Scatter(x=fy, y=df["hospital_net_cum"], name="Cumulative net (hospital)", mode="lines+markers",
                             line=dict(color=INK, width=2), marker=dict(size=8, color=INK, line=dict(color=SURFACE, width=2)),
                             hovertemplate="%{x}<br>Cumulative net: $%{y:,.0f}<extra></extra>"))
    fig.add_hline(y=0, line=dict(color=BASELINE, width=1))
    fig.update_layout(barmode="relative", barcornerradius=0, bargap=0.45)
    fig.update_yaxes(title_text="US$ per fiscal year", tickprefix="$", tickformat="~s")
    fig.update_xaxes(showgrid=False)
    return _title(fig, title, subtitle, height=440)


def tornado_chart(tor: pd.DataFrame, base: float, title: str, subtitle: str, pct: float = 0.30) -> go.Figure:
    d = tor.sort_values("swing")
    fig = go.Figure()
    fig.add_trace(go.Bar(y=d["label"], x=d["metric_at_low"] - base, base=base, orientation="h",
                         name=f"Input −{pct:.0%}", marker_color=ORANGE, width=0.5,
                         customdata=d["metric_at_low"],
                         hovertemplate="%{y}<br>Input −30%: net $%{customdata:,.0f}<extra></extra>"))
    fig.add_trace(go.Bar(y=d["label"], x=d["metric_at_high"] - base, base=base, orientation="h",
                         name=f"Input +{pct:.0%}", marker_color=BLUE, width=0.5,
                         customdata=d["metric_at_high"],
                         hovertemplate="%{y}<br>Input +30%: net $%{customdata:,.0f}<extra></extra>"))
    fig.add_vline(x=base, line=dict(color=INK_2, width=1))
    fig.add_vline(x=0, line=dict(color=RED, width=1))
    fig.add_annotation(x=base, y=1.0, yref="paper", text=f"Base {money(base)}", showarrow=False,
                       yanchor="bottom", font=dict(size=11, color=INK_2))
    fig.update_layout(barmode="overlay", barcornerradius=0)
    fig.update_xaxes(title_text="Hospital net benefit per year (US$, steady state)", tickprefix="$", tickformat="~s")
    fig.update_yaxes(showgrid=False)
    return _title(fig, title, subtitle, height=max(320, 90 + 46 * len(d)))


def breakeven_heatmap(g: pd.DataFrame, x: str, y: str, metric: str, base_xy: tuple[float, float],
                      title: str, subtitle: str, x_title: str, y_title: str) -> go.Figure:
    z = g.pivot(index=y, columns=x, values=metric)
    lim = float(np.nanmax(np.abs(z.values)))
    fig = go.Figure(go.Heatmap(
        z=z.values, x=z.columns, y=z.index, colorscale=[[0, RED], [0.5, MIDPOINT], [1, BLUE]],
        zmid=0, zmin=-lim, zmax=lim, xgap=1, ygap=1,
        colorbar=dict(title=dict(text="Net $/yr", side="right", font=dict(size=12, color=INK_2)),
                      thickness=12, outlinewidth=0, tickprefix="$", tickformat="~s", tickfont=dict(color=INK_2)),
        hovertemplate=f"{x_title}: %{{x:.0%}}<br>{y_title}: $%{{y:,.0f}}<br>Net: $%{{z:,.0f}}<extra></extra>"))
    fig.add_trace(go.Contour(z=z.values, x=z.columns, y=z.index, showscale=False,
                             contours=dict(start=0, end=0, size=1, coloring="none", showlabels=False),
                             line=dict(color=INK, width=2), hoverinfo="skip", name="Break-even"))
    fig.add_trace(go.Scatter(x=[base_xy[0]], y=[base_xy[1]], mode="markers+text", text=["Base case"],
                             textposition="top center", marker=dict(size=11, color=INK, symbol="x"),
                             textfont=dict(color=INK), showlegend=False, hoverinfo="skip"))
    fig.update_xaxes(title_text=x_title, tickformat=".0%", showgrid=False)
    fig.update_yaxes(title_text=y_title, tickprefix="$", showgrid=False)
    return _title(fig, title, subtitle, height=440)


def monte_carlo_hist(mc: pd.DataFrame, col: str, title: str, subtitle: str) -> go.Figure:
    v = mc[col]
    p_pos = float((v > 0).mean())
    fig = go.Figure(go.Histogram(x=v, nbinsx=40, marker=dict(color=BLUE, line=dict(color=SURFACE, width=1)),
                                 hovertemplate="Net $%{x:,.0f}: %{y} runs<extra></extra>"))
    fig.add_vline(x=0, line=dict(color=RED, width=1.5))
    fig.add_annotation(x=0, y=1.0, yref="paper", text=f"Break-even · {p_pos:.0%} of runs above",
                       showarrow=False, yanchor="bottom", xanchor="left", font=dict(size=11, color=INK_2))
    fig.update_xaxes(title_text="Net benefit per year (US$)", tickprefix="$", tickformat="~s")
    fig.update_yaxes(title_text="Simulation runs")
    fig.update_layout(bargap=0.02)
    return _title(fig, title, subtitle, height=380)


def validation_scatter(v: pd.DataFrame, title: str, subtitle: str) -> go.Figure:
    """Our estimated payment cut vs CMS's actual FY2026 cut, one dot per hospital."""
    d = v.copy()
    lim = float(max(d["payment_reduction_pct"].max(), d["cms_reduction_pct"].max())) * 1.05
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=[0, lim], y=[0, lim], mode="lines", line=dict(color=NEUTRAL, width=1),
                             hoverinfo="skip", showlegend=False))
    fig.add_trace(go.Scatter(
        x=d["payment_reduction_pct"], y=d["cms_reduction_pct"], mode="markers", showlegend=False,
        marker=dict(size=6, color="rgba(42,120,214,0.45)", line=dict(width=0)),
        hovertemplate="Our estimate %{x:.2%}<br>CMS actual %{y:.2%}<extra></extra>"))
    fig.update_xaxes(title_text="Our estimated payment cut (from Care Compare files only)", tickformat=".1%",
                     range=[0, lim])
    fig.update_yaxes(title_text="CMS actual FY2026 payment cut (Table 15)", tickformat=".1%", range=[0, lim])
    return _title(fig, title, subtitle, height=440)


def persistence_scatter(d: pd.DataFrame, slope: float, title: str, subtitle: str) -> go.Figure:
    """CMS actual payment cut FY2026 vs FY2027, one dot per hospital."""
    lim = float(max(d["cut_fy2026"].max(), d["cut_fy2027"].max())) * 1.03
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=[0, lim], y=[0, lim], mode="lines", line=dict(color=NEUTRAL, width=1),
                             name="Same cut both years", hoverinfo="skip"))
    fig.add_trace(go.Scatter(x=[0, lim], y=[0, slope * lim], mode="lines", line=dict(color=RED, width=2),
                             name=f"Average relationship (slope {slope:.2f})", hoverinfo="skip"))
    fig.add_trace(go.Scatter(x=d["cut_fy2026"], y=d["cut_fy2027"], mode="markers", name="Hospital",
                             marker=dict(size=5, color="rgba(42,120,214,0.35)", line=dict(width=0)),
                             hovertemplate="FY2026 cut %{x:.2%}<br>FY2027 cut %{y:.2%}<extra></extra>"))
    fig.update_xaxes(title_text="CMS actual payment cut, FY2026", tickformat=".1%", range=[0, lim])
    fig.update_yaxes(title_text="CMS actual payment cut, FY2027", tickformat=".1%", range=[0, lim])
    return _title(fig, title, subtitle, height=440)
