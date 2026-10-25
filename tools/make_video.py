"""Builds the VERDIQ demo video automatically.

  python tools/make_video.py                # everything: narration -> screen recording -> assembly -> QA frames
  python tools/make_video.py --stage narration|record|assemble|qa
  python tools/make_video.py --reuse-recording   # skip re-recording, re-assemble from work/raw.webm

Needs: playwright (+chromium), edge-tts (internet), ffmpeg/ffprobe on PATH (or imageio-ffmpeg), Node for the local chain.
Outputs (docs/demo/): verdiq_demo.mp4, verdiq_demo_silent.mp4, narration.mp3, demo.srt, preview.gif
All data shown is SYNTHETIC; the script says so on screen and in the narration.
"""
from __future__ import annotations

import asyncio
import json
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "app"))

OUT = ROOT / "docs" / "demo"
WORK = OUT / "work"
BASE = "http://localhost:8501"
W, H = 1920, 1080
VOICE = "en-US-AndrewNeural"
RATE = "-3%"
TITLE_S, END_S = 4.0, 7.0
REPO = "https://github.com/shahriarsharif406/verdiq"

# --------------------------------------------------------------------------------------------- narration (mirrors docs/demo_script.md)
SECTIONS = [
    dict(id="s1_problem", text=(
        "Carbon credits only work if one credit means one tonne. Today the same credit can be sold twice, retired twice, "
        "claimed by a host country and a company at once, or never have been issued at all. "
        "Banks solved this a century ago with a daily three-way reconciliation. Carbon markets never did. "
        "This is VERDIQ: every tonne, verified once.")),
    dict(id="s2_results", text=(
        "Everything you will see is synthetic data, generated for this demo, with eight kinds of fraud deliberately injected. "
        "VERDIQ reconciles all six hundred and fifty-three ledger events, and all 8 injected fraud types were detected in our synthetic test, "
        "with no false alarms on the clean trades. "
        "In this market, about fifty-five thousand tonnes of claims would have been counted twice: roughly one and a half million dollars of volume, "
        "the yearly emissions of about twelve thousand cars. "
        "Like a bank balance, every issuance balances to the tonne: issued equals unsold, plus in market, plus retired. "
        "The coral hexagons are tonnes the ledger refused.")),
    dict(id="s3_network", text=(
        "The same eight thousand tonnes circle between three trading desks in three weeks while the price doubles. That is a wash-trading loop. "
        "Select a node, and you get every flag with its rule, severity and evidence. Coral lines mark flows that broke a rule, and the node size shows how many tonnes it traded. "
        "The Time Machine replays the market month by month. Fraud events pop in at the moment they occur, "
        "and the protected-tonnes curve steps up.")),
    dict(id="s4_projects", text=(
        "Two Sundarbans projects claim thirty-one percent of the same mangrove polygon, and a Cusco project claims one hundred seventy-three tonnes per hectare "
        "where the physical ceiling is forty. Every project gets a zero to one hundred trust score, with a plain-English reason. "
        "The vegetation series here is simulated, and labelled as such. "
        "Now greenwashing. Meridian Airways, a fictional company, told the press it offset four hundred thousand tonnes. "
        "The ledger shows about one hundred twenty-six thousand validly retired, and only about one hundred thirteen thousand from credits with no integrity flags. "
        "Roughly twenty-eight percent of the claim is backed.")),
    dict(id="s5_attack", text=(
        "Now the part that matters. A fraudster tries to double-count credits, live. "
        "That was a real transaction against our Solidity registry on a local test chain. The contract reverted it with a reason code, "
        "and here is the transaction hash, in about two seconds. "
        "Independently, the reconciliation engine flagged it, with the rule and the evidence. "
        "Without VERDIQ, these tonnes would have been counted twice. "
        "Again: a double sale. And a double retirement. "
        "Every attempt is blocked, counted, and added to the impact total. "
        "The log shows who tried it, how many tonnes were at stake, the reason code, and the transaction that carried the revert.")),
    dict(id="s6_proof", text=(
        "Banks close the day. Now carbon markets do too: every month-end snapshot is a Merkle root anchored on-chain. "
        "Pick any serial and prove it with a handful of hashes, without seeing the dataset. Watch what happens when one field of the record is tampered with: the proof fails, and the original verifies again. "
        "Every credit range also gets a passport, with its timeline, owner chain, trust score, Merkle proof, "
        "and the transaction hash of any blocked sale. "
        "The QR code opens a public page with no login, so a buyer, a journalist or a regulator can verify a credit in seconds.")),
    dict(id="s7_close", text=(
        "VERDIQ turns carbon credits from promises into audited facts: reconciled daily, blocked on a chain, and verifiable by anyone, "
        "in Bangla and in English. "
        "All data in this demo is synthetic, the vegetation signal is simulated, and we claim no partnership with any registry or company. "
        "Every tonne, verified once.")),
]


