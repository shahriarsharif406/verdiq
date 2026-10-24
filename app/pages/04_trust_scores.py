import numpy as np
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

import data
import theme
from i18n import t
from engine import score as sc_mod
from engine.common import parse_range, project_of

res = data.result()
theme.page_title(t("trust_title"), t("trust_sub"))
S = res.scores

fig = go.Figure(go.Bar(x=S.score, y=S.project_id + " · " + S.project_name, orientation="h",
                       marker=dict(color=[theme.TIER_COLOR[x] for x in S.tier], line=dict(width=0)),
                       text=[f"{v:.0f}" for v in S.score], textposition="outside", customdata=S.tier,
                       hovertemplate="%{y}<br>score %{x}<br>%{customdata}<extra></extra>"))
fig.update_layout(xaxis=dict(range=[0, 108], title="Trust score"), yaxis=dict(autorange="reversed"))
st.plotly_chart(theme.style_fig(fig, 380), use_container_width=True)

pick = st.selectbox("Explain a project", [f"{r.project_id} · {r.project_name}" for r in S.itertuples()])
pid = pick.split(" · ")[0]
r = S[S.project_id == pid].iloc[0]
a, b = st.columns([2, 3])
with a:
    theme.card(f"<div class='vq-k'>{t('score')}</div><div class='vq-v' style='color:{theme.TIER_COLOR[r.tier]}'>{r.score:.0f}<span class='vq-sub'>/100</span></div>"
               f"{theme.badge(r.tier)}", cls="gold" if r.tier == "VERIFIED" else ("coral" if r.tier == "BLOCKED" else ""))
    comp = go.Figure(go.Bar(x=["Rule flags", "Isolation Forest", "Benford's law", "Sim. NDVI"],
                            y=[r.pen_rules, r.pen_iforest, r.pen_benford, r.pen_ndvi], marker_color=[theme.C["coral"], theme.C["amber"], theme.C["teal"], theme.C["muted"]]))
    comp.update_layout(title="Penalty points", yaxis_title="points lost")
    st.plotly_chart(theme.style_fig(comp, 260), use_container_width=True)
with b:
    st.markdown(f"#### {t('why')}")
    for w in r.why:
        st.markdown(f"- {w}")

st.markdown("### Statistical signals")
c1, c2 = st.columns(2)
an = res.anomalies
with c1:
    f2 = px.scatter(an, x="price_ratio", y="tco2", color="is_outlier", log_y=True, hover_data=["trade_id", "project_id"],
                    color_discrete_map={True: theme.C["coral"], False: theme.C["emerald"]}, title="Isolation Forest: trade outliers")
    f2.update_layout(xaxis_title="price ÷ project median", yaxis_title="tCO₂ per trade")
    st.plotly_chart(theme.style_fig(f2, 330), use_container_width=True)
with c2:
    tr = res.data["trades"].assign(project_id=lambda d: d.serial_start.map(project_of))
    vol = (tr.serial_end - tr.serial_start + 1)[tr.project_id == pid]
    lead = np.array([int(str(int(x))[0]) for x in vol if x > 0])
    obs = [(lead == d).mean() if len(lead) else 0 for d in range(1, 10)]
    f3 = go.Figure()
    f3.add_bar(x=list(range(1, 10)), y=obs, name=f"{pid} trade volumes", marker_color=theme.C["emerald"])
    f3.add_scatter(x=list(range(1, 10)), y=sc_mod.BENFORD, name="Benford expectation", line=dict(color=theme.C["gold"], width=3))
    f3.update_layout(title=f"Benford's law · first digit of trade volumes ({len(lead)} trades)", xaxis_title="leading digit", legend=dict(orientation="h", y=-0.25))
    st.plotly_chart(theme.style_fig(f3, 330), use_container_width=True)
st.caption("Benford's law is a screening hint on small samples, never a flag on its own: it only moves the score when a project deviates much more than the portfolio median.")

st.markdown("### Score any credit range")
rng = st.text_input("Serial range", value=f"{int(res.data['issuances'].serial_start.iloc[0])}-{int(res.data['issuances'].serial_start.iloc[0]) + 999}")
try:
    a0, a1 = parse_range(rng)
    out = sc_mod.score_range(a0, a1, res.flags, S)
    st.markdown(f"{theme.badge(out['verdict'])} &nbsp; score **{out['score']:.0f}/100** · project {out['project_id']}", unsafe_allow_html=True)
    for w in out["why"]:
        st.markdown(f"- {w}")
except Exception:
    st.warning("Enter two serial numbers, e.g. 2507189-2508936.")
theme.footer()
