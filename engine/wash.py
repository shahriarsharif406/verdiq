"""R07 wash-trade loops (A -> B -> ... -> A on overlapping serials in a short window) and R08 price spikes."""
from __future__ import annotations

import networkx as nx
import pandas as pd

from .common import make_flag, overlap

WINDOW_DAYS = 90
MAX_CYCLE = 4
SPIKE_MULTIPLE = 3.0   # price > 3x the project median


def _clusters(tr: pd.DataFrame) -> list:
    """Group trades whose serial ranges chain-overlap (union-find over a sorted sweep)."""
    tr = tr.sort_values("serial_start")
    groups, cur, cur_end = [], [], -1
    for r in tr.itertuples():
        if cur and r.serial_start > cur_end:
            groups.append(cur); cur, cur_end = [], -1
        cur.append(r); cur_end = max(cur_end, r.serial_end)
    if cur:
        groups.append(cur)
    return groups


def wash_flags(trades: pd.DataFrame) -> list:
    flags, seen = [], set()
    for grp in _clusters(trades):
        if len(grp) < 3:
            continue
        g = nx.DiGraph()
        for r in grp:
            g.add_edge(r.seller, r.buyer, **{})   # structure only
        for cyc in nx.simple_cycles(g, length_bound=MAX_CYCLE):
            edges = list(zip(cyc, cyc[1:] + cyc[:1]))
            legs = []
            for a, b in edges:
                cand = [r for r in grp if r.seller == a and r.buyer == b]
                legs.append(cand)
            if any(not c for c in legs):
                continue
            # pick, per edge, the trade that overlaps the first leg and keeps the window tight
            pick = []
            for c in legs:
                pick.append(sorted(c, key=lambda r: r.date)[0])
            lo, hi = max(p.serial_start for p in pick), min(p.serial_end for p in pick)
            if lo > hi:
                continue
            span = (pd.Timestamp(max(p.date for p in pick)) - pd.Timestamp(min(p.date for p in pick))).days
            if span > WINDOW_DAYS:
                continue
            ids = tuple(sorted(p.trade_id for p in pick))
            if ids in seen:
                continue
            seen.add(ids)
            ring = " → ".join(cyc + [cyc[0]])
            for p in pick:
                flags.append(make_flag(
                    "R07", "event", p.trade_id,
                    f"Part of a wash-trading loop: {ring}. The same {hi-lo+1:,} tCO2 changed hands "
                    f"{len(pick)} times within {span} days and returned to the first party, creating volume without a real buyer.",
                    project_id=None, serial_start=int(p.serial_start), serial_end=int(p.serial_end),
                    tco2=int(p.serial_end - p.serial_start + 1), usd=p.price_usd * (p.serial_end - p.serial_start + 1), date=p.date,
                    evidence=[dict(trade_id=q.trade_id, seller=q.seller, buyer=q.buyer, price_usd=q.price_usd, date=q.date) for q in pick]))
    return flags


def price_spike_flags(trades: pd.DataFrame, project_of_fn) -> list:
    tr = trades.copy()
    tr["project_id"] = tr.serial_start.map(project_of_fn)
    med = tr.groupby("project_id").price_usd.median()
    flags = []
    for r in tr.itertuples():
        m = med.get(r.project_id)
        if m and r.price_usd > SPIKE_MULTIPLE * m:
            n = r.serial_end - r.serial_start + 1
            flags.append(make_flag(
                "R08", "event", r.trade_id,
                f"Price ${r.price_usd:,.2f}/t is {r.price_usd/m:.1f}x the {r.project_id} median (${m:,.2f}). "
                "Abnormal price on a thin trade can launder credit value or inflate reported market volume.",
                project_id=r.project_id, serial_start=int(r.serial_start), serial_end=int(r.serial_end), tco2=n,
                usd=r.price_usd * n, date=r.date, evidence=[dict(price_usd=r.price_usd, project_median=round(float(m), 2))]))
    return flags
