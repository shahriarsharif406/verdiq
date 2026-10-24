import streamlit as st

import data
import netgraph
import theme
import views
from i18n import t

res = data.result()
theme.page_title(t("net_title"), t("net_sub"))

fig, nodes = netgraph.build()
ev = st.plotly_chart(fig, use_container_width=True, on_select="rerun", selection_mode="points", key="netsel")
sel = None
try:
    pts = ev.selection.points if ev and ev.selection else []
    if pts:
        sel = pts[0].get("customdata")
        sel = sel[0] if isinstance(sel, (list, tuple)) else sel
except Exception:
    sel = None

c1, c2 = st.columns([2, 3])
hot = sorted([n for n, v in nodes.items() if v["flags"] and v["kind"] == "entity"], key=lambda n: -len(nodes[n]["flags"]))
with c1:
    st.markdown("#### Node inspector")
    PH = "(click a node, or choose here)"
    opts = [PH] + hot + sorted(n for n, v in nodes.items() if v["kind"] == "project")
    choice = st.selectbox("Entity or project", opts, index=opts.index(sel) if sel in opts else 0)
    st.caption("Coral = involved in a flagged flow. Hexagons are projects, circles are trading entities, size = tCO₂ traded.")
with c2:
    name = choice if not choice.startswith("(") else sel
    if name and name in nodes:
        n = nodes[name]
        nf = len(n["flags"])
        b = theme.badge("BLOCKED", f"{nf} FLAGS") if nf else theme.badge("VERIFIED", "NO FLAGS")
        st.markdown(f"#### {name} {b}", unsafe_allow_html=True)
        seen = set()
        txs = data.tx_index()
        for f in n["flags"]:
            if (f["flag_id"]) in seen:
                continue
            seen.add(f["flag_id"])
            views.flag_card(f, txs.get(f["subject_id"]))
        if not n["flags"]:
            st.success("No integrity flags touch this node.")
    else:
        st.markdown("#### Loops detected")
        for f in [f for f in res.flags if f["rule_id"] == "R07"][:1]:
            st.markdown(f"<div class='vq-flag'>{f['reason']}</div>", unsafe_allow_html=True)
theme.footer()