def ff(name="ffmpeg") -> str:
    p = shutil.which(name)
    if p:
        return p
    if name == "ffmpeg":
        import imageio_ffmpeg
        return imageio_ffmpeg.get_ffmpeg_exe()
    raise SystemExit(f"{name} not found")


def run(cmd, **kw):
    r = subprocess.run([str(c) for c in cmd], capture_output=True, text=True, **kw)
    if r.returncode:
        print(r.stderr[-1500:])
        raise SystemExit(f"command failed: {cmd[:3]}")
    return r


def dur(path) -> float:
    try:
        from mutagen import File
        return File(str(path)).info.length
    except Exception:
        r = run([ff("ffprobe") if shutil.which("ffprobe") else ff(), "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", path])
        return float(r.stdout.strip())


# --------------------------------------------------------------------------------------------- stage 1: narration
def stage_narration():
    import edge_tts
    WORK.mkdir(parents=True, exist_ok=True)

    async def go():
        for s in SECTIONS:
            f = WORK / f"{s['id']}.mp3"
            await edge_tts.Communicate(s["text"], VOICE, rate=RATE).save(str(f))
    asyncio.run(go())
    info = {s["id"]: dur(WORK / f"{s['id']}.mp3") for s in SECTIONS}
    (WORK / "narration_durations.json").write_text(json.dumps(info, indent=1))
    print("narration seconds:", {k: round(v, 1) for k, v in info.items()}, "total", round(sum(info.values()), 1))
    return info


# --------------------------------------------------------------------------------------------- stage 2: screen recording
INIT_JS = """
(() => {
  if (window.__vq) return; window.__vq = true;
  const mk = () => {
    if (document.getElementById('vq-cursor')) return;
    const c = document.createElement('div'); c.id = 'vq-cursor';
    c.style.cssText = 'position:fixed;z-index:2147483647;width:30px;height:30px;border-radius:50%;border:3px solid #F5C451;background:rgba(245,196,81,.28);'
      + 'pointer-events:none;transform:translate(-50%,-50%);left:-80px;top:-80px;box-shadow:0 0 22px rgba(245,196,81,.9)';
    document.body.appendChild(c);
    const st = document.createElement('style');
    st.textContent = '@keyframes vqhl{0%{box-shadow:0 0 0 0 rgba(245,196,81,.75)}100%{box-shadow:0 0 0 22px rgba(245,196,81,0)}}';
    document.head.appendChild(st);
    document.addEventListener('mousemove', e => { c.style.left = e.clientX + 'px'; c.style.top = e.clientY + 'px'; }, true);
  };
  if (document.body) mk(); else document.addEventListener('DOMContentLoaded', mk);
})();
"""


