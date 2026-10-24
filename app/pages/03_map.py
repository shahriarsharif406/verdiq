import pydeck as pdk
import plotly.graph_objects as go
import streamlit as st
from shapely import wkt

import data
import theme
from i18n import t
from engine import ndvi_sim
from engine.plausibility import yield_table

res = data.result()
theme.page_title(t("map_title"), t("map_sub"))

proj = res.data["issuances"].drop_duplicates("project_id").set_index("project_id")
sc = res.scores.set_index("project_id")
div = res.divergence.set_index("project_id")


def rgb(h, a=140):
    h = h.lstrip("#")
    return [int(h[i:i + 2], 16) for i in (0, 2, 4)] + [a]


rows = []
for pid, r in proj.iterrows():
    poly = wkt.loads(r.polygon_wkt)
    s = sc.loc[pid]
    tier = s.tier
    rows.append(dict(pid=pid, name=r.project_name, country=r.country, score=float(s.score), tier=tier,
                     coords=[list(c) for c in poly.exterior.coords], lon=poly.centroid.x, lat=poly.centroid.y,
                     color=rgb(theme.TIER_COLOR[tier]), line=rgb(theme.TIER_COLOR[tier], 255), area=float(r.area_ha),
                     flags=int(s.n_flags), method=r.methodology))
view = pdk.ViewState(latitude=5, longitude=45, zoom=1.9, pitch=0)
focus = st.selectbox("Zoom to", ["World"] + [f"{r['pid']} · {r['name']}" for r in rows])
if focus != "World":
    row = next(r for r in rows if r["pid"] == focus.split(" · ")[0])
    view = pdk.ViewState(latitude=row["lat"], longitude=row["lon"], zoom=8.5 if row["area"] < 20000 else 7, pitch=35)

layers = [
    pdk.Layer("PolygonLayer", rows, get_polygon="coords", get_fill_color="color", get_line_color="line", line_width_min_pixels=2,
              pickable=True, stroked=True, filled=True),
    # a pulse-sized halo so tiny polygons are visible at world zoom
    pdk.Layer("ScatterplotLayer", rows, get_position=["lon", "lat"], get_fill_color="color", get_radius=90000, radius_min_pixels=7,
              radius_max_pixels=22, pickable=True, opacity=0.55),
    pdk.Layer("TextLayer", rows, get_position=["lon", "lat"], get_text="pid", get_size=13, get_color=[231, 245, 238, 255],
              get_pixel_offset=[0, -22]),
]
tooltip = {"html": "<b>{pid} · {name}</b><br/>{country} · {method}<br/>Trust {score} · {tier}<br/>{area} ha · {flags} flags",
           "style": {"backgroundColor": "#0C2019", "color": "#E7F5EE", "border": "1px solid #10B981"}}
st.pydeck_chart(pdk.Deck(layers=layers, initial_view_state=view, tooltip=tooltip,
                         map_style="https://basemaps.cartocdn.com/gl/dark-matter-gl-style/style.json"), height=470)
st.markdown(f"{theme.badge('VERIFIED', 'trust ≥ 85')} {theme.badge('RISKY', '55 – 85')} {theme.badge('BLOCKED', '< 55')}", unsafe_allow_html=True)

st.markdown("### Projects & simulated forest health")
st.caption("⚠ Vegetation series are SIMULATED (deterministic synthetic NDVI-style signal), not satellite data. "
           "A project is flagged when its claimed sequestration grows while the simulated vegetation signal declines.")
yt = yield_table(res.data["issuances"])
cols = st.columns(3)
for i, (pid, r) in enumerate(proj.iterrows()):
    s, d = sc.loc[pid], div.loc[pid]
    ser = ndvi_sim.series(pid)
    fig = go.Figure(go.Scatter(x=ser.month, y=ser.ndvi, mode="lines", line=dict(color=theme.C["coral"] if d.divergence else theme.C["emerald"], width=2),
                               fill="tozeroy", fillcolor="rgba(16,185,129,.10)" if not d.divergence else "rgba(251,113,133,.12)"))
    fig.update_layout(height=90, margin=dict(l=0, r=0, t=0, b=0), xaxis=dict(visible=False), yaxis=dict(visible=False, range=[0, 1]))
    with cols[i % 3]:
        y = yt[yt.project_id == pid]
        theme.card(f"<div style='display:flex;justify-content:space-between'><b class='vq-h'>{pid}</b>{theme.badge(s.tier)}</div>"
                   f"<div style='font-weight:600;margin:2px 0'>{r.project_name}</div>"
                   f"<div class='vq-sub'>{r.country} · {r.area_ha:,.0f} ha · trust <b style='color:{theme.TIER_COLOR[s.tier]}'>{s.score:.0f}</b></div>"
                   f"<div class='vq-sub'>Claimed: {', '.join(f'{int(v):,}' for v in y.issued_tco2)} tCO₂ (2021-23)</div>",
                   cls="coral" if d.divergence else "")
        st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False}, key=f"nd{pid}")
        if d.divergence:
            st.markdown(f"<div class='vq-sub' style='color:{theme.C['coral']};margin-top:-14px'>▼ SIMULATED NDVI falls {abs(d.ndvi_slope_per_yr):.3f}/yr while claims grow {d.claim_growth_per_yr:.0%}/yr</div>", unsafe_allow_html=True)
        elif d.applicable:
            st.markdown("<div class='vq-sub' style='margin-top:-14px'>simulated NDVI stable · claims consistent</div>", unsafe_allow_html=True)
        else:
            st.markdown("<div class='vq-sub' style='margin-top:-14px'>cookstove project: vegetation signal not applicable</div>", unsafe_allow_html=True)
theme.footer()
