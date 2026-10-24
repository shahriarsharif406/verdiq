"""SIMULATED vegetation-health (NDVI-style) series. NOT satellite data.

Each project gets a deterministic monthly series (2021-01 .. 2025-09). Most projects are stable or improving;
P04 (REDD+) is generated with a declining trend so the divergence detector has something to find:
claimed sequestration (issued tCO2 per vintage) grows while the vegetation signal falls.
Labelled `simulated=True` everywhere it is shown.
"""
from __future__ import annotations

import hashlib

import numpy as np
import pandas as pd

DECLINING = {"P04"}
START, END = "2021-01-01", "2025-09-01"


def series(project_id: str) -> pd.DataFrame:
    seed = int(hashlib.sha256(project_id.encode()).hexdigest()[:8], 16)
    rng = np.random.default_rng(seed)
    idx = pd.date_range(START, END, freq="MS")
    t = np.arange(len(idx))
    base = rng.uniform(0.55, 0.72)
    seasonal = 0.04 * np.sin(2 * np.pi * (t % 12) / 12 + rng.uniform(0, 6))
    trend = (-0.0030 if project_id in DECLINING else rng.uniform(0.0, 0.0008)) * np.maximum(t - 14, 0)
    if project_id in DECLINING:
        trend = trend - 0.0006 * t
    noise = rng.normal(0, 0.008, len(idx))
    ndvi = np.clip(base + seasonal + trend + noise, 0.05, 0.95)
    return pd.DataFrame({"month": idx, "ndvi": ndvi, "simulated": True})


def divergence(issuances: pd.DataFrame) -> pd.DataFrame:
    """One row per project: claim slope vs simulated NDVI slope (per year)."""
    rows = []
    for pid, g in issuances.groupby("project_id"):
        g = g.sort_values("vintage_year")
        cat_cook = "Cookstoves" in g.methodology.iloc[0]
        s = series(pid)
        yr = s.groupby(s.month.dt.year).ndvi.mean()
        ys = np.array(yr.index, dtype=float)
        nd_slope = float(np.polyfit(ys, yr.values, 1)[0])
        claim_slope = float(np.polyfit(g.vintage_year.astype(float), g.issued_tco2.astype(float), 1)[0]) if len(g) > 1 else 0.0
        claim_growth = claim_slope / max(float(g.issued_tco2.mean()), 1.0)
        flagged = (not cat_cook) and claim_growth > 0.02 and nd_slope < -0.015
        rows.append(dict(project_id=pid, ndvi_slope_per_yr=round(nd_slope, 4), claim_growth_per_yr=round(claim_growth, 3),
                         divergence=bool(flagged), applicable=not cat_cook, simulated=True))
    return pd.DataFrame(rows)