class Driver:
    def __init__(self, page):
        self.p = page
        self.mx, self.my = 960, 540
        self.t0 = time.time()

    # ---- timing inside a section
    def start(self, budget):
        self.t0, self.budget = time.time(), budget

    def at(self, frac):
        wait = self.t0 + frac * self.budget - time.time()
        if wait > 0:
            time.sleep(wait)

    def elapsed(self):
        return time.time() - self.t0

    # ---- motion
    def glide(self, x, y, ms=520):
        n = 28
        for i in range(1, n + 1):
            k = i / n
            e = k * k * (3 - 2 * k)
            self.p.mouse.move(self.mx + (x - self.mx) * e, self.my + (y - self.my) * e)
            time.sleep(ms / 1000 / n)
        self.mx, self.my = x, y

    def box(self, loc):
        loc.first.wait_for(state="attached", timeout=45000)
        loc.first.scroll_into_view_if_needed(timeout=15000)
        return loc.first.bounding_box()

    def hl(self, loc, secs=2.0, pad=8, move=True):
        b = self.box(loc)
        if not b:
            return
        if move:
            self.glide(b["x"] + min(b["width"] / 2, 400), b["y"] + min(b["height"] / 2, 200))
        self.p.evaluate("""([x,y,w,h]) => { let d=document.getElementById('vq-hl'); if(d) d.remove();
            d=document.createElement('div'); d.id='vq-hl';
            d.style.cssText=`position:fixed;left:${x}px;top:${y}px;width:${w}px;height:${h}px;border:3px solid #F5C451;border-radius:14px;z-index:2147483646;pointer-events:none;animation:vqhl 1.1s infinite`;
            document.body.appendChild(d);}""", [b["x"] - pad, b["y"] - pad, b["width"] + 2 * pad, b["height"] + 2 * pad])
        time.sleep(secs)
        self.p.evaluate("() => { const d=document.getElementById('vq-hl'); if(d) d.remove(); }")

    def click(self, loc, hl=0.5):
        b = self.box(loc)
        self.glide(b["x"] + b["width"] / 2, b["y"] + b["height"] / 2)
        self.p.evaluate("""([x,y,w,h]) => { let d=document.getElementById('vq-hl'); if(d) d.remove();
            d=document.createElement('div'); d.id='vq-hl';
            d.style.cssText=`position:fixed;left:${x}px;top:${y}px;width:${w}px;height:${h}px;border:3px solid #F5C451;border-radius:14px;z-index:2147483646;pointer-events:none;animation:vqhl 1.1s infinite`;
            document.body.appendChild(d);}""", [b["x"] - 6, b["y"] - 6, b["width"] + 12, b["height"] + 12])
        time.sleep(hl)
        loc.first.click()
        self.p.evaluate("() => { const d=document.getElementById('vq-hl'); if(d) d.remove(); }")

    def scroll(self, dy, secs=3.0):
        self.p.evaluate("""async ([dy, ms]) => { const el = document.querySelector('[data-testid="stMain"]') || document.scrollingElement;
            const t0 = performance.now(), y0 = el.scrollTop;
            await new Promise(r => { const f = t => { const p = Math.min(1, (t - t0) / ms), e = p < .5 ? 2*p*p : 1 - Math.pow(-2*p + 2, 2) / 2;
              el.scrollTop = y0 + dy * e; p < 1 ? requestAnimationFrame(f) : r(); }; requestAnimationFrame(f); }); }""", [dy, secs * 1000])

    def top(self, secs=1.2):
        self.p.evaluate("""async (ms) => { const el = document.querySelector('[data-testid="stMain"]') || document.scrollingElement;
            const t0=performance.now(), y0=el.scrollTop; await new Promise(r=>{const f=t=>{const p=Math.min(1,(t-t0)/ms); el.scrollTop=y0*(1-p); p<1?requestAnimationFrame(f):r()}; requestAnimationFrame(f)});}""", secs * 1000)

    def ready(self, extra=2.5, title=None, plot=False):
        """Wait until the page is really rendered: no running-status widget, nothing stale, the page heading visible, main area filled."""
        time.sleep(0.8)
        try:
            self.p.wait_for_function("() => !document.querySelector('[data-testid=\"stStatusWidget\"]')", timeout=60000)
        except Exception:
            pass
        if title:
            self.p.locator('[data-testid="stMain"] h2').filter(has_text=re.compile("^\s*" + re.escape(title), re.I)).first.wait_for(state="visible", timeout=60000)
        try:
            self.p.wait_for_function("""() => { const m = document.querySelector('[data-testid="stMain"]');
                return m && !m.querySelector('[data-stale="true"]') && m.innerText.trim().length > 150 && m.scrollHeight > 500; }""", timeout=60000)
            if plot:
                self.p.wait_for_function("() => document.querySelectorAll('[data-testid=\"stPlotlyChart\"] .main-svg').length > 0", timeout=60000)
        except Exception:
            pass
        time.sleep(extra)

    TITLES = {"Reconciliation": "Three-way", "Map & Forest Health": "Project map", "Trust Scores": "Trust scores", "Fraud Network": "Fraud network",
              "Time Machine": "Time machine", "Greenwashing Checker": "Greenwashing", "Attack Mode": "Attack Mode",
              "Day-End Close & Verify": "Day-End Close", "Tonne Passport": "Tonne Passport"}

    def nav(self, name, extra=2.0):
        self.click(self.p.locator('[data-testid="stSidebarNavLink"]').filter(has_text=name), hl=0.4)
        self.ready(extra, title=self.TITLES.get(name), plot=name in ("Reconciliation", "Map & Forest Health", "Trust Scores", "Fraud Network", "Time Machine", "Greenwashing Checker"))

    def check(self, label):
        bad = self.p.locator('[data-testid="stException"]').count()
        body = self.p.inner_text("body")
        if bad or "Traceback" in body:
            self.p.screenshot(path=str(WORK / f"ERR_{label}.png"))
            raise SystemExit(f"error text on screen during {label}")


def hashes(p):
    return p.evaluate("() => [...document.querySelectorAll('.vq-hash')].map(e=>e.textContent).join('|')")


