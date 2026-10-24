"""Entity graph (sellers, buyers, projects) as a themed Plotly figure; coral glow on flagged structure."""
from __future__ import annotations

import networkx as nx
import plotly.graph_objects as go
import streamlit as st

import data
import theme
from engine.common import project_of


@st.cache_data(show_spinner=False)
def _layout():
    res = data.result()
    g = nx.Graph()
    iss = res.data["issuances"].drop_duplicates("project_id")
    for r in iss.itertuples():
        g.add_edge(r.project_id, r.developer)
    for r in res.data["trades"].itertuples():
        g.add_edge(r.seller, r.buyer)
    pos = nx.spring_layout(g, seed=11, k=0.9, iterations=200)
    return {k: (float(v[0]), float(v[1])) for k, v in pos.items()}


def build(asof: str | None = None, highlight: str | None = None):
    """Return (figure, node_info dict). Only trades dated <= asof are drawn."""
    res = data.result()
    pos = _layout()
    tr = res.data["trades"]
    if asof:
        tr = tr[tr.date <= asof]
    flag_by_trade: dict = {}
    for f in res.flags:
        if f["subject_type"] == "event" and f["rule_id"] in ("R01", "R07", "R08", "R10", "R03"):
            flag_by_trade.setdefault(f["subject_id"], []).append(f)
    edges: dict = {}
    for r in tr.itertuples():
        k = (r.seller, r.buyer)
        e = edges.setdefault(k, dict(n=0, tco2=0, usd=0.0, flags=[], ids=[]))
        n = r.serial_end - r.serial_start + 1
        e["n"] += 1; e["tco2"] += n; e["usd"] += n * r.price_usd; e["ids"].append(r.trade_id)
        e["flags"] += flag_by_trade.get(r.trade_id, [])
    iss = res.data["issuances"].drop_duplicates("project_id")
    nodes = {}
    for k, e in edges.items():
        for who, role in ((k[0], "seller"), (k[1], "buyer")):
            n = nodes.setdefault(who, dict(tco2=0, flags=[], kind="entity"))
            n["tco2"] += e["tco2"]; n["flags"] += e["flags"]
    for r in iss.itertuples():
        if r.developer in nodes or not asof:
            nodes.setdefault(r.developer, dict(tco2=0, flags=[], kind="entity"))
            nodes[r.project_id] = dict(tco2=0, flags=[f for f in res.flags if f["project_id"] == r.project_id and f["subject_type"] in ("project", "issuance")],
                                       kind="project", name=r.project_name)

    fig = go.Figure()
    # structural edges project -> developer
    xs, ys = [], []
    for r in iss.itertuples():
        if r.project_id in nodes:
            xs += [pos[r.project_id][0], pos[r.developer][0], None]; ys += [pos[r.project_id][1], pos[r.developer][1], None]
    fig.add_scatter(x=xs, y=ys, mode="lines", line=dict(color="rgba(143,181,163,.25)", width=1, dash="dot"), hoverinfo="skip", showlegend=False)
    # normal trade edges
    nx_, ny_ = [], []
    for (a, b), e in edges.items():
        if not e["flags"]:
            nx_ += [pos[a][0], pos[b][0], None]; ny_ += [pos[a][1], pos[b][1], None]
    fig.add_scatter(x=nx_, y=ny_, mode="lines", line=dict(color="rgba(45,212,191,.28)", width=1.2), hoverinfo="skip", name="trades")
    # flagged edges: glow underlay + core + midpoint hover
    fx, fy = [], []
    for (a, b), e in edges.items():
        if e["flags"]:
            fx += [pos[a][0], pos[b][0], None]; fy += [pos[a][1], pos[b][1], None]
    fig.add_scatter(x=fx, y=fy, mode="lines", line=dict(color="rgba(251,113,133,.20)", width=11), hoverinfo="skip", showlegend=False)
    fig.add_scatter(x=fx, y=fy, mode="lines", line=dict(color=theme.C["coral"], width=2.6), hoverinfo="skip", name="flagged flow (double-sold / wash / spike)")
    mx, my, mt = [], [], []
    for (a, b), e in edges.items():
        if e["flags"]:
            mx.append((pos[a][0] + pos[b][0]) / 2); my.append((pos[a][1] + pos[b][1]) / 2)
            mt.append(f"{a} → {b}<br>" + "<br>".join(sorted({f"{f['rule_id']} {f['rule_name']} ({f['subject_id']})" for f in e['flags']})))
    fig.add_scatter(x=mx, y=my, mode="markers", marker=dict(size=9, color=theme.C["coral"], symbol="diamond"), hovertext=mt, hoverinfo="text", showlegend=False)

    names = [n for n in nodes if n in pos]
    for kind, symbol in (("entity", "circle"), ("project", "hexagon")):
        sub = [n for n in names if nodes[n]["kind"] == kind]
        if not sub:
            continue
        hot = [bool(nodes[n]["flags"]) for n in sub]
        size = [(18 if kind == "project" else 11 + 22 * (nodes[n]["tco2"] / max(1, max(v["tco2"] for v in nodes.values())))) for n in sub]
        color = [theme.C["coral"] if h else (theme.C["gold"] if kind == "project" else theme.C["emerald"]) for h in hot]
        fig.add_scatter(
            x=[pos[n][0] for n in sub], y=[pos[n][1] for n in sub], mode="markers+text", text=[n if (h or kind == "project") else "" for n, h in zip(sub, hot)],
            textposition="top center", textfont=dict(size=10, color=theme.C["text"]), customdata=sub,
            marker=dict(size=size, color=color, symbol=symbol, line=dict(width=[3 if (n == highlight) else 1 for n in sub], color="#E7F5EE")),
            hovertext=[f"<b>{n}</b><br>{nodes[n]['tco2']:,} tCO₂ traded<br>{len(nodes[n]['flags'])} flags" if kind == "entity" else
                       f"<b>{n} · {nodes[n].get('name','')}</b><br>{len(nodes[n]['flags'])} project flags" for n in sub],
            hoverinfo="text", name="projects" if kind == "project" else "entities", selected=dict(marker=dict(opacity=1)), unselected=dict(marker=dict(opacity=.85)))
    fig.update_layout(xaxis=dict(visible=False), yaxis=dict(visible=False), height=560, showlegend=True,
                      legend=dict(orientation="h", y=1.04), dragmode="pan", margin=dict(l=0, r=0, t=10, b=0))
    return theme.style_fig(fig), nodes
