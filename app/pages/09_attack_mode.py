import random
import time

import pandas as pd
import streamlit as st

import data
import theme
import views
from i18n import t
from engine import chain
from engine.common import RULES, STATUS_RULE, fmt_serial, make_flag
from engine.match import classify

res = data.result()
theme.page_title(t("atk_title"), t("atk_sub"))

REASONS = {
    "NOT_OWNER": "Seller no longer owns these serials (already sold)",
    "NOT_ISSUED": "Serials were never issued by the registry",
    "ALREADY_RETIRED": "Tonnes already retired for this claim",
    "DOUBLE_CLAIM": "Second claim on tonnes already retired",
    "RETIRED": "Credits are retired and cannot be traded",
    "HOST_DOUBLE_CLAIM": "Host country already counts these tonnes",
}
if "atk" not in st.session_state:
    st.session_state["atk"] = dict(log=[], blocked=0, tonnes=0, usd=0.0)
A = st.session_state["atk"]

# ---- chain connection ----
live = chain.chain_ready()
top = st.columns([3, 2])
with top[0]:
    if live:
        st.markdown(f"{theme.badge('VERIFIED', 'REAL CONTRACT LIVE')} <span class='vq-sub'>VerdiqRegistry on a local Hardhat node · {data.chain_replay()['contract']}</span>", unsafe_allow_html=True)
    elif chain.toolchain_available():
        st.markdown(f"{theme.badge('RISKY', 'CHAIN OFFLINE')} <span class='vq-sub'>the first attack boots a local Hardhat node and replays the ledger (≈30-60 s, once)</span>", unsafe_allow_html=True)
    else:
        st.markdown(f"{theme.badge('RISKY', 'PYTHON MIRROR')} <span class='vq-sub'>Node/Hardhat not installed: attacks run against the Python mirror of the contract rules</span>", unsafe_allow_html=True)
tally = top[1].empty()


def draw_tally():
    with tally.container():
        m = st.columns(3)
        m[0].metric("Attacks blocked", A["blocked"])
        m[1].metric("tCO₂ protected", f"{A['tonnes']:,}")
        m[2].metric("USD blocked", f"${A['usd']:,.0f}")


draw_tally()

kind = st.radio("Attack type", ["Random", "Double sale", "Double retirement"], horizontal=True)
st.markdown("<div class='vq-danger'>", unsafe_allow_html=True)
go_btn = st.button(f"⚡ {t('atk_btn')}", use_container_width=True)
st.markdown("</div>", unsafe_allow_html=True)