def launch(d: Driver, kind=None):
    p = d.p
    if kind:
        d.click(p.get_by_text(kind, exact=True), hl=0.3)
        time.sleep(1.5)
    before = hashes(p)
    print(f"    launching at +{d.elapsed():.1f}s")
    d.click(p.get_by_role("button", name=re.compile("LAUNCH ATTACK")), hl=0.4)
    p.wait_for_function("b => [...document.querySelectorAll('.vq-hash')].map(e=>e.textContent).join('|') !== b", arg=before, timeout=90000)
    p.wait_for_selector(".vq-stamp", timeout=30000)
    print(f"    attack done at +{d.elapsed():.1f}s")
    time.sleep(1.0)


def record(info: dict):
    from playwright.sync_api import sync_playwright
    from engine import chain
    import urllib.request

    started = []
    try:
        urllib.request.urlopen(BASE, timeout=2)
    except Exception:
        print("starting dashboard…")
        started.append(subprocess.Popen([sys.executable, "-m", "streamlit", "run", "app/streamlit_app.py", "--server.port", "8501"], cwd=ROOT,
                                        stdout=open(WORK / "streamlit.log", "w"), stderr=subprocess.STDOUT))
        for _ in range(60):
            try:
                urllib.request.urlopen(BASE, timeout=2)
                break
            except Exception:
                time.sleep(1)
    print("warming the local chain…")
    if not chain.ensure_chain(print):
        raise SystemExit("local chain could not be started: Attack Mode would fall back to the Python mirror")

    import pandas as pd
    ev = pd.read_csv(ROOT / "data" / "out" / "reconciliation_events.csv")
    t9 = ev[ev.event_id == "T9001"].iloc[0]
    pass_url = f"{BASE}/?passport={int(t9.serial_start)}-{int(t9.serial_end)}"

    pages = ["", "reconciliation", "fraud_network", "time_machine", "map", "trust_scores", "greenwashing", "attack_mode", "day_end_close", "tonne_passport"]
    marks = []
    with sync_playwright() as pw:
        b = pw.chromium.launch(args=["--force-device-scale-factor=1"])
        warm = b.new_page(viewport={"width": W, "height": H})
        for s in pages:                       # warm caches (engine result, fonts, plots) so nothing is slow on camera
            warm.goto(f"{BASE}/{s}")
            warm.wait_for_selector('[data-testid="stApp"]')
            time.sleep(3)
        warm.goto(f"{BASE}/attack_mode"); time.sleep(3)
        warm.get_by_role("button", name=re.compile("LAUNCH ATTACK")).click()
        warm.wait_for_selector(".vq-stamp", timeout=90000)
        warm.close()

        ctx = b.new_context(viewport={"width": W, "height": H}, record_video_dir=str(WORK / "vid"), record_video_size={"width": W, "height": H})
        ctx.add_init_script(INIT_JS)
        page = ctx.new_page()
        t_page = time.time()
        d = Driver(page)
        page.goto(BASE)
        d.ready(4)

        def section(i, fn, pre=None):
            if pre:                                   # navigate and fully render the page BEFORE the section's narration/recording window opens
                time.sleep(0.7)                       # previous section's cut ends before this click
                d.nav(pre, 2.0)
            s = SECTIONS[i]
            budget = info[s["id"]]
            off = time.time() - t_page
            d.start(budget)
            fn(d, budget)
            d.check(s["id"])
            used = d.elapsed()
            marks.append(dict(id=s["id"], offset=off, used=used, audio=budget))
            print(f"  {s['id']}: audio {budget:.1f}s, actions {used:.1f}s")

        # ---- S1: problem, Overview
        def s1(d, B):
            d.hl(page.locator("iframe").first, 2.2)
            d.at(.45); d.hl(page.locator('[data-testid="stMetric"]').first, 1.8)
            d.at(.65); d.scroll(520, 3.5)
            d.at(.97)
        section(0, s1)

        # ---- S2: results + reconciliation
        def s2(d, B):
            d.top(0.8)
            d.hl(page.locator("iframe").first, 2.0)
            d.at(.30); d.nav("Reconciliation", 1.5)
            d.at(.45); d.hl(page.locator('[data-testid="stPlotlyChart"]').first, 2.5)
            d.at(.70); d.scroll(500, 3.0)
            d.at(.97)
        section(1, s2)

        # ---- S3: network + time machine
        def s3(d, B):
            d.hl(page.locator('[data-testid="stPlotlyChart"]').first, 1.8)
            sel = page.locator('[data-testid="stSelectbox"]').first
            d.click(sel, hl=0.2)
            page.keyboard.type("Tidewater", delay=50); time.sleep(0.4); page.keyboard.press("Enter")
            d.ready(1.2)
            d.scroll(420, 2.0)
            d.at(.50); d.nav("Time Machine", 3.0)
            sl = page.locator('[data-testid="stSlider"] input[type="range"]').first
            d.hl(page.locator('[data-testid="stSlider"]').first, 0.8)
            sl.focus(); page.keyboard.press("Home"); d.ready(2.0)
            d.click(page.get_by_role("button", name=re.compile("Play")), hl=0.2)
        section(2, s3, pre="Fraud Network")

        # ---- S4: map / trust / greenwashing
        def s4(d, B):
            d.hl(page.locator('[data-testid="stPlotlyChart"]').first, 1.5)
            d.scroll(820, 2.8)
            d.at(.34); d.nav("Trust Scores", 2.0)
            d.hl(page.locator('[data-testid="stPlotlyChart"]').first, 1.8)
            d.scroll(420, 2.2)
            d.at(.56); d.nav("Greenwashing Checker", 2.5)
            d.hl(page.locator('[data-testid="stPlotlyChart"]').first, 2.2)
            d.at(.80); d.hl(page.locator(".vq-card").first, 2.5)
            d.scroll(400, 2.5)
        section(3, s4, pre="Map & Forest Health")

        # ---- S5: attack mode (climax)
        def s5(d, B):
            d.hl(page.locator(".vq-badge").first, 1.5)
            d.at(.08); launch(d)
            d.hl(page.locator(".vq-stamp").first, 2.2)
            d.scroll(430, 2.4)
            d.hl(page.locator(".vq-hash").first, 1.6)
            d.at(.55); d.top(0.8); launch(d, "Double sale")
            d.hl(page.locator(".vq-stamp").first, 1.2)
            d.at(.78); d.top(0.5); launch(d, "Double retirement")
            d.hl(page.locator(".vq-stamp").first, 1.0)
            d.scroll(900, 2.5)
        section(4, s5, pre="Attack Mode")

        # ---- S6: close, verify, passport
        def s6(d, B):
            d.hl(page.locator(".vq-card").first, 2.2)
            d.scroll(520, 2.2)
            d.at(.24)
            d.click(page.get_by_text("Tamper with the record"), hl=0.2); d.ready(1.2)
            d.hl(page.locator(".vq-badge").last, 1.6)
            d.click(page.get_by_text("Tamper with the record"), hl=0.2); d.ready(1.0)
            d.at(.48); d.nav("Tonne Passport", 2.0)
            d.click(page.get_by_text("Double-sold range", exact=False).first, hl=0.2); d.ready(1.5)
            d.hl(page.locator(".vq-passport").first, 2.2)
            d.scroll(560, 2.4)
            d.at(.80)
            page.goto(pass_url); d.ready(3.0); page.locator(".vq-passport").first.wait_for(state="visible", timeout=60000)
            d.hl(page.locator(".vq-passport").first, 2.0)
        section(5, s6, pre="Day-End Close & Verify")

        # ---- S7: close
        def s7(d, B):
            page.goto(BASE); d.ready(3.0, title="")
            d.hl(page.locator("iframe").first, 2.0)
            d.at(.50); d.click(page.get_by_text("বাংলা").first, hl=0.2); d.ready(2.0)
            d.at(.80); d.click(page.get_by_text("English", exact=True).first, hl=0.2); d.ready(1.5)
        section(6, s7)

        time.sleep(1.0)
        vpath = page.video.path()
        ctx.close()
        b.close()
    for pr in started:
        pr.terminate()
    shutil.copy(vpath, WORK / "raw.webm")
    (WORK / "marks.json").write_text(json.dumps(marks, indent=1))
    print("recorded", WORK / "raw.webm")


