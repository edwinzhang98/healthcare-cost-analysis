import numpy as np
import pandas as pd
import streamlit as st

from dashboard.common import (md, esc, CONDITION_LABELS, chart, charts, how_to_read, hospital_conditions, hospital_label, hospital_names,
                              hospital_options, kpis, money, page, pct, short_name, show_data, table)
from src import benchmarking, client

page("Hospital Benchmarking",
     "How does one hospital compare with similar hospitals (same ownership type and Medicare volume), condition by "
     "condition?")

dim = table("dim_hospital")
hc = hospital_conditions()
ph = table("mart_penalty_hospital")

f1, f2 = st.columns([3, 2])
opts = hospital_options()
target = client.target_hospital_id()
fid = f1.selectbox("Hospital", opts, index=opts.index(target), format_func=hospital_label,
                   help="Client-group hospitals are listed first; type to search any US hospital with a score.")
with f2:
    md("**Peers must have the same…**")
    k1, k2 = st.columns(2)
    keys = []
    if k1.checkbox("Ownership", value=True):
        keys.append("ownership_group")
    if k2.checkbox("HRRP volume band", value=True):
        keys.append("size_band")
    if k1.checkbox("Census region", value=False):
        keys.append("census_region")
    if k2.checkbox("Emergency dept status", value=False):
        keys.append("has_emergency_services")

row = dim.set_index("facility_id").loc[fid]
bench = benchmarking.benchmark(hc, dim, fid, tuple(keys))
summ = benchmarking.peer_summary(dim, ph, fid, tuple(keys))
peers = benchmarking.peer_ids(dim, fid, tuple(keys))
peer_rows = hc[hc["facility_id"].isin(peers) & hc["has_err"]]
name = short_name(hospital_names().get(fid, row["facility_name"]), 40)

peer_desc = ", ".join({"ownership_group": f"{row['ownership_group'].lower()}",
                       "size_band": f"{row['size_band'].lower()}-volume",
                       "census_region": f"{row['census_region']}",
                       "has_emergency_services": "same emergency-department status"}[k] for k in keys) or "all"
st.caption(f"{name}: {row['ownership_group']} · {row['size_band']} ({row['eligible_discharges_3yr']:,.0f} eligible "
           f"discharges over 3 years) · {row['census_region']} · star rating "
           f"{int(row['star_rating']) if pd.notna(row['star_rating']) else 'n/a'} · peers = {peer_desc} "
           f"payment-eligible hospitals ({summ['n_peers']:,}).")
if row["is_maryland"]:
    st.info("Maryland hospital: scored by CMS but exempt from HRRP payment cuts (state all-payer model).")
st.caption("Peers are national. New Jersey and the Northeast readmit more than average overall, so tick "
           "'Census region' to see how a hospital compares with regional peers. The red penalty threshold is the "
           "national median; CMS actually uses the median of hospitals with a similar share of low-income "
           "(dual-eligible) patients, which is higher for safety-net hospitals, so this view can overstate how far a "
           "safety-net hospital sits above its real threshold.")
if summ["n_peers"] < 30:
    st.warning(f"Only {summ['n_peers']} peers: percentiles are unstable. Loosen the peer definition.")

worse = bench[bench["status"] == "Worse than most peers"]
kpis([
    ("Readmission index (all conditions)", f"{summ['target_index']:.3f}",
     f"peer median {summ['peer_median_index']:.3f} · higher than {summ['index_percentile']:.0f}% of peers"),
    ("Estimated penalty per year", money(summ["target_penalty"]),
     f"peer median {money(summ['peer_median_penalty'])} · {pct(summ['peer_share_penalized'])} of peers penalized"),
    ("Conditions worse than most peers", f"{len(worse)} of {int(bench['has_err'].sum())}",
     "75th percentile or worse among peers"),
    ("Readmissions/yr above peer median", f"{bench['readmissions_vs_peer_median'].clip(lower=0).sum():.1f}",
     "sum over conditions where it is worse than the median peer"),
])

sorted_b = bench[bench["has_err"]].sort_values("percentile_vs_peers", ascending=False)
if len(sorted_b):
    w = sorted_b.iloc[0]
    title = (f"{name} is worst on {w['condition_label'].lower()}: higher ERR than {w['percentile_vs_peers']:.0f}% of peers"
             if w["percentile_vs_peers"] >= 75 else f"{name} is in line with or better than most peers on every condition")
else:
    title = f"{name} has too few cases to be scored"
