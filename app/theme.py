"""Midnight Forest theme: CSS, logo, badges, animated counters and a Plotly template. Reused by every page."""
from __future__ import annotations

import html
import json

import plotly.graph_objects as go
import plotly.io as pio
import streamlit as st
import streamlit.components.v1 as components

C = dict(bg="#06130F", panel="#0C2019", emerald="#10B981", teal="#2DD4BF", gold="#F5C451", coral="#FB7185",
         amber="#FBBF24", text="#E7F5EE", muted="#8FB5A3", line="rgba(16,185,129,.28)")
TIER_COLOR = {"VERIFIED": C["gold"], "SAFE": C["gold"], "RISKY": C["amber"], "BLOCKED": C["coral"], "DISPUTED": C["coral"],
              "OK": C["emerald"], "WARN": C["amber"], "BAD": C["coral"]}
SEV_COLOR = {"CRITICAL": C["coral"], "HIGH": "#F97316", "MEDIUM": C["amber"], "LOW": C["muted"]}

HEX_BG = ("data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' width='56' height='98' viewBox='0 0 56 98'>"
          "<path d='M28 66L0 50V16L28 0l28 16v34zM28 100L0 84V50l28-16 28 16v34z' fill='none' stroke='%2310B981' "
          "stroke-opacity='.07' stroke-width='1'/></svg>")

FONTS = ("@import url('https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@500;600;700&family=Inter:wght@400;500;600"
         "&family=JetBrains+Mono:wght@400;600&family=Noto+Sans+Bengali:wght@400;600;700&display=swap');")