def pick_attack(kind: str, rnd: random.Random) -> dict:
    sold = [s for s in res.ledger.segs if s.history and not s.retired and s.end - s.start >= 800]
    done = [s for s in res.ledger.segs if s.retired and s.end - s.start >= 800]
    if kind == "Random":
        kind = rnd.choice(["Double sale", "Double retirement"])
    buyers = sorted({r.buyer for r in res.data["trades"].itertuples()} & set(res.data["corp_claims"].company))
    if kind == "Double sale":
        s = rnd.choice(sold)
        a = s.start + rnd.randint(0, max(0, (s.end - s.start) // 3))
        b = min(s.end, a + rnd.randint(800, 4000))
        seller = s.history[-1]
        return dict(kind="TRADE", label="Double sale", actor=seller, counterparty=rnd.choice([x for x in buyers if x != s.owner]), start=a, end=b,
                    story=f"{seller} (who already sold these tonnes) offers them AGAIN to a second buyer.")
    s = rnd.choice(done)
    a = s.start + rnd.randint(0, max(0, (s.end - s.start) // 3))
    b = min(s.end, a + rnd.randint(500, 3000))
    return dict(kind="RETIREMENT", label="Double retirement", actor=s.retired_by, counterparty="FY2026 net-zero claim", start=a, end=b,
                story=f"{s.retired_by} (who already retired these tonnes) tries to retire them AGAIN for a second claim.")


if go_btn:
    if not live and chain.toolchain_available():
        with st.spinner("Booting local Hardhat node and replaying the ledger on-chain…"):
            live = chain.ensure_chain()
    rnd = random.Random(time.time_ns())
    atk = pick_attack(kind, rnd)
    n = atk["end"] - atk["start"] + 1
    px = res.price_by_project.get(f"P{atk['start'] // 2_000_000:02d}", 10.0)

    s1 = st.container()
    with s1:
        st.markdown(f"<div class='vq-card coral'><div class='vq-k'>1 · attack submitted</div><div class='vq-h' style='font-size:1.3rem;font-weight:700;color:{theme.C['coral']}'>"
                    f"{atk['label'].upper()} · {n:,} tCO₂</div><div>{atk['story']}</div><div class='vq-mono vq-muted' style='margin-top:6px'>"
                    f"{fmt_serial(atk['start'])} → {fmt_serial(atk['end'])} · by {atk['actor']}</div></div>", unsafe_allow_html=True)
    time.sleep(0.5)
    t0 = time.time()
    with st.spinner("Contract executing…"):
        tx = chain.fire_attack(dict(kind=atk["kind"], actor=atk["actor"], counterparty=atk["counterparty"], start=atk["start"], end=atk["end"]), res.ledger, classify)
    chain_ms = tx.get("ms") or int((time.time() - t0) * 1000)
    blocked = not tx["accepted"]
    code = tx.get("reason", "")
    if blocked:
        st.markdown(
            f"<div class='vq-alert'><div class='vq-k'>2 · smart-contract firewall</div><div style='display:flex;gap:22px;align-items:center;flex-wrap:wrap'>"
            f"<div class='vq-stamp'>{t('atk_blocked')}</div><div><div class='vq-h' style='font-size:1.2rem;font-weight:700'>Transaction reverted: <span class='vq-mono' style='color:{theme.C['coral']}'>{code}</span></div>"
            f"<div>{REASONS.get(code, 'Rule violation')}</div>"
            f"<div class='vq-hash' style='margin-top:6px'>tx {tx['txHash']}</div>"
            f"<div class='vq-sub'>{'block ' + str(tx['block']) + ' · ' if tx.get('block') else ''}{'gas ' + format(tx['gasUsed'], ',') + ' · ' if tx.get('gasUsed') else ''}{chain_ms} ms · "
            f"source: {tx['source']}</div></div></div></div>", unsafe_allow_html=True)
        if tx.get("note"):
            st.caption(tx["note"])
    else:
        st.error("The contract ACCEPTED this transaction. That should not happen. See logs.")
    time.sleep(0.4)

    # ---- engine side: independent detection on the off-chain ledger
    t1 = time.time()
    status, why = classify(res.ledger, atk["kind"], atk["start"], atk["end"], atk["actor"])
    eng_ms = (time.time() - t1) * 1000
    rule = STATUS_RULE.get(status)
    if rule:
        f = make_flag(rule, "event", "ATTACK-" + str(len(A["log"]) + 1), why, serial_start=atk["start"], serial_end=atk["end"], tco2=n, usd=n * px)
        st.markdown(f"<div class='vq-k' style='margin-top:10px'>3 · reconciliation engine</div>", unsafe_allow_html=True)
        views.flag_card(f)
        st.markdown(f"<div class='vq-sub'>flagged in {eng_ms:.1f} ms · status <b>{status}</b> · rule {rule}</div>", unsafe_allow_html=True)
    st.markdown(
        f"<div class='vq-card gold'><div class='vq-k'>Without VERDIQ</div><div class='vq-h' style='font-size:1.4rem;font-weight:700'>"
        f"{n:,} tCO₂ (≈ ${n*px:,.0f}) would have been counted twice.</div>"
        f"<div class='vq-sub'>≈ {n/4.6:,.0f} cars' worth of annual emissions claimed as offset without a real reduction behind it.</div></div>", unsafe_allow_html=True)
    if blocked:
        A["blocked"] += 1; A["tonnes"] += n; A["usd"] += n * px
        A["log"].insert(0, dict(time=time.strftime("%H:%M:%S"), attack=atk["label"], tco2=n, by=atk["actor"], verdict="BLOCKED", reason=code,
                                tx=views.short(tx["txHash"]), engine=f"{rule} {status}", source=tx["source"]))
        draw_tally()

if A["log"]:
    st.markdown("### Attack log")
    st.dataframe(pd.DataFrame(A["log"]), use_container_width=True, hide_index=True)
elif not go_btn:
    theme.card("<div class='vq-h' style='font-size:1.15rem;font-weight:600'>Ready.</div><div class='vq-sub'>Press the button. A fresh, random double-sale or double-retirement is fired at the live registry. "
               "The contract reverts it, the engine flags it, and the tonnes that would have been counted twice are added to the impact counter.</div>")
theme.footer()
