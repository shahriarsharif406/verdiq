"""Cross-platform task runner (the Makefile just calls this).   python verdiq.py <task>

  setup    install Python + Node dependencies
  data     generate synthetic data + run the engine (writes data/out/*)
  test     engine tests (pytest) + smart-contract tests (Hardhat)
  replay   replay the ledger on an in-process Hardhat chain, anchor all Day-End Closes
  chain    boot a persistent local node + replay (what Attack Mode uses)
  run      start the dashboard on http://localhost:8501
  shots    capture screenshots of every page (needs a running dashboard and `playwright install chromium`)
  all      setup + data + test + replay
"""
from __future__ import annotations

import os
import shutil
import subprocess
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))
NPX = shutil.which("npx") or shutil.which("npx.cmd") or "npx"
NPM = shutil.which("npm") or shutil.which("npm.cmd") or "npm"
PY = sys.executable


def sh(*cmd, env=None):
    print("$", " ".join(cmd), flush=True)
    r = subprocess.run(cmd, cwd=ROOT, env=dict(os.environ, **(env or {})))
    if r.returncode:
        sys.exit(r.returncode)


def setup():
    sh(PY, "-m", "pip", "install", "-r", "requirements.txt")
    sh(NPM, "install")


def data():
    sh(PY, "data/generate.py")
    sh(PY, "-m", "engine.pipeline")


def test():
    sh(PY, "-m", "pytest", "-q", "tests")
    sh(NPX, "hardhat", "test")


def replay():
    sh(NPX, "hardhat", "run", "scripts/replay.js", env={"VERDIQ_REPLAY": "1"})


def chain():
    sys.path.insert(0, ROOT)
    from engine import chain as c
    ok = c.ensure_chain()
    print("local chain ready" if ok else "could not start the local chain (Attack Mode will use the Python mirror)")


def run():
    if not os.path.exists(os.path.join(ROOT, "data", "out", "reconciliation_events.csv")):
        data()
    sh(PY, "-m", "streamlit", "run", "app/streamlit_app.py", "--server.port", "8501")


def shots():
    sh(PY, "scripts/smoke.py", "--shots")


TASKS = dict(setup=setup, data=data, test=test, replay=replay, chain=chain, run=run, shots=shots)

if __name__ == "__main__":
    if len(sys.argv) < 2 or sys.argv[1] not in (*TASKS, "all"):
        print(__doc__)
        sys.exit(1)
    for name in (["setup", "data", "test", "replay"] if sys.argv[1] == "all" else [sys.argv[1]]):
        TASKS[name]()
