import pandas as pd
import plotly.graph_objects as go
import streamlit as st

import data
import theme
from i18n import t
from engine import greenwash

res = data.result()
theme.page_title(t("gw_title"), t("gw_sub"))
claims = res.data["corp_claims"]
companies = sorted(set(res.events.actor) | set(claims.company))
companies = [c for c in companies if c in set(claims.company) or c in set(res.data["retirements"].retiring_entity)]

c1, c2, c3 = st.columns([2, 2, 1])
default = companies.index("Meridian Airways") if "Meridian Airways" in companies else 0
company = c1.selectbox("Company", companies, index=default)
known = claims[claims.company == company]
claim_default = int(known.claimed_tco2.iloc[0]) if len(known) else 100_000
claimed = c2.number_input("Claimed offset (tCO₂)", min_value=1, value=claim_default, step=1000)
c3.markdown("<div style='height:28px'></div>", unsafe_allow_html=True)
if len(known):
    st.caption(f"Public claim on record: “{known.claim_text.iloc[0]}” ({known.channel.iloc[0]}, {known.date.iloc[0]})")

out = greenwash.check_claim(company, int(claimed), res.events, res.flags)
lvl = out["verdict_level"]
tone = dict(OK="gold", WARN="", BAD="coral")[lvl]

g1, g2 = st.columns([1, 1])
with g1:
    pct = min(out["ratio_clean"], 1.0) * 100
    fig = go.Figure(go.Indicator(mode="gauge+number", value=pct, number=dict(suffix="%", font=dict(family="Space Grotesk", color=theme.C["text"])),
                                 title=dict(text="Claim backed by clean, verified retirements"),
                                 gauge=dict(axis=dict(range=[0, 100]), bar=dict(color=theme.TIER_COLOR[lvl]), bgcolor="rgba(12,32,25,.6)",
                                            steps=[dict(range=[0, 50], color="rgba(251,113,133,.25)"), dict(range=[50, 90], color="rgba(251,191,36,.18)"),
                                                   dict(range=[90, 100], color="rgba(245,196,81,.20)")],
                                            threshold=dict(line=dict(color=theme.C["gold"], width=4), value=90))))
    st.plotly_chart(theme.style_fig(fig, 300), use_container_width=True)
with g2:
    theme.card(f"<div class='vq-k'>Verdict</div><div class='vq-v' style='color:{theme.TIER_COLOR[lvl]}'>{out['verdict']}</div>"
               f"<div style='margin-top:8px'>{out['summary']}</div>", cls=tone)
    bars = go.Figure(go.Bar(y=["Claimed", "Validly retired", "Retired · clean"], x=[out["claimed"], out["retired_valid"], out["retired_clean"]], orientation="h",
                            marker_color=[theme.C["coral"], theme.C["amber"], theme.C["emerald"]], text=[f"{v:,}" for v in (out["claimed"], out["retired_valid"], out["retired_clean"])],
                            textposition="auto"))
    bars.update_layout(yaxis=dict(autorange="reversed"), xaxis_title="tCO₂")
    st.plotly_chart(theme.style_fig(bars, 190), use_container_width=True)

if out["rejected_rows"]:
    st.markdown("#### Retirement attempts the ledger rejected")
    st.dataframe(pd.DataFrame(out["rejected_rows"]), use_container_width=True, hide_index=True)
if out["tainted"]:
    st.markdown("#### Valid retirements that touch flagged credits")
    st.dataframe(pd.DataFrame(out["tainted"]), use_container_width=True, hide_index=True)

st.markdown("### All public claims on record")
rows = []
for r in claims.itertuples():
    o = greenwash.check_claim(r.company, int(r.claimed_tco2), res.events, res.flags)
    rows.append(dict(company=r.company, claimed=int(r.claimed_tco2), validly_retired=o["retired_valid"], clean=o["retired_clean"], backed=f"{o['ratio_clean']:.0%}", verdict=o["verdict"], channel=r.channel))
st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
theme.footer()
