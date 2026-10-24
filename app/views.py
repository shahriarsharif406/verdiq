"""Reusable view fragments: flag cards, passport certificate, QR code."""
from __future__ import annotations

import base64
import html
import io
import os

import qrcode
import streamlit as st

import theme
from data import anchor_index, result, tx_index
from i18n import t

from engine import passport as pp
from engine.common import fmt_serial


def short(h: str, n: int = 10) -> str:
    return h if not h or len(h) <= 2 * n + 2 else f"{h[:n+2]}…{h[-n:]}"


def flag_card(f: dict, tx: dict | None = None) -> None:
    sev = f["severity"]
    rng = f" · <span class='vq-mono'>{fmt_serial(f['serial_start'])}→{fmt_serial(f['serial_end'])}</span>" if f.get("serial_start") is not None else ""
    txh = ""
    if tx and not tx["ok"]:
        txh = (f"<div style='margin-top:6px'>{theme.badge('BLOCKED', 'REVERTED ON-CHAIN: ' + tx['reason'])} "
               f"<span class='vq-hash'>{tx['txHash']}</span></div>")
    st.markdown(
        f"<div class='vq-flag {sev}'><div>{theme.badge(sev)} <b>{f['rule_id']} · {f['rule_name']}</b> · <span class='vq-mono'>{html.escape(str(f['subject_id']))}</span>"
        f"{rng} · <span class='vq-muted'>{f['tco2']:,} tCO₂{' · $' + format(f['usd_at_risk'], ',.0f') if f['usd_at_risk'] else ''}</span></div>"
        f"<div style='margin-top:4px'>{html.escape(f['reason'])}</div>{txh}</div>", unsafe_allow_html=True)


def qr_png(url: str) -> bytes:
    img = qrcode.QRCode(box_size=7, border=2, error_correction=qrcode.constants.ERROR_CORRECT_M)
    img.add_data(url)
    img.make(fit=True)
    buf = io.BytesIO()
    img.make_image(fill_color="#F5C451", back_color="#0C2019").save(buf, format="PNG")
    return buf.getvalue()


def base_url() -> str:
    env = os.environ.get("VERDIQ_PUBLIC_URL")
    if env:
        return env.rstrip("/")
    try:
        u = st.context.url  # type: ignore[attr-defined]
        if u:
            from urllib.parse import urlparse
            pu = urlparse(u)
            return f"{pu.scheme}://{pu.netloc}"
    except Exception:
        pass
    return "http://localhost:8501"


def passport_url(start: int, end: int) -> str:
    return f"{base_url()}/?passport={start}-{end}"


def seal(verdict: str) -> str:
    color = theme.TIER_COLOR.get(verdict, theme.C["gold"])
    mark = "✓" if verdict == "SAFE" else ("!" if verdict == "RISKY" else "✕")
    return (f'<svg width="96" height="96" viewBox="0 0 100 100"><polygon points="50,3 92,26 92,74 50,97 8,74 8,26" fill="#0C2019" stroke="{color}" stroke-width="4"/>'
            f'<polygon points="50,12 83,31 83,69 50,88 17,69 17,31" fill="none" stroke="{color}" stroke-width="1.2" stroke-dasharray="3 3"/>'
            f'<text x="50" y="62" text-anchor="middle" font-family="Space Grotesk" font-weight="700" font-size="40" fill="{color}">{mark}</text></svg>')


