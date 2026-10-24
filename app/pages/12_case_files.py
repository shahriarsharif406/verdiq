import os

import streamlit as st

import data
import theme
import views
from i18n import t
from engine import casefile

res = data.result()
theme.page_title(t("case_title"), t("case_sub"))

flags = res.flags
if not flags:
    st.info(t("empty"))
    st.stop()

txs, anchors = data.tx_index(), data.anchor_index()
llm_on = bool(os.environ.get("ANTHROPIC_API_KEY"))
st.markdown(f"{theme.badge('VERIFIED' if llm_on else 'OK', 'LLM SUMMARY ON' if llm_on else 'TEMPLATE SUMMARY')} "
            f"<span class='vq-sub'>{'ANTHROPIC_API_KEY found: the narrative is written by Claude from the verified facts.' if llm_on else 'No API key set: deterministic template text is used (the project works fully offline).'}</span>", unsafe_allow_html=True)

sev = st.multiselect("Severity", ["CRITICAL", "HIGH", "MEDIUM"], default=["CRITICAL", "HIGH", "MEDIUM"])
opts = [f for f in flags if f["severity"] in sev]
labels = [f"{f['severity']:<8} {f['rule_id']} · {f['subject_id']} · {f['tco2']:,} tCO₂" for f in opts]
if not opts:
    st.info(t("empty"))
    st.stop()
pick = st.selectbox("Flagged item", labels)
f = opts[labels.index(pick)]
views.flag_card(f, txs.get(f["subject_id"]))

md, src = casefile.build_markdown(res, f, txs, anchors)
c = st.columns(3)
c[0].download_button("⬇ Markdown", md, file_name=f"verdiq_case_{f['rule_id']}_{f['subject_id']}.md", mime="text/markdown", use_container_width=True)
try:
    pdf = casefile.to_pdf(md)
    c[1].download_button("⬇ PDF", pdf, file_name=f"verdiq_case_{f['rule_id']}_{f['subject_id']}.pdf", mime="application/pdf", use_container_width=True)
except Exception:
    c[1].caption("PDF export unavailable (install fpdf2).")
c[2].markdown(f"<div class='vq-sub' style='padding-top:8px'>summary source: <b>{src}</b></div>", unsafe_allow_html=True)
with st.container(border=True):
    st.markdown(md)
theme.footer()
