"""VERDIQ - entry point. `streamlit run app/streamlit_app.py`"""
from __future__ import annotations

import streamlit as st

st.set_page_config(page_title="VERDIQ · Every tonne, verified once", page_icon="🌿", layout="wide", initial_sidebar_state="expanded")

import theme  # noqa: E402
from i18n import language_selector, t  # noqa: E402

theme.inject()

# ---- public verification route: /?passport=<start>-<end>  (also accepts a single serial)
q = st.query_params
if "passport" in q:
    import data  # noqa: E402
    import views  # noqa: E402
    from engine.common import parse_range  # noqa: E402
    from engine import passport as pp  # noqa: E402

    st.markdown("<style>[data-testid='stSidebar'],[data-testid='stSidebarCollapsedControl'],[data-testid='collapsedControl']{display:none}</style>",
                unsafe_allow_html=True)
    st.markdown(theme.logo_svg(40, text=True), unsafe_allow_html=True)
    st.markdown("<div class='vq-sub' style='margin:6px 0 14px'>Public verification page · anyone can check this credit. Synthetic demo data.</div>", unsafe_allow_html=True)
    try:
        s, e = parse_range(q["passport"])
        res = data.result()
        if s == e:  # a single serial resolves to the whole segment that contains it
            c, _ = res.ledger.pieces(s, s)
            if c:
                s, e = c[0][2].start, c[0][2].end
        p = pp.build(res, s, e, data.tx_index(), data.anchor_index())
        views.render_passport(p, views.passport_url(s, e), public=True)
    except Exception:
        st.error("That serial range could not be read. Use the form `?passport=<start>-<end>`, e.g. `?passport=2507189-2508936`.")
    theme.footer()
    st.stop()

language_selector()

pages = [
    st.Page("pages/01_overview.py", title=t("nav_overview"), icon="🌿", default=True),
    st.Page("pages/02_reconciliation.py", title=t("nav_recon"), icon="⚖️"),
    st.Page("pages/03_map.py", title=t("nav_map"), icon="🗺️"),
    st.Page("pages/04_trust_scores.py", title=t("nav_trust"), icon="🛡️"),
    st.Page("pages/05_fraud_network.py", title=t("nav_network"), icon="🕸️"),
    st.Page("pages/06_time_machine.py", title=t("nav_time"), icon="⏳"),
    st.Page("pages/07_pre_purchase.py", title=t("nav_prepurchase"), icon="🛒"),
    st.Page("pages/08_greenwashing.py", title=t("nav_greenwash"), icon="🌿"),
    st.Page("pages/09_attack_mode.py", title=t("nav_attack"), icon="⚡"),
    st.Page("pages/10_day_end_close.py", title=t("nav_close"), icon="🔏"),
    st.Page("pages/11_tonne_passport.py", title=t("nav_passport"), icon="🎫"),
    st.Page("pages/12_case_files.py", title=t("nav_cases"), icon="📁"),
]
nav = st.navigation(pages)
with st.sidebar:
    st.markdown(theme.logo_svg(46, text=True), unsafe_allow_html=True)
    st.markdown("<div class='vq-sub' style='margin-top:10px'>Synthetic data · simulated NDVI · no real registry data</div>", unsafe_allow_html=True)
nav.run()