# --------------------------------------------------------------------------------------------- stage 3: assembly
def card_png(path: Path, kind: str):
    from playwright.sync_api import sync_playwright
    import theme
    logo = theme.logo_svg(230)
    if kind == "title":
        body = ("<h1>VERDIQ</h1><h2>Every tonne, verified once.</h2>"
                "<p>Three-way carbon-credit reconciliation · blockchain double-counting firewall · public Tonne Passport</p>"
                "<small>Demo on 100% synthetic data</small>")
    else:
        body = (f"<h1>VERDIQ</h1><h2>Every tonne, verified once.</h2><div class='url'>{REPO}</div>"
                "<p>IEEE ClimateChain Global Hackathon · Track: Carbon Markets &amp; Emissions Transparency</p>"
                "<small>All data synthetic · NDVI series simulated · no real registry, company or government is involved</small>")
    html = f"""<html><head><style>
    @import url('https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@500;700&family=Inter:wght@400;500&family=JetBrains+Mono&display=swap');
    body{{margin:0;width:{W}px;height:{H}px;display:flex;align-items:center;justify-content:center;color:#E7F5EE;font-family:Inter,sans-serif;
    background:radial-gradient(900px 500px at 85% 0%,rgba(45,212,191,.28),transparent 60%),radial-gradient(900px 600px at 0% 100%,rgba(16,185,129,.22),transparent 60%),#06130F;overflow:hidden}}
    .c{{text-align:center}} h1{{font-family:'Space Grotesk';font-size:150px;letter-spacing:14px;margin:24px 0 0;font-weight:700}}
    h2{{font-family:'Space Grotesk';font-size:52px;color:#F5C451;margin:6px 0 30px;font-weight:500;letter-spacing:2px}}
    p{{font-size:30px;color:#8FB5A3;margin:8px 0}} small{{font-size:24px;color:#8FB5A3;opacity:.8}}
    .url{{font-family:'JetBrains Mono',monospace;font-size:46px;color:#2DD4BF;margin:10px 0 26px}}
    </style></head><body><div class="c">{logo}{body}</div></body></html>"""
    with sync_playwright() as pw:
        b = pw.chromium.launch()
        pg = b.new_page(viewport={"width": W, "height": H})
        pg.set_content(html)
        time.sleep(2.0)
        pg.screenshot(path=str(path))
        b.close()