CSS = f"""
{FONTS}
:root {{ --bg:{C['bg']}; --panel:{C['panel']}; --em:{C['emerald']}; --teal:{C['teal']}; --gold:{C['gold']};
  --coral:{C['coral']}; --amber:{C['amber']}; --text:{C['text']}; --muted:{C['muted']}; }}
html, body, [class*="css"], .stApp {{ font-family:'Inter','Noto Sans Bengali',system-ui,sans-serif; color:var(--text); }}
.stApp {{ background: radial-gradient(1200px 500px at 85% -10%, rgba(45,212,191,.10), transparent 60%),
          radial-gradient(900px 500px at -10% 10%, rgba(16,185,129,.10), transparent 60%),
          url("{HEX_BG}"), var(--bg); background-attachment: fixed; }}
h1,h2,h3,h4, .vq-h {{ font-family:'Space Grotesk','Noto Sans Bengali',sans-serif !important; letter-spacing:-.01em; color:var(--text); }}
h1 {{ font-weight:700 !important; }}
code, .mono, .vq-mono {{ font-family:'JetBrains Mono',ui-monospace,monospace !important; }}
.block-container {{ padding-top:2.2rem; max-width:1280px; }}
header[data-testid="stHeader"] {{ background:transparent; }}
[data-testid="stSidebar"] {{ background:linear-gradient(180deg,#07170f,#06130F); border-right:1px solid {C['line']}; }}
[data-testid="stSidebarNav"] a, [data-testid="stSidebar"] a {{ border-radius:10px; }}
hr {{ border-color:{C['line']} !important; }}
a {{ color:var(--teal) !important; }}

/* glass cards */
.vq-card {{ background:linear-gradient(145deg, rgba(12,32,25,.78), rgba(12,32,25,.46)); backdrop-filter:blur(10px);
  border:1px solid {C['line']}; border-radius:16px; padding:18px 20px; box-shadow:0 0 0 1px rgba(16,185,129,.04), 0 10px 34px -14px rgba(16,185,129,.35);
  margin-bottom:12px; }}
.vq-card.coral {{ border-color:rgba(251,113,133,.5); box-shadow:0 0 28px -8px rgba(251,113,133,.45); }}
.vq-card.gold {{ border-color:rgba(245,196,81,.55); box-shadow:0 0 28px -10px rgba(245,196,81,.45); }}
.vq-k {{ font-size:.74rem; text-transform:uppercase; letter-spacing:.12em; color:var(--muted); }}
.vq-v {{ font-family:'Space Grotesk',sans-serif; font-size:2.1rem; font-weight:700; line-height:1.1; }}
.vq-sub {{ color:var(--muted); font-size:.85rem; }}
.vq-muted {{ color:var(--muted); }}

/* hero */
.vq-hero {{ position:relative; overflow:hidden; border-radius:20px; padding:30px 34px; margin-bottom:18px;
  border:1px solid {C['line']};
  background: linear-gradient(120deg, rgba(16,185,129,.22), rgba(45,212,191,.10) 45%, rgba(245,196,81,.10)), var(--panel); }}
.vq-hero:before {{ content:""; position:absolute; inset:-40% -10% auto auto; width:520px; height:520px; border-radius:50%;
  background:radial-gradient(circle, rgba(45,212,191,.28), transparent 65%); animation: aurora 9s ease-in-out infinite alternate; }}
@keyframes aurora {{ from {{ transform:translate(0,0) scale(1); opacity:.7; }} to {{ transform:translate(-60px,30px) scale(1.15); opacity:1; }} }}
.vq-hero h1 {{ margin:0 0 4px 0; font-size:2.3rem; position:relative; }}
.vq-hero p {{ margin:0; color:var(--muted); font-size:1.02rem; position:relative; max-width:760px; }}
.vq-tag {{ font-family:'Space Grotesk'; color:var(--gold); font-weight:600; letter-spacing:.04em; position:relative; }}

/* LIVE pulse */
.vq-live {{ display:inline-flex; align-items:center; gap:8px; font-size:.75rem; letter-spacing:.14em; color:var(--em); font-weight:600; }}
.vq-live i {{ width:9px; height:9px; border-radius:50%; background:var(--em); box-shadow:0 0 0 0 rgba(16,185,129,.7); animation:pulse 1.6s infinite; }}
@keyframes pulse {{ 70% {{ box-shadow:0 0 0 10px rgba(16,185,129,0); }} 100% {{ box-shadow:0 0 0 0 rgba(16,185,129,0); }} }}

/* badges */
.vq-badge {{ display:inline-flex; align-items:center; gap:6px; padding:3px 11px; border-radius:999px; font-size:.72rem; font-weight:700;
  letter-spacing:.08em; border:1px solid currentColor; clip-path:polygon(8% 0,92% 0,100% 50%,92% 100%,8% 100%,0 50%); }}
.vq-badge.VERIFIED, .vq-badge.SAFE {{ color:var(--gold); background:rgba(245,196,81,.12); }}
.vq-badge.RISKY, .vq-badge.WARN, .vq-badge.MEDIUM {{ color:var(--amber); background:rgba(251,191,36,.10); }}
.vq-badge.BLOCKED, .vq-badge.DISPUTED, .vq-badge.CRITICAL, .vq-badge.BAD {{ color:var(--coral); background:rgba(251,113,133,.12); }}
.vq-badge.HIGH {{ color:#F97316; background:rgba(249,115,22,.12); }}
.vq-badge.OK, .vq-badge.MATCHED {{ color:var(--em); background:rgba(16,185,129,.12); }}
.vq-badge.LOW {{ color:var(--muted); }}

/* flag rows */
.vq-flag {{ border-left:3px solid var(--coral); padding:10px 14px; margin:8px 0; background:rgba(251,113,133,.06); border-radius:0 12px 12px 0; }}
.vq-flag.HIGH {{ border-color:#F97316; background:rgba(249,115,22,.06); }}
.vq-flag.MEDIUM {{ border-color:var(--amber); background:rgba(251,191,36,.06); }}
.vq-hash {{ font-family:'JetBrains Mono',monospace; font-size:.78rem; color:var(--teal); word-break:break-all; }}

/* attack mode */
@keyframes shake {{ 0%,100% {{ transform:translateX(0); }} 20% {{ transform:translateX(-7px); }} 40% {{ transform:translateX(7px); }} 60% {{ transform:translateX(-5px); }} 80% {{ transform:translateX(5px); }} }}
@keyframes alertflash {{ 0% {{ box-shadow:0 0 0 0 rgba(251,113,133,.8); }} 100% {{ box-shadow:0 0 0 38px rgba(251,113,133,0); }} }}
@keyframes stamp {{ 0% {{ transform:rotate(-14deg) scale(3); opacity:0; }} 60% {{ transform:rotate(-14deg) scale(.92); opacity:1; }} 100% {{ transform:rotate(-14deg) scale(1); opacity:1; }} }}
.vq-alert {{ animation: shake .5s, alertflash 1s 2; border:1px solid var(--coral); border-radius:16px; padding:18px 22px; background:rgba(251,113,133,.09); }}
.vq-stamp {{ display:inline-block; font-family:'Space Grotesk'; font-weight:700; font-size:2.4rem; letter-spacing:.14em; color:var(--coral);
  border:4px solid var(--coral); border-radius:10px; padding:2px 22px; transform:rotate(-14deg); animation: stamp .55s cubic-bezier(.2,1.4,.4,1) both;
  text-shadow:0 0 18px rgba(251,113,133,.6); box-shadow:0 0 22px rgba(251,113,133,.35), inset 0 0 14px rgba(251,113,133,.25); }}
.vq-stamp.ok {{ color:var(--em); border-color:var(--em); text-shadow:0 0 18px rgba(16,185,129,.6); }}
.vq-step {{ display:flex; gap:12px; align-items:flex-start; padding:8px 0; }}
.vq-step b {{ min-width:26px; height:26px; border-radius:50%; display:inline-flex; align-items:center; justify-content:center; background:rgba(16,185,129,.18); color:var(--em); font-size:.8rem; }}

/* passport */
.vq-passport {{ position:relative; border:2px solid var(--gold); border-radius:20px; padding:26px 30px;
  background: linear-gradient(160deg, rgba(245,196,81,.10), rgba(12,32,25,.9) 38%), var(--panel);
  box-shadow:0 0 0 6px rgba(245,196,81,.07), 0 0 0 7px rgba(245,196,81,.35), 0 20px 60px -20px rgba(245,196,81,.35); }}
.vq-passport.blocked {{ border-color:var(--coral); box-shadow:0 0 0 6px rgba(251,113,133,.07), 0 0 0 7px rgba(251,113,133,.35); background:linear-gradient(160deg, rgba(251,113,133,.10), rgba(12,32,25,.9) 38%), var(--panel); }}
.vq-passport.risky {{ border-color:var(--amber); }}
.vq-tl {{ border-left:2px solid {C['line']}; margin-left:8px; padding-left:18px; }}
.vq-tl > div {{ position:relative; padding:6px 0 10px 0; }}
.vq-tl > div:before {{ content:""; position:absolute; left:-25px; top:12px; width:12px; height:12px; background:var(--em); clip-path:polygon(25% 0,75% 0,100% 50%,75% 100%,25% 100%,0 50%); }}
.vq-tl > div.bad:before {{ background:var(--coral); }}
.vq-tl > div.gold:before {{ background:var(--gold); }}

/* streamlit widgets */
.stButton > button, .stDownloadButton > button {{ border-radius:12px; border:1px solid {C['line']}; background:linear-gradient(135deg, rgba(16,185,129,.22), rgba(45,212,191,.12));
  color:var(--text); font-weight:600; transition: all .18s; }}
.stButton > button:hover, .stDownloadButton > button:hover {{ border-color:var(--em); box-shadow:0 0 22px -4px rgba(16,185,129,.7); transform:translateY(-1px); }}
.stButton > button[kind="primary"] {{ background:linear-gradient(135deg,#10B981,#2DD4BF); color:#032217; border:none; }}
.vq-danger .stButton > button {{ background:linear-gradient(135deg,#FB7185,#F43F5E); color:#fff; border:none; font-size:1.1rem; padding:.7rem 1.4rem; box-shadow:0 0 30px -6px rgba(251,113,133,.8); }}
[data-testid="stMetric"] {{ background:rgba(12,32,25,.6); border:1px solid {C['line']}; border-radius:14px; padding:12px 16px; }}
[data-testid="stMetricValue"] {{ font-family:'Space Grotesk'; font-size:1.65rem; }}
[data-testid="stMetricValue"] > div {{ overflow:visible; text-overflow:clip; white-space:normal; }}
[data-testid="stDataFrame"] {{ border:1px solid {C['line']}; border-radius:12px; }}
.stTabs [data-baseweb="tab-list"] {{ gap:6px; }}
.stTabs [data-baseweb="tab"] {{ background:rgba(12,32,25,.6); border-radius:10px 10px 0 0; padding:8px 16px; }}
.stTabs [aria-selected="true"] {{ color:var(--em) !important; }}
[data-testid="stExpander"] {{ border:1px solid {C['line']}; border-radius:12px; background:rgba(12,32,25,.45); }}
.vq-foot {{ color:var(--muted); font-size:.78rem; margin-top:28px; border-top:1px solid {C['line']}; padding-top:12px; }}
.vq-public [data-testid="stSidebar"], .vq-public [data-testid="collapsedControl"] {{ display:none; }}
"""


