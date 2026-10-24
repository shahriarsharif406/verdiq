import time

import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from shapely import wkt

import data
import netgraph
import theme
import views
from i18n import t
from engine.pipeline import flag_dates

res = data.result()
theme.page_title(t("time_title"), t("time_sub"))

months = sorted(res.closes)
fdates = flag_dates(res)
FL = [dict(f, eff=fdates[f["flag_id"]]) for f in res.flags if f["severity"] in ("CRITICAL", "HIGH", "MEDIUM")]
ev = res.events
proj = res.data["issuances"].drop_duplicates("project_id")
txs = data.tx_index()


def cumulative():
    rows = []
    for m in months:
        im = data.impact(m)
        rows.append(dict(month=m, tonnes=im["tonnes_protected"], usd=im["usd_blocked"]))
    return pd.DataFrame(rows)


@st.cache_data(show_spinner=False)
def cum_cached(_n):
    return cumulative()


cum = cum_cached(len(months))


def render(d: str):
    prev = months[max(months.index(d) - 1, 0)]
    done = ev[ev.date <= d]
    live = [f for f in FL if f["eff"] <= d]
    new = [f for f in FL if prev < f["eff"] <= d] if d != months[0] else [f for f in FL if f["eff"] <= d]
    im = data.impact(d)
    c = st.columns(5)
    c[0].metric("Market date", d)
    c[1].metric("Ledger events", f"{len(done):,}")
    c[2].metric("Flags raised", len(live), f"+{len(new)} this month" if new else None)
    c[3].metric("tCO₂ protected", f"{im['tonnes_protected']:,}")
    c[4].metric("USD blocked", f"${im['usd_blocked']:,.0f}")

    l, r = st.columns([3, 2])
    with l:
        fig = go.Figure()
        fig.add_scatter(x=cum.month, y=cum.tonnes, mode="lines", line=dict(color=theme.C["emerald"], width=3, shape="hv"), fill="tozeroy",
                        fillcolor="rgba(16,185,129,.10)", name="tCO₂ protected (cumulative)")
        ev_pts = cum[cum.month <= d]
        fig.add_scatter(x=ev_pts.month.iloc[-1:], y=ev_pts.tonnes.iloc[-1:], mode="markers", marker=dict(size=14, color=theme.C["gold"], symbol="hexagon"), name="now")
        for f in live:
            if f["severity"] != "MEDIUM":
                mm = next((m for m in months if m >= f["eff"]), months[-1])
                fig.add_vline(x=mm, line=dict(color="rgba(251,113,133,.35)", width=1, dash="dot"))
        fig.update_layout(height=290, showlegend=False, title="Cumulative tonnes protected · fraud events as they occur")
        st.plotly_chart(theme.style_fig(fig), use_container_width=True, key=f"cum{d}")
        # map
        lons, lats, sizes, cols, txt = [], [], [], [], []
        vmax = ev[ev.kind == "TRADE"].groupby("project_id").tco2.sum().max()
        for p in proj.itertuples():
            g = wkt.loads(p.polygon_wkt).centroid
            vol = ev[(ev.project_id == p.project_id) & (ev.date <= d) & (ev.kind == "TRADE")].tco2.sum()
            bad = [f for f in live if f["project_id"] == p.project_id]
            lons.append(g.x); lats.append(g.y); sizes.append(10 + 28 * (vol / max(1, vmax)) ** 0.5)
            cols.append(theme.C["coral"] if bad else theme.C["emerald"])
            txt.append(f"<b>{p.project_id} · {p.project_name}</b><br>{int(vol):,} tCO₂ traded so far<br>{len(bad)} flags")
        mp = go.Figure(go.Scattergeo(lon=lons, lat=lats, mode="markers+text", text=[p for p in proj.project_id], textposition="top center",
                                     marker=dict(size=sizes, color=cols, symbol="circle", line=dict(width=1.5, color="#E7F5EE"), opacity=.9),
                                     hovertext=txt, hoverinfo="text"))
        mp.update_geos(projection_type="natural earth", showland=True, landcolor="#0C2019", showocean=True, oceancolor="#06130F", showcountries=True,
                       countrycolor="rgba(16,185,129,.25)", coastlinecolor="rgba(16,185,129,.35)", bgcolor="rgba(0,0,0,0)", lataxis_range=[-35, 45], lonaxis_range=[-95, 135])
        mp.update_layout(height=300, margin=dict(l=0, r=0, t=0, b=0))
        st.plotly_chart(theme.style_fig(mp), use_container_width=True, key=f"map{d}")
    with r:
        st.markdown("#### Fraud events appearing")
        if not new:
            st.markdown("<div class='vq-sub'>A quiet month: nothing flagged.</div>", unsafe_allow_html=True)
        for f in sorted(new, key=lambda x: -{"CRITICAL": 3, "HIGH": 2, "MEDIUM": 1}[x["severity"]])[:5]:
            views.flag_card(f, txs.get(f["subject_id"]))
        g, _ = netgraph.build(asof=d)
        g.update_layout(height=300, showlegend=False)
        st.plotly_chart(g, use_container_width=True, key=f"net{d}")


_cnt = {}
for f in FL:
    mm = next((m for m in months if m >= f["eff"]), months[-1])
    _cnt[mm] = _cnt.get(mm, 0) + 1
DEFAULT = max(_cnt, key=lambda m: (_cnt[m], m)) if _cnt else months[-1]
top = st.columns([6, 1])
idx = top[0].select_slider("Month-end close", options=months, value=DEFAULT, key="tm_month")
play = top[1].button("▶ Play", use_container_width=True)
body = st.empty()
if play:
    start = months.index(idx)
    for m in months[start:]:
        with body.container():
            render(m)
        time.sleep(0.45)
else:
    with body.container():
        render(idx)
theme.footer()