def srt_time(t):
    ms = int(round(t * 1000))
    return f"{ms//3600000:02d}:{ms//60000%60:02d}:{ms//1000%60:02d},{ms%1000:03d}"


def wrap(text, width=58):
    words, lines, cur = text.split(), [], ""
    for w in words:
        if len(cur) + len(w) + 1 > width and cur:
            lines.append(cur); cur = w
        else:
            cur = (cur + " " + w).strip()
    lines.append(cur)
    return "\n".join(lines)


def chunks(text, limit=105):
    out = []
    for s in re.split(r"(?<=[.!?:])\s+", text.strip()):
        parts = [s]
        while len(parts[-1]) > limit:
            long = parts.pop()
            mid = len(long) // 2
            cut = min([m.end() for m in re.finditer(r",\s|\sand\s|\swhile\s|\swhere\s", long)] or [mid], key=lambda k: abs(k - mid))
            parts += [long[:cut].strip(), long[cut:].strip()]
        out += parts
    return out



def blank_intervals(video: Path, step: float = 0.1):
    """[(t0, t1)] where the main area (right of the sidebar) is empty: a page that is still loading."""
    import numpy as np
    from PIL import Image
    d = WORK / "blank_scan"
    shutil.rmtree(d, ignore_errors=True)
    d.mkdir(parents=True)
    run([ff(), "-y", "-i", video, "-vf", f"fps={1 / step},crop=1500:900:380:60,scale=150:90", d / "b_%05d.png"])
    out, cur = [], None
    for i, f in enumerate(sorted(d.glob("b_*.png"))):
        a = np.asarray(Image.open(f).convert("L"), dtype=float)
        blank = (a > 50).mean() < 0.004
        t = i * step
        if blank and cur is None:
            cur = t
        elif not blank and cur is not None:
            out.append((cur, t))
            cur = None
    if cur is not None:
        out.append((cur, len(list(d.glob("b_*.png"))) * step))
    return out


def freeze_blanks(raw: Path) -> Path:
    """Replace every blank (loading) interval of the recording with the last good frame, keeping the timeline (and so the narration sync) intact."""
    iv = [(a, b) for a, b in blank_intervals(raw) if a > 0.3]
    fixed = WORK / "raw_fixed.mp4"
    print(f"blank intervals frozen: {[(round(a, 1), round(b, 1)) for a, b in iv] or 'none'}")
    vf = f"scale={W}:{H}:flags=lanczos,fps=30,format=yuv420p"
    if not iv:
        run([ff(), "-y", "-i", raw, "-vf", vf, "-c:v", "libx264", "-preset", "fast", "-crf", "14", "-an", fixed])
        return fixed
    inputs, chain, last = [], [], "[0:v]"
    cmd = [ff(), "-y", "-i", raw]
    for k, (a, b) in enumerate(iv):
        png = WORK / f"freeze_{k}.png"
        run([ff(), "-y", "-ss", f"{max(0.0, a - 0.15):.2f}", "-i", raw, "-frames:v", "1", "-vf", f"scale={W}:{H}", png])
        cmd += ["-i", png]
        chain.append(f"{last}[{k + 1}:v]overlay=0:0:enable='between(t,{a:.2f},{b:.2f})'[v{k}]")
        last = f"[v{k}]"
    fc = ";".join(chain) + f";{last}{vf}[out]"
    run(cmd + ["-filter_complex", fc, "-map", "[out]", "-c:v", "libx264", "-preset", "fast", "-crf", "14", "-an", fixed])
    return fixed


