"""Smoke-test every dashboard page with a real browser (Playwright) and optionally capture screenshots.

  python scripts/smoke.py                 # check that every page renders without an exception
  python scripts/smoke.py --shots         # also write docs/screenshots/*.png (1920x1080)
"""
from __future__ import annotations

import sys
import time
from pathlib import Path

from playwright.sync_api import sync_playwright

BASE = "http://localhost:8501"
ROOT = Path(__file__).resolve().parent.parent
PAGES = [("overview", ""), ("reconciliation", "reconciliation"), ("map", "map"), ("trust_scores", "trust_scores"), ("fraud_network", "fraud_network"),
         ("time_machine", "time_machine"), ("pre_purchase", "pre_purchase"), ("greenwashing", "greenwashing"), ("attack_mode", "attack_mode"),
         ("day_end_close", "day_end_close"), ("tonne_passport", "tonne_passport"), ("case_files", "case_files")]
PAGE_PATH = {"reconciliation": "02_reconciliation"}


def check(page, name, wait=4.0):
    page.wait_for_selector('[data-testid="stApp"]', timeout=60000)
    time.sleep(wait)
    errs = page.locator('[data-testid="stException"]').count()
    body = page.inner_text("body")
    bad = errs or "Traceback" in body
    return not bad, body


def main():
    shots = "--shots" in sys.argv
    out = ROOT / "docs" / "screenshots"
    out.mkdir(parents=True, exist_ok=True)
    fails = []
    with sync_playwright() as p:
        b = p.chromium.launch()
        pg = b.new_page(viewport={"width": 1920, "height": 1080})
        for name, path in PAGES:
            pg.goto(f"{BASE}/{path}", wait_until="domcontentloaded")
            ok, body = check(pg, name, 12 if name == "map" else 7 if name in ("overview", "time_machine", "fraud_network") else 4)
            if name == "attack_mode" and ok:
                pg.get_by_role("button", name="LAUNCH ATTACK").click()
                try:
                    pg.wait_for_selector(".vq-stamp", timeout=150000)
                    time.sleep(2.5)
                except Exception:
                    ok = False
                ok = ok and pg.locator('[data-testid="stException"]').count() == 0
            print(("OK  " if ok else "FAIL"), name)
            if not ok:
                fails.append(name)
                pg.screenshot(path=str(out / f"_fail_{name}.png"))
            elif shots:
                pg.screenshot(path=str(out / f"{name}.png"))
        pg.goto(f"{BASE}/?passport=2507189-2508936", wait_until="domcontentloaded")
        ok, _ = check(pg, "public_passport", 6)
        print(("OK  " if ok else "FAIL"), "public passport route")
        if shots and ok:
            pg.screenshot(path=str(out / "public_passport.png"))
        if not ok:
            fails.append("passport")
        b.close()
    sys.exit(1 if fails else 0)


if __name__ == "__main__":
    main()