def logo_svg(size: int = 44, text: bool = False) -> str:
    """Hexagon + leaf + check mark, drawn in code."""
    svg = f"""<svg xmlns="http://www.w3.org/2000/svg" width="{size}" height="{size}" viewBox="0 0 100 100" role="img" aria-label="VERDIQ logo">
<defs><linearGradient id="vqg" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#2DD4BF"/><stop offset="1" stop-color="#10B981"/></linearGradient>
<linearGradient id="vqk" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#F5C451"/><stop offset="1" stop-color="#FBBF24"/></linearGradient></defs>
<polygon points="50,4 91,27 91,73 50,96 9,73 9,27" fill="#0C2019" stroke="url(#vqg)" stroke-width="4"/>
<path d="M50 78C30 70 24 48 30 30c18 2 34 12 34 30 0 8-4 14-14 18z" fill="url(#vqg)" opacity=".92"/>
<path d="M50 78C50 62 52 52 60 40" stroke="#0C2019" stroke-width="3" fill="none" stroke-linecap="round"/>
<path d="M36 52l9 9 19-23" stroke="url(#vqk)" stroke-width="7" fill="none" stroke-linecap="round" stroke-linejoin="round"/>
</svg>"""
    if not text:
        return svg
    return (f'<div style="display:flex;align-items:center;gap:10px">{svg}<div><div class="vq-h" style="font-size:1.5rem;font-weight:700;'
            f'letter-spacing:.06em;line-height:1">VERDIQ</div><div style="color:{C["gold"]};font-size:.72rem;letter-spacing:.08em">'
            f'EVERY TONNE, VERIFIED ONCE.</div></div></div>')