def stage_assemble(info: dict):
    marks = json.loads((WORK / "marks.json").read_text())
    FF = ff()
    raw = freeze_blanks(WORK / "raw.webm")
    segs, srt, t_cursor, cues = [], [], TITLE_S, 1
    vf = f"scale={W}:{H}:flags=lanczos,fps=30,format=yuv420p"
    enc = ["-c:v", "libx264", "-preset", "medium", "-crf", "17", "-pix_fmt", "yuv420p", "-r", "30", "-an"]

    card_png(WORK / "title.png", "title")
    card_png(WORK / "end.png", "end")
    for name, secs in (("title", TITLE_S), ("end", END_S)):
        run([FF, "-y", "-loop", "1", "-i", WORK / f"{name}.png", "-t", secs, "-vf",
             f"fps=30,format=yuv420p,fade=t=in:st=0:d=0.7,fade=t=out:st={secs-0.7}:d=0.7"] + enc + [WORK / f"{name}.mp4"])

    audio_parts = []
    run([FF, "-y", "-f", "lavfi", "-i", "anullsrc=r=44100:cl=mono", "-t", TITLE_S, WORK / "sil_title.wav"])
    audio_parts.append(WORK / "sil_title.wav")
    for m in marks:
        sid = m["id"]
        a = info[sid]
        D = max(a + 0.6, m["used"] + 0.3)
        # video: cut [offset, offset+D] from the recording
        run([FF, "-y", "-ss", f"{m['offset']:.3f}", "-t", f"{D:.3f}", "-i", raw, "-vf", vf] + enc + [WORK / f"{sid}.mp4"])
        run([FF, "-y", "-i", WORK / f"{sid}.mp3", "-af", f"apad=whole_dur={D:.3f},aresample=44100", "-ac", "1", "-t", f"{D:.3f}", WORK / f"{sid}.wav"])
        audio_parts.append(WORK / f"{sid}.wav")
        segs.append(WORK / f"{sid}.mp4")
        # subtitles: cue timing proportional to characters inside the audio clip
        text = next(s["text"] for s in SECTIONS if s["id"] == sid)
        cs = chunks(text)
        total = sum(len(c) for c in cs)
        t = t_cursor + 0.15
        for c in cs:
            span = (a - 0.2) * len(c) / total
            srt.append(f"{cues}\n{srt_time(t)} --> {srt_time(t + span - 0.04)}\n{wrap(c)}\n")
            cues += 1
            t += span
        t_cursor += D
    run([FF, "-y", "-f", "lavfi", "-i", "anullsrc=r=44100:cl=mono", "-t", END_S, WORK / "sil_end.wav"])
    audio_parts.append(WORK / "sil_end.wav")
    total_len = t_cursor + END_S
    (OUT / "demo.srt").write_text("\n".join(srt), encoding="utf-8")

    # video concat
    lst = WORK / "v.txt"
    lst.write_text("\n".join(f"file '{p.name}'" for p in [WORK / "title.mp4"] + segs + [WORK / "end.mp4"]))
    run([FF, "-y", "-f", "concat", "-safe", "0", "-i", lst, "-c", "copy", WORK / "silent_nosubs.mp4"], cwd=WORK)
    # audio concat -> narration
    alst = WORK / "a.txt"
    alst.write_text("\n".join(f"file '{p.name}'" for p in audio_parts))
    run([FF, "-y", "-f", "concat", "-safe", "0", "-i", alst, "-c", "copy", WORK / "narration_full.wav"], cwd=WORK)
    run([FF, "-y", "-i", WORK / "narration_full.wav", "-codec:a", "libmp3lame", "-b:a", "160k", OUT / "narration.mp3"])
    # silent deliverable (no audio, no burned subs) so the author can record their own voice
    shutil.copy(WORK / "silent_nosubs.mp4", OUT / "verdiq_demo_silent.mp4")
    # final: burned subtitles + narration
    shutil.copy(OUT / "demo.srt", WORK / "demo.srt")
    style = "FontName=Arial,FontSize=22,PrimaryColour=&H00FFFFFF,OutlineColour=&H00152008,BackColour=&H80000000,BorderStyle=1,Outline=2,Shadow=1,MarginV=38,Bold=1"
    run([FF, "-y", "-i", WORK / "silent_nosubs.mp4", "-i", WORK / "narration_full.wav", "-vf", f"subtitles=demo.srt:force_style='{style}'",
         "-c:v", "libx264", "-preset", "medium", "-crf", "19", "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "160k", "-movflags", "+faststart",
         "-shortest", "-metadata", "title=VERDIQ demo", OUT / "verdiq_demo.mp4"], cwd=WORK)
    # preview gif of the attack section
    atk = next(m for m in marks if m["id"] == "s5_attack")
    start_attack = TITLE_S + sum(max(info[x["id"]] + 0.6, x["used"] + 0.3) for x in marks[:4])
    run([FF, "-y", "-ss", f"{start_attack + 6:.1f}", "-t", "9", "-i", OUT / "verdiq_demo.mp4", "-vf",
         "fps=8,scale=800:-1:flags=lanczos,split[a][b];[a]palettegen=max_colors=96[p];[b][p]paletteuse=dither=bayer", OUT / "preview.gif"])
    print(f"video length ~ {total_len:.1f}s -> {OUT/'verdiq_demo.mp4'} ({(OUT/'verdiq_demo.mp4').stat().st_size/1e6:.1f} MB)")


