import plotly.express as px
import streamlit as st

import data
import theme
import views
from i18n import t

res = data.result()
ev = data.evaluation()
im = data.impact()
rep = data.chain_replay()

theme.hero(t("hero_title"), t("hero_sub"), tag=t("tagline"))

theme.counters([
    dict(label=t("m_tonnes"), value=im["tonnes_protected"], tone="gold", sub=t("s_tonnes")),
    dict(label=t("m_usd"), value=im["usd_blocked"], prefix="$", tone="coral", sub=t("s_usd")),
    dict(label=t("m_cars"), value=im["cars_per_year"], tone="teal", sub=t("s_cars")),
    dict(label=t("m_trees"), value=im["trees"], tone="em", sub=t("s_trees")),
], height=150)

n_events = len(res.events)
blocked_chain = rep["reverted"] if rep else int((res.events.status != "MATCHED").sum())
c = st.columns(4)
c[0].metric(t("m_detect"), f"{ev['types_detected']}/{ev['types_total']}", f"precision {ev['precision']:.0%} · recall {ev['recall']:.0%}", delta_color="off", delta_arrow="off")
c[1].metric(t("m_events"), f"{n_events:,}", f"{len(res.data['issuances'])} issuances · {len(res.closes)} daily closes", delta_color="off", delta_arrow="off")
c[2].metric(t("m_flags"), len(res.flags), f"{sum(f['severity']=='CRITICAL' for f in res.flags)} critical", delta_color="off", delta_arrow="off")
c[3].metric(t("m_blocked"), blocked_chain, "on a local Hardhat chain" if rep else "chain replay not run yet (make replay)", delta_color="off", delta_arrow="off")

st.markdown(f"### {t('how_title')}")
h = st.columns(3)
for col, (k, d, ico) in zip(h, [("how1", "how1d", "⚖️"), ("how2", "how2d", "🛡️"), ("how3", "how3d", "🎫")]):
    with col:
        theme.card(f"<div style='font-size:1.6rem'>{ico}</div><div class='vq-h' style='font-size:1.15rem;font-weight:600'>{t(k)}</div>"
                   f"<div class='vq-sub' style='margin-top:4px'>{t(d)}</div>")

left, right = st.columns([3, 2])
with left:
    st.markdown(f"### {t('recent')}")
    txs = data.tx_index()
    for f in res.flags[:0]:
        pass
    shown = res.flags_df.head(6)
    by_id = {(f["subject_id"], f["rule_id"]): f for f in res.flags}
    for r in shown.itertuples():
        views.flag_card(by_id[(r.subject_id, r.rule_id)], txs.get(r.subject_id))
with right:
    st.markdown(f"### {t('by_rule')}")
    df = res.flags_df.groupby(["rule_id", "rule_name", "severity"]).size().reset_index(name="n")
    df["label"] = df.rule_id + " " + df.rule_name.str.replace("_", " ").str.title()
    fig = px.bar(df.sort_values("n"), x="n", y="label", orientation="h", color="severity",
                 color_discrete_map=theme.SEV_COLOR, labels=dict(n="flags", label=""))
    fig.update_layout(showlegend=True, legend=dict(orientation="h", y=-0.15))
    st.plotly_chart(theme.style_fig(fig, 380), use_container_width=True)

theme.footer()
