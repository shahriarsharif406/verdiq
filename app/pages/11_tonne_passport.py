import streamlit as st

import data
import theme
import views
from i18n import t
from engine import passport as pp
from engine.common import fmt_serial, parse_range

res = data.result()
theme.page_title(t("pp_title"), t("pp_sub"))

iss = res.data["issuances"]
# curated examples: one clean, one double-sold, one wash-traded, one never issued
examples = {}
clean = next((s for s in res.ledger.segs if s.retired and s.end - s.start > 1200 and s.project_id in ("P07", "P05", "P03")), None)
if clean:
    examples["✅ A clean, retired credit"] = (clean.start, clean.start + 999)
for ev_id, label in (("T9001", "⛔ Double-sold range (Kisumu)"), ("T9004", "🔁 Wash-traded range"), ("T9003", "👻 Never-issued range")):
    r = res.events[res.events.event_id == ev_id]
    if len(r):
        examples[label] = (int(r.iloc[0].serial_start), int(r.iloc[0].serial_end))
p8 = iss[iss.issuance_id == "ISS-P08-2022"].iloc[0]
examples["📏 Impossible yield (Cusco)"] = (int(p8.serial_start), int(p8.serial_start) + 1999)

ex = st.radio("Examples", list(examples) + ["Custom range"], horizontal=True)
if ex == "Custom range":
    txt = st.text_input("Serial range", value=f"{iss.serial_start.iloc[3]}-{iss.serial_start.iloc[3] + 1999}")
else:
    a, b = examples[ex]
    txt = f"{a}-{b}"
    st.text_input("Serial range", value=txt, disabled=True)
try:
    s, e = parse_range(txt)
    if e - s > 5_000_000:
        raise ValueError
    p = pp.build(res, s, e, data.tx_index(), data.anchor_index())
except Exception:
    st.warning("Enter two serial numbers, e.g. 2507189-2508936.")
    st.stop()

url = views.passport_url(s, e)
views.render_passport(p, url)
st.markdown("---")
st.markdown(f"**Public verification link** (works for anyone, no sidebar, no login): [{url}]({url})")
theme.footer()
