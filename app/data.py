"""Cached access to the engine result and chain replay, shared by all pages."""
from __future__ import annotations

import json
import sys
from pathlib import Path

import streamlit as st

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from engine import chain, pipeline  # noqa: E402
from engine.common import OUT  # noqa: E402


@st.cache_resource(show_spinner="Reconciling the ledger…")
def result():
    r = pipeline.run()
    pipeline.write_outputs(r)
    return r


@st.cache_data(show_spinner=False)
def evaluation():
    return pipeline.evaluate(result())


def chain_replay() -> dict | None:
    f = OUT / "chain_replay.json"
    if f.exists():
        try:
            return json.loads(f.read_text(encoding="utf-8"))
        except Exception:
            return None
    return None


def tx_index() -> dict:
    rep = chain_replay()
    return {t["id"]: t for t in rep["txs"]} if rep else {}


def anchor_index() -> dict:
    rep = chain_replay()
    return {a["date"]: a for a in rep["anchors"]} if rep else {}


def impact(asof: str | None = None):
    return pipeline.impact(result(), asof)