def inject():
    st.markdown(f"<style>{CSS}</style>", unsafe_allow_html=True)


def badge(label: str, text: str | None = None) -> str:
    return f'<span class="vq-badge {html.escape(label)}">{html.escape(text or label)}</span>'


def card(inner: str, cls: str = "") -> None:
    st.markdown(f'<div class="vq-card {cls}">{inner}</div>', unsafe_allow_html=True)


def hero(title: str, subtitle: str, tag: str | None = None, live: bool = True) -> None:
    live_html = '<span class="vq-live"><i></i>LIVE</span>' if live else ""
    tag_html = f'<div class="vq-tag">{html.escape(tag)}</div>' if tag else ""
    st.markdown(f'<div class="vq-hero"><div style="display:flex;justify-content:space-between;align-items:flex-start">{tag_html}{live_html}</div>'
                f'<h1>{html.escape(title)}</h1><p>{html.escape(subtitle)}</p></div>', unsafe_allow_html=True)


def page_title(title: str, subtitle: str = "") -> None:
    st.markdown(f'<h2 style="margin-bottom:2px">{html.escape(title)}</h2><div class="vq-sub" style="margin-bottom:16px">{html.escape(subtitle)}</div>',
                unsafe_allow_html=True)


def counters(items: list, height: int = 150) -> None:
    """Row of glass cards whose numbers count up from zero. items: dict(label, value, prefix, suffix, decimals, sub, tone)."""
    payload = json.dumps(items)
    comp = f"""
<style>{FONTS}
body{{margin:0;background:transparent;font-family:Inter,sans-serif;color:{C['text']}}}
.row{{display:grid;grid-template-columns:repeat({len(items)},1fr);gap:14px}}
.c{{background:linear-gradient(145deg,rgba(12,32,25,.85),rgba(12,32,25,.5));border:1px solid rgba(16,185,129,.3);border-radius:16px;padding:16px 18px;
box-shadow:0 10px 34px -14px rgba(16,185,129,.4)}}
.c.gold{{border-color:rgba(245,196,81,.55);box-shadow:0 0 28px -10px rgba(245,196,81,.5)}}
.c.coral{{border-color:rgba(251,113,133,.5)}}
.k{{font-size:.72rem;text-transform:uppercase;letter-spacing:.12em;color:{C['muted']}}}
.v{{font-family:'Space Grotesk',sans-serif;font-size:2rem;font-weight:700;margin:6px 0 2px;white-space:nowrap}}
.s{{font-size:.8rem;color:{C['muted']}}}
.gold .v{{color:{C['gold']}}} .coral .v{{color:{C['coral']}}} .em .v{{color:{C['emerald']}}} .teal .v{{color:{C['teal']}}}
@media(max-width:700px){{.row{{grid-template-columns:1fr 1fr}}}}
</style><div class="row" id="r"></div>
<script>
const items={payload};
const r=document.getElementById('r');
items.forEach((it,i)=>{{
  const d=document.createElement('div'); d.className='c '+(it.tone||'em');
  d.innerHTML='<div class="k">'+it.label+'</div><div class="v" id="v'+i+'">0</div><div class="s">'+(it.sub||'')+'</div>'; r.appendChild(d);
  const el=d.querySelector('.v'), dec=it.decimals||0, t0=performance.now(), dur=1500;
  const fmt=n=>(it.prefix||'')+n.toLocaleString('en-US',{{minimumFractionDigits:dec,maximumFractionDigits:dec}})+(it.suffix||'');
  const step=t=>{{const p=Math.min(1,(t-t0)/dur), e=1-Math.pow(1-p,3); el.textContent=fmt(it.value*e); if(p<1) requestAnimationFrame(step); else el.textContent=fmt(it.value);}};
  requestAnimationFrame(step);
}});
</script>"""
    components.html(comp, height=height)


