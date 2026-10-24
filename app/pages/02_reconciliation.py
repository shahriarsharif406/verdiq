import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

import data
import theme
import views
from i18n import t
from engine.common import fmt_serial

res = data.result()
theme.page_title(t("recon_title"), t("recon_sub"))

ev = res.events
c = st.columns(5)
c[0].metric("Issued (tCO₂)", f"{int(res.data['issuances'].issued_tco2.sum()):,}")
c[1].metric("Trades", f"{(ev.kind=='TRADE').sum():,}")
c[2].metric("Retirements", f"{(ev.kind=='RETIREMENT').sum():,}")
c[3].metric("Matched events", f"{(ev.status=='MATCHED').sum():,}")
c[4].metric("Rejected events", f"{(ev.status!='MATCHED').sum():,}")

tab1, tab2, tab3 = st.tabs(["Balance per issuance", "Ledger events", "Integrity flags"])

with tab1:
    s = res.issuance_summary.copy()
    fig = go.Figure()
    for col, color, name in [("retired", theme.C["emerald"], "Retired"), ("in_market", theme.C["teal"], "Held by buyers / brokers"),
                             ("unsold", "#2b4a3f", "Unsold at developer")]:
        fig.add_bar(x=s.issuance_id, y=s[col], name=name, marker_color=color)
    fig.add_scatter(x=s.issuance_id, y=s.rejected_tco2, name="Rejected attempts", mode="markers",
                    marker=dict(color=theme.C["coral"], size=11, symbol="hexagon", line=dict(width=1, color="white")))
    fig.update_layout(barmode="stack", legend=dict(orientation="h", y=1.12), xaxis_tickangle=-60, yaxis_title="tCO₂")
    st.plotly_chart(theme.style_fig(fig, 420), use_container_width=True)
    st.caption("Bank-style balance: issued = unsold + in market + retired. Every issuance balances to the tonne; red hexagons are tonnes the ledger refused.")
    st.dataframe(s.rename(columns={"in_market": "in_market", "rejected_tco2": "rejected_tco2"}), use_container_width=True, hide_index=True)

with tab2:
    f1, f2 = st.columns(2)
    stat = f1.multiselect("Status", sorted(ev.status.unique()), default=[x for x in sorted(ev.status.unique()) if x != "MATCHED"])
    kind = f2.multiselect("Kind", ["TRADE", "RETIREMENT"], default=["TRADE", "RETIREMENT"])
    v = ev[ev.status.isin(stat) & ev.kind.isin(kind)]
    if v.empty:
        st.info(t("empty"))
    else:
        show = v[["event_id", "kind", "date", "actor", "counterparty", "serial_start", "serial_end", "tco2", "price_usd", "status", "reason"]].copy()
        show["serial_start"] = show.serial_start.map(fmt_serial)
        show["serial_end"] = show.serial_end.map(fmt_serial)
        st.dataframe(show, use_container_width=True, hide_index=True, height=420)
    sc = ev.status.value_counts().reset_index()
    sc.columns = ["status", "events"]
    fig = px.bar(sc, x="status", y="events", color="status", log_y=True,
                 color_discrete_map={"MATCHED": theme.C["emerald"]}, color_discrete_sequence=[theme.C["coral"]])
    st.plotly_chart(theme.style_fig(fig, 300), use_container_width=True)

with tab3:
    sev = st.multiselect("Severity", ["CRITICAL", "HIGH", "MEDIUM"], default=["CRITICAL", "HIGH", "MEDIUM"])
    txs = data.tx_index()
    n = 0
    for f in res.flags:
        if f["severity"] in sev:
            views.flag_card(f, txs.get(f["subject_id"]))
            n += 1
            if f["evidence"]:
                with st.expander(f"Evidence rows · {f['subject_id']}"):
                    st.dataframe(pd.DataFrame(f["evidence"]), use_container_width=True, hide_index=True)
    if not n:
        st.info(t("empty"))
theme.footer()
