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
focus = st.selectbox("Zoom to", ["World"] + [f"{r['pid']} · {r['name']}" for r in rows])
fig = go.Figure()
zoom = None if focus == "World" else next(r for r in rows if r["pid"] == focus.split(" · ")[0])
for r in rows:
    xs = [c[0] for c in r["coords"]]
    ys = [c[1] for c in r["coords"]]
    col = theme.TIER_COLOR[r["tier"]]
    hover = (f"<b>{r['pid']} · {r['name']}</b><br>{r['country']} · {r['method']}<br>Trust {r['score']:.0f} · {r['tier']}<br>"
             f"{r['area']:,.0f} ha · {r['flags']} flags")
    if zoom is not None:   # footprint outline visible when zoomed in
        fig.add_trace(go.Scattergeo(lon=xs, lat=ys, mode="lines", fill="toself", line=dict(color=col, width=2), fillcolor="rgba(0,0,0,0)",
                                    hoverinfo="skip", showlegend=False))
    fig.add_trace(go.Scattergeo(lon=[r["lon"]], lat=[r["lat"]], mode="markers+text", text=[r["pid"]], textposition="top center",
                                textfont=dict(color=theme.C["text"], size=12), marker=dict(size=16, color=col, opacity=.85, symbol="hexagon",
                                line=dict(width=2, color="#E7F5EE")), hovertext=[hover], hoverinfo="text", showlegend=False))
geo = dict(projection_type="natural earth", showland=True, landcolor="#0C2019", showocean=True, oceancolor="#06130F", showcountries=True,
           countrycolor="rgba(16,185,129,.28)", coastlinecolor="rgba(16,185,129,.4)", bgcolor="rgba(0,0,0,0)", showframe=False,
           lataxis_range=[-35, 40], lonaxis_range=[-90, 135])
if zoom is not None:
    span = 3 if zoom["area"] > 50000 else (0.8 if zoom["area"] > 5000 else 0.25)
    geo.update(lataxis_range=[zoom["lat"] - span, zoom["lat"] + span], lonaxis_range=[zoom["lon"] - span * 1.4, zoom["lon"] + span * 1.4],
               resolution=50, projection_type="mercator")
fig.update_geos(**geo)
fig.update_layout(height=480, margin=dict(l=0, r=0, t=0, b=0))
st.plotly_chart(theme.style_fig(fig), use_container_width=True)
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
