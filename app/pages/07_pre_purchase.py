import pandas as pd
import plotly.graph_objects as go
import streamlit as st

import data
import theme
from i18n import t
from engine import score as sc_mod
from engine.common import fmt_serial, parse_range, project_of

res = data.result()
theme.page_title(t("pre_title"), t("pre_sub"))
iss = res.data["issuances"]
cat = iss.drop_duplicates("project_id").set_index("project_id").methodology


def sample_portfolio() -> str:
    segs = [s for s in res.ledger.segs if s.owner not in set(iss.developer) and not s.retired and (s.end - s.start) > 1500]
    clean = [s for s in segs if not sc_mod.score_range(s.start, s.end, res.flags, res.scores)["flags"] and s.project_id in ("P07", "P01", "P05", "P02")][:3]
    lines = [f"{s.start}-{s.start + 999}" for s in clean]
    fraud = res.events[res.events.event_id.isin(["T9001", "T9003", "T9004"])]
    lines += [f"{int(r.serial_start)}-{int(r.serial_end)}" for r in fraud.itertuples()]
    p8 = iss[iss.issuance_id == "ISS-P08-2022"].iloc[0]
    lines.append(f"{int(p8.serial_start) + 100}-{int(p8.serial_start) + 3099}")
    return "\n".join(lines)


if "pp_text" not in st.session_state:
    st.session_state["pp_text"] = sample_portfolio()
a, b = st.columns([3, 1])
with b:
    if st.button("Load sample portfolio", use_container_width=True):
        st.session_state["pp_text"] = sample_portfolio()
    if st.button("Clear", use_container_width=True):
        st.session_state["pp_text"] = ""
with a:
    text = st.text_area("Serial ranges, one per line (e.g. 2507189-2508936 or VQ-02507189 → VQ-02508936)", key="pp_text", height=190)

rows, bad_lines = [], []
for line in [l for l in text.splitlines() if l.strip()]:
    try:
        s, e = parse_range(line)
        out = sc_mod.score_range(s, e, res.flags, res.scores)
        covered, gaps = res.ledger.pieces(s, e)
        if gaps:
            out = dict(out, verdict="BLOCKED", score=0.0, why=[f"{sum(y - x + 1 for x, y in gaps):,} tCO₂ were never issued by the registry."] + out["why"])
        rows.append(dict(start=s, end=e, tco2=e - s + 1, project=project_of(s), **{k: out[k] for k in ("verdict", "score", "why")}))
    except Exception:
        bad_lines.append(line)
if bad_lines:
    st.warning(f"Could not read {len(bad_lines)} line(s): " + ", ".join(bad_lines[:3]))
if not rows:
    st.info(t("empty") + " Paste at least one serial range above.")
    st.stop()

df = pd.DataFrame(rows)
health = float((df.score * df.tco2).sum() / df.tco2.sum())
tier = "VERIFIED" if health >= 85 and (df.verdict == "SAFE").all() else ("BLOCKED" if (df.verdict == "BLOCKED").any() and health < 55 else "RISKY")
c = st.columns([2, 1, 1, 1])
with c[0]:
    fig = go.Figure(go.Indicator(mode="gauge+number", value=health, number=dict(suffix="/100", font=dict(family="Space Grotesk", color=theme.C["text"])),
                                 title=dict(text="Portfolio health"), gauge=dict(axis=dict(range=[0, 100]), bar=dict(color=theme.TIER_COLOR[tier]),
                                 bgcolor="rgba(12,32,25,.6)", steps=[dict(range=[0, 55], color="rgba(251,113,133,.25)"), dict(range=[55, 85], color="rgba(251,191,36,.18)"),
                                                                       dict(range=[85, 100], color="rgba(245,196,81,.20)")])))
    st.plotly_chart(theme.style_fig(fig, 250), use_container_width=True)
c[1].metric("SAFE", int((df.verdict == "SAFE").sum()), f"{int(df[df.verdict=='SAFE'].tco2.sum()):,} tCO₂", delta_color="off", delta_arrow="off")
c[2].metric("RISKY", int((df.verdict == "RISKY").sum()), f"{int(df[df.verdict=='RISKY'].tco2.sum()):,} tCO₂", delta_color="off", delta_arrow="off")
c[3].metric("BLOCKED", int((df.verdict == "BLOCKED").sum()), f"{int(df[df.verdict=='BLOCKED'].tco2.sum()):,} tCO₂", delta_color="off", delta_arrow="off")

# replacement inventory: unsold tonnes still at developers, from clean projects
inv = []
for s in res.ledger.segs:
    if s.retired or s.owner != iss[iss.project_id == s.project_id].developer.iloc[0]:
        continue
    ps = res.scores[res.scores.project_id == s.project_id].iloc[0]
    proj_flagged = any(f["project_id"] == s.project_id and f["subject_type"] in ("project", "issuance") for f in res.flags)
    if ps.tier == "VERIFIED" and not proj_flagged and not sc_mod.score_range(s.start, s.end, res.flags, res.scores)["flags"]:
        inv.append(dict(start=s.start, end=s.end, tco2=s.end - s.start + 1, project=s.project_id, method=cat[s.project_id], score=ps.score,
                        price=res.price_by_project.get(s.project_id, 10)))

st.markdown("### Verdict per range")
for r in df.itertuples():
    cls = {"BLOCKED": "coral", "SAFE": "gold", "RISKY": ""}[r.verdict]
    why = "".join(f"<div class='vq-sub'>• {w}</div>" for w in r.why[:3])
    theme.card(f"<div style='display:flex;justify-content:space-between;align-items:center'><div class='vq-mono'>{fmt_serial(r.start)} → {fmt_serial(r.end)}"
               f" <span class='vq-muted'>· {r.tco2:,} tCO₂ · {r.project or 'unknown'}</span></div><div>{theme.badge(r.verdict)} <b>{r.score:.0f}</b>/100</div></div>{why}", cls=cls)
    if r.verdict != "SAFE":
        mine = cat.get(r.project)
        cand = sorted([i for i in inv if i["method"] == mine and i["project"] != r.project] or inv, key=lambda i: abs(i["tco2"] - r.tco2))[:2]
        if cand:
            st.markdown("**What to replace it with** (unsold, unflagged tonnes from VERIFIED projects):")
            st.dataframe(pd.DataFrame([dict(serials=f"{fmt_serial(i['start'])} → {fmt_serial(i['end'])}", tco2=i["tco2"], project=i["project"], trust=i["score"],
                                           indicative_usd_per_t=round(i["price"], 2)) for i in cand]), hide_index=True, use_container_width=True)
theme.footer()