# ---------------------------------------------------------------------------- plotly
def _template():
    return go.layout.Template(layout=dict(
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family="Inter, sans-serif", color=C["text"]),
        colorway=[C["emerald"], C["teal"], C["gold"], C["coral"], C["amber"], "#A78BFA", "#60A5FA"],
        xaxis=dict(gridcolor="rgba(143,181,163,.12)", zerolinecolor="rgba(143,181,163,.2)", linecolor="rgba(143,181,163,.25)"),
        yaxis=dict(gridcolor="rgba(143,181,163,.12)", zerolinecolor="rgba(143,181,163,.2)", linecolor="rgba(143,181,163,.25)"),
        legend=dict(bgcolor="rgba(0,0,0,0)"), margin=dict(l=10, r=10, t=36, b=10),
        hoverlabel=dict(bgcolor=C["panel"], bordercolor=C["emerald"], font=dict(family="JetBrains Mono, monospace", color=C["text"])),
        title=dict(font=dict(family="Space Grotesk, sans-serif", size=16)),
    ))


pio.templates["verdiq"] = _template()
pio.templates.default = "verdiq"


def style_fig(fig, height: int | None = None):
    fig.update_layout(template="verdiq")
    if height:
        fig.update_layout(height=height)
    return fig


def footer() -> None:
    st.markdown('<div class="vq-foot">VERDIQ · all data in this demo is <b>synthetic</b>; vegetation (NDVI) series are <b>simulated</b>; '
                'company and broker names are fictional. · Every tonne, verified once.</div>', unsafe_allow_html=True)