def render_passport(p: dict, qr_url: str | None = None, public: bool = False) -> None:
    verdict = p["verdict"]
    cls = {"SAFE": "", "RISKY": "risky", "BLOCKED": "blocked"}[verdict]
    word = {"SAFE": "VERIFIED", "RISKY": "RISKY", "BLOCKED": "BLOCKED"}[verdict]
    owner = "—"
    if p["segments"]:
        owners = {s["owner"] for s in p["segments"] if not s["retired"]}
        owner = ", ".join(sorted(owners)) if owners else f"Retired by {p['segments'][0]['retired_by']}"
    c1, c2 = st.columns([5, 2])
    with c1:
        st.markdown(
            f"""<div class="vq-passport {cls}">
<div style="display:flex;gap:18px;align-items:center;justify-content:space-between">
 <div><div class="vq-k" style="color:{theme.C['gold']}">VERDIQ · TONNE PASSPORT</div>
 <div class="vq-h" style="font-size:1.7rem;font-weight:700;margin:4px 0">{html.escape(p['project_name'] or 'Unissued serial range')}</div>
 <div class="vq-sub">{html.escape(p['country'] or '')} {('· ' + html.escape(p['methodology'])) if p['methodology'] else ''} {('· vintage ' + str(p['vintage'])) if p['vintage'] else ''}</div></div>
 <div style="text-align:center">{seal(verdict)}<div class="vq-h" style="color:{theme.TIER_COLOR[verdict]};font-weight:700;letter-spacing:.1em">{word}</div></div>
</div>
<hr/>
<div style="display:grid;grid-template-columns:repeat(3,1fr);gap:14px">
 <div><div class="vq-k">Serial range</div><div class="vq-mono" style="font-size:.85rem">{fmt_serial(p['start'])}<br/>→ {fmt_serial(p['end'])}</div></div>
 <div><div class="vq-k">Quantity</div><div class="vq-v" style="font-size:1.5rem">{p['tco2']:,} <span class="vq-sub">tCO₂</span></div></div>
 <div><div class="vq-k">{t('score')}</div><div class="vq-v" style="font-size:1.5rem;color:{theme.TIER_COLOR[verdict]}">{p['score']['score']:.0f}<span class="vq-sub">/100</span></div></div>
 <div><div class="vq-k">Status</div><div><b>{p['state']}</b></div></div>
 <div style="grid-column:span 2"><div class="vq-k">Current holder</div><div><b>{html.escape(owner)}</b></div></div>
</div></div>""", unsafe_allow_html=True)
    with c2:
        if qr_url:
            st.image(qr_png(qr_url), caption="Scan to verify" if not public else None, use_container_width=True)
            st.markdown(f"<div class='vq-hash' style='font-size:.7rem'>{html.escape(qr_url)}</div>", unsafe_allow_html=True)

    st.markdown("#### Why this verdict")
    for w in p["score"]["why"]:
        st.markdown(f"- {w}")

    t1, t2, t3 = st.tabs(["Timeline", "Owner chain", "Merkle proof"])
    with t1:
        rows = []
        for e in p["timeline"]:
            cls_ = "bad" if not e["ok"] else ("gold" if e["kind"] == "ISSUED" else "")
            tx = e.get("tx")
            txh = ""
            if tx:
                txh = (f"<div class='vq-hash'>{'⛓ blocked tx ' if not tx['ok'] else '⛓ tx '}{short(tx['txHash'], 12)}"
                       f"{' · reverted: ' + html.escape(tx['reason']) if not tx['ok'] else ''}</div>")
            rows.append(f"<div class='{cls_}'><span class='vq-muted vq-mono' style='font-size:.78rem'>{e['date']}</span> · <b>{html.escape(e['title'])}</b>"
                        f"<div class='vq-sub'>{html.escape(e['detail'])}</div>{txh}</div>")
        st.markdown(f"<div class='vq-tl'>{''.join(rows) or 'No ledger activity.'}</div>", unsafe_allow_html=True)
    with t2:
        if p["owner_chain"]:
            st.markdown(" → ".join(f"**{o}**" for o in p["owner_chain"]))
        else:
            st.info("This range was never issued, so it has no owner chain.")
    with t3:
        m = p["merkle"]
        if not m:
            st.info("No ledger segment in the latest Day-End Close covers this range.")
        else:
            ok = m["valid"]
            st.markdown(f"{theme.badge('VERIFIED' if ok else 'BLOCKED', 'MERKLE PROOF ' + ('VALID' if ok else 'INVALID'))} "
                        f"&nbsp; close of <b>{m['close_date']}</b> · leaf #{m['index']} · {len(m['path'])} sibling hashes", unsafe_allow_html=True)
            st.markdown(f"<div class='vq-sub'>Root</div><div class='vq-hash'>{m['root']}</div>"
                        f"<div class='vq-sub' style='margin-top:6px'>Leaf</div><div class='vq-hash'>{m['leaf']}</div>", unsafe_allow_html=True)
            if m.get("anchor"):
                st.markdown(f"<div class='vq-sub' style='margin-top:6px'>Anchored on-chain · block {m['anchor']['block']}</div>"
                            f"<div class='vq-hash'>{m['anchor']['txHash']}</div>", unsafe_allow_html=True)
            with st.expander("Proof path"):
                st.code("\n".join(m["path"]))