# --------------------------------------------------------------------------------------------- stage 4: QA
def stage_qa():
    from PIL import Image, ImageStat
    FF = ff()
    q = WORK / "qa"
    shutil.rmtree(q, ignore_errors=True)
    q.mkdir(parents=True)
    video = OUT / "verdiq_demo.mp4"
    run([FF, "-y", "-i", video, "-vf", "fps=1/5,scale=640:-1", q / "f_%03d.png"])
    frames = sorted(q.glob("f_*.png"))
    bad = []
    for f in frames:
        im = Image.open(f).convert("L")
        sd = ImageStat.Stat(im).stddev[0]
        mean = ImageStat.Stat(im).mean[0]
        if sd < 6 or mean > 235:
            bad.append((f.name, round(sd, 1)))
    # contact sheets for eyeballing
    per = 12
    for i in range(0, len(frames), per):
        grp = frames[i:i + per]
        sheet = Image.new("RGB", (640 * 3, 360 * 4), "black")
        for k, f in enumerate(grp):
            sheet.paste(Image.open(f).resize((640, 360)), ((k % 3) * 640, (k // 3) * 360))
        sheet.save(q / f"sheet_{i // per + 1}.png")
    vd = dur(video)
    ad = dur(OUT / "narration.mp3")
    r = run([ff("ffprobe") if shutil.which("ffprobe") else FF, "-v", "error", "-select_streams", "a:0", "-show_entries", "stream=duration", "-of", "csv=p=0", video])
    print(f"video {vd:.1f}s | narration.mp3 {ad:.1f}s | audio stream in mp4 {float(r.stdout.strip()):.1f}s | size {video.stat().st_size/1e6:.1f} MB")
    print(f"frames checked: {len(frames)}; suspicious (blank/flat) frames: {bad or 'none'}")
    assert 210 <= vd <= 285, "video length outside 3:30-4:30"
    assert abs(vd - ad) < 1.0, "audio and video duration differ"
    assert video.stat().st_size < 200e6
    # a single flat frame is a ~0.5 s page-navigation flash (checked by hand at 4 fps); only consecutive flat samples fail
    idx = [int(n[2:5]) for n, _ in bad]
    empty = blank_intervals(OUT / "verdiq_demo_silent.mp4", 0.1)
    print(f"empty-main-area intervals in the final video: {[(round(a, 1), round(b, 1)) for a, b in empty] or 'none'}")
    assert not empty, "empty main area (loading page) visible in the final video"
    assert not any(b - a == 1 for a, b in zip(idx, idx[1:])), "blank frames found"


def main():
    args = sys.argv[1:]
    stage = args[args.index("--stage") + 1] if "--stage" in args else "all"
    WORK.mkdir(parents=True, exist_ok=True)
    OUT.mkdir(parents=True, exist_ok=True)
    f = WORK / "narration_durations.json"
    if stage in ("all", "narration") or not f.exists():
        info = stage_narration()
    else:
        info = json.loads(f.read_text())
    if stage in ("all", "record") and "--reuse-recording" not in args:
        record(info)
    if stage in ("all", "assemble"):
        stage_assemble(info)
    if stage in ("all", "qa"):
        stage_qa()


if __name__ == "__main__":
    main()
