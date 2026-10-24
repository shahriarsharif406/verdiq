import pandas as pd
import plotly.graph_objects as go
import streamlit as st

import data
import theme
from i18n import t
from engine import chain, merkle
from engine.common import fmt_serial, parse_range

res = data.result()
theme.page_title(t("close_title"), t("close_sub"))
dates = sorted(res.closes)
anchors = data.anchor_index()

d = st.select_slider("Close date", options=dates, value=dates[-1])
close = res.closes[d]
anc = anchors.get(d)

c = st.columns(4)
c[0].metric("Leaves (ledger segments)", f"{close['n_leaves']:,}")
c[1].metric("VERIFIED segments", f"{close['n_verified']:,}")
c[2].metric("DISPUTED segments", f"{close['n_disputed']:,}")
c[3].metric("Tree depth", len(close["_levels"]) - 1)
theme.card(f"<div class='vq-k'>Merkle root of the {d} snapshot</div><div class='vq-hash' style='font-size:1rem'>0x{close['root']}</div>"
           + (f"<div style='margin-top:8px'>{theme.badge('VERIFIED', 'ANCHORED ON-CHAIN')} <span class='vq-sub'>block {anc['block']} · tx</span> <span class='vq-hash'>{anc['txHash']}</span></div>"
              if anc else f"<div style='margin-top:8px'>{theme.badge('RISKY', 'NOT ANCHORED YET')} <span class='vq-sub'>run the chain replay (Attack Mode boots it, or <code>make replay</code>)</span></div>"),
           cls="gold" if anc else "")

if anc and st.button("🔗 Read this root back from the live chain"):
    with st.spinner("eth_call closeRoot()…"):
        r = chain.onchain_root(d)
    if r is None:
        st.warning("The local node is not running (start it from Attack Mode). The anchor above comes from the recorded replay.")
    else:
        same = r.lower() == close["root"].lower()
        st.markdown(f"{theme.badge('VERIFIED' if same else 'BLOCKED', 'ROOT MATCHES' if same else 'ROOT MISMATCH')} <span class='vq-hash'>0x{r}</span>", unsafe_allow_html=True)

st.markdown("### Verify one credit without seeing the dataset")
col1, col2 = st.columns([2, 1])
with col1:
    default = str(close["records"][len(close["records"]) // 3]["start"] + 10)
    ser = st.text_input("Any serial number", value=default)
with col2:
    tamper = st.toggle("Tamper with the record (demo)", value=False)
try:
    s, _ = parse_range(ser)
    pr = merkle.proof_for_serial(close, s)
    if not pr:
        st.warning("That serial is not part of the ledger at this close (never issued).")
    else:
        rec = dict(pr["record"])
        if tamper:
            rec["owner"] = "Mallory Trading"
        ok = merkle.verify(rec, [bytes.fromhex(x) for x in pr["path"]], bytes.fromhex(pr["root"]))
        st.markdown(f"{theme.badge('VERIFIED' if ok else 'BLOCKED', 'PROOF VALID' if ok else 'PROOF INVALID: record was altered')}", unsafe_allow_html=True)
        a, b = st.columns([2, 3])
        with a:
            st.markdown("**Record (the leaf)**")
            st.json(rec)
        with b:
            st.markdown(f"**Proof path** · {len(pr['path'])} hashes lead from the leaf to the root")
            h = merkle.leaf_hash(rec)
            rows = [dict(step="leaf", hash=h.hex())]
            for i, p in enumerate(pr["path"]):
                h = merkle.node_hash(h, bytes.fromhex(p))
                rows.append(dict(step=f"+ sibling {i+1}", hash=h.hex()))
            st.dataframe(pd.DataFrame(rows), hide_index=True, use_container_width=True, height=300)
            st.markdown(f"<div class='vq-sub'>computed root</div><div class='vq-hash'>{h.hex()}</div><div class='vq-sub'>anchored root</div><div class='vq-hash'>{pr['root']}</div>", unsafe_allow_html=True)
except Exception:
    st.warning("Enter a serial number, e.g. 2507189.")

st.markdown("### Closes over time")
cl = pd.DataFrame([dict(date=k, disputed=v["n_disputed"], verified=v["n_verified"]) for k, v in res.closes.items()])
fig = go.Figure()
fig.add_bar(x=cl.date, y=cl.verified, name="VERIFIED segments", marker_color=theme.C["emerald"])
fig.add_bar(x=cl.date, y=cl.disputed, name="DISPUTED segments", marker_color=theme.C["coral"])
fig.update_layout(barmode="stack", legend=dict(orientation="h", y=1.12))
st.plotly_chart(theme.style_fig(fig, 300), use_container_width=True)
st.caption("The same proof format is verified by the Solidity function `verifyRecord` (tested in Hardhat against proofs produced by this Python engine).")
theme.footer()