chart(charts.benchmark_strip(
    bench, peer_rows, name, title,
    "ERR by condition: gray = peer hospitals (box = middle half), blue diamond = this hospital, red tick = national "
    "penalty threshold; right is worse"), key="bench")

tbl = (bench.assign(condition=bench["condition_code"].map(CONDITION_LABELS),
                    _o=bench["condition_code"].map({c: i for i, c in enumerate(charts.CONDITION_ORDER)}))
       .sort_values("_o")[["condition", "status", "target_err", "peer_median", "peer_p25", "peer_p75",
                           "percentile_vs_peers", "national_threshold", "readmissions_vs_peer_median", "n_peers",
                           "discharges_annual"]])
num = lambda label, fmt: st.column_config.NumberColumn(label, format=fmt)
st.dataframe(tbl.astype({c: float for c in tbl.columns if c not in ("condition", "status")}),
             hide_index=True, width="stretch",
             column_config={"condition": "Condition", "status": "Status",
                            "target_err": num("This hospital's ERR", "%.3f"), "peer_median": num("Peer median", "%.3f"),
                            "peer_p25": num("Peer 25th pct", "%.3f"), "peer_p75": num("Peer 75th pct", "%.3f"),
                            "percentile_vs_peers": num("Higher than % of peers", "%.0f%%"),
                            "national_threshold": num("Penalty threshold", "%.3f"),
                            "readmissions_vs_peer_median": num("Readmissions/yr vs peer median", "%+.1f"),
                            "n_peers": num("Peers scored", "%d"), "discharges_annual": num("Eligible discharges/yr", "%.0f")})

md("## The client group side by side")
cl = dim[dim["facility_id"].isin(client.client_ids())]
grid = []
for f in cl["facility_id"]:
    b = benchmarking.benchmark(hc, dim, f, tuple(keys)).set_index("condition_code")["percentile_vs_peers"]
    grid.append({"Hospital": hospital_names().get(f, cl.set_index("facility_id").loc[f, "facility_name"]),
                 **{CONDITION_LABELS[c]: (np.nan if pd.isna(b.get(c, np.nan)) else float(b.get(c))) for c in charts.CONDITION_ORDER}})
grid = pd.DataFrame(grid)
grid[grid.columns[1:]] = grid[grid.columns[1:]].astype(float)


def _pct_color(v):
    """Diverging background: blue (better than peers) - neutral - red (worse), same palette as the charts."""
    if pd.isna(v):
        return ""
    lo, mid, hi = np.array([42, 120, 214]), np.array([240, 239, 236]), np.array([227, 73, 72])
    t = float(v) / 100
    rgb = mid + (lo - mid) * (0.5 - t) / 0.5 if t < 0.5 else mid + (hi - mid) * (t - 0.5) / 0.5
    rgb = (0.55 * rgb + 0.45 * mid).astype(int)          # soften so text stays readable
    return f"background-color: rgb({rgb[0]},{rgb[1]},{rgb[2]}); color: #0b0b0b"


st.dataframe(grid.style.format("{:.0f}", subset=list(grid.columns[1:]), na_rep="–")
             .map(_pct_color, subset=list(grid.columns[1:])),
             hide_index=True, width="stretch")
st.caption("Each cell = the hospital's percentile among its peers for that condition (50 = typical; higher = more "
           "readmissions than peers). Red cells are where a hospital is worse than most similar hospitals; – = too few "
           "cases to score.")

how_to_read(
    """
- **Peers** are hospitals that look like this one on the boxes you tick. Ownership and size are on by default because
  they shape patient mix and resources. Ticking more boxes makes peers more similar but fewer, so percentiles get
  noisier.
- **Chart:** each row is one condition. Gray dots are the peer hospitals' scores; the box marks the middle half of
  peers; the blue diamond is the selected hospital; the red tick is where the national penalty threshold sits. A
  diamond to the right of the box means the hospital readmits more patients than most of its peers for that condition.
- **"Higher than X% of peers"** is the hospital's percentile. Above 75 = worse than most peers; below 25 = better.
- **Readmissions/yr vs peer median** turns the gap into patients: how many fewer readmissions per year the hospital
  would have if it performed like the median peer, with its current volume.
- **Readmission index** is the volume-weighted average ERR across the hospital's scored conditions, a one-number
  summary. Small hospitals' scores sit close to 1.00 partly because CMS pulls them toward the average (page 2).
"""
)
