"""Tonne Passport: everything verifiable about one serial range, as plain data."""
from __future__ import annotations

import pandas as pd

from . import merkle, score
from .common import fmt_range, fmt_serial, overlap, project_of


def build(res, start: int, end: int, tx_index: dict | None = None, anchors: dict | None = None) -> dict:
    tx_index = tx_index or {}
    anchors = anchors or {}
    iss = res.data["issuances"]
    hit = iss[(iss.serial_start <= end) & (iss.serial_end >= start)]
    issued = len(hit) > 0
    prim = hit.iloc[0] if issued else None
    covered, gaps = res.ledger.pieces(start, end)
    ev = res.events[(res.events.serial_start <= end) & (res.events.serial_end >= start)]

    timeline = []
    if issued:
        for r in hit.itertuples():
            ov = overlap(start, end, int(r.serial_start), int(r.serial_end))
            timeline.append(dict(date=r.issuance_date, kind="ISSUED", ok=True, title=f"Issued by registry · {r.project_name} · vintage {r.vintage_year}",
                                 detail=f"{ov[1]-ov[0]+1:,} tCO₂ to {r.developer} ({r.methodology})", tx=None, event_id=r.issuance_id))
    owners = []
    for r in ev.itertuples():
        tx = tx_index.get(r.event_id)
        ok = r.status == "MATCHED"
        if r.kind == "TRADE":
            title = f"{'Sold' if ok else 'Sale ATTEMPT REJECTED'}: {r.actor} → {r.counterparty}"
            detail = f"{r.tco2:,} tCO₂ @ ${r.price_usd:,.2f}/t" if ok else f"{r.status}: {r.reason}"
            if ok:
                owners.append(r.counterparty)
        else:
            title = f"{'Retired' if ok else 'Retirement ATTEMPT REJECTED'} by {r.actor}"
            detail = f"{r.tco2:,} tCO₂ for “{r.counterparty}”" if ok else f"{r.status}: {r.reason}"
        timeline.append(dict(date=r.date, kind=("TRADE" if r.kind == "TRADE" else "RETIREMENT") if ok else "REJECTED", ok=ok, title=title,
                             detail=detail, tx=tx, event_id=r.event_id))
    timeline.sort(key=lambda x: x["date"])

    owner_chain = ([prim.developer] if issued else []) + owners
    seen, chain_clean = set(), []
    for o in owner_chain:
        if o not in seen:
            chain_clean.append(o); seen.add(o)

    segs = [dict(start=a, end=b, owner=s.owner, retired=s.retired, retired_by=s.retired_by, claimed_for=s.claimed_for) for a, b, s in covered]
    if not issued:
        state = "NOT ISSUED"
    elif all(s["retired"] for s in segs) and not gaps:
        state = "RETIRED"
    elif any(s["retired"] for s in segs):
        state = "PARTLY RETIRED"
    else:
        state = "ACTIVE"

    sc = score.score_range(start, end, res.flags, res.scores)
    if gaps:
        sc = dict(sc, verdict="BLOCKED", score=0.0, why=[f"{sum(b-a+1 for a,b in gaps):,} tCO₂ of this range were never issued by the registry."] + sc["why"])

    last_date = sorted(res.closes)[-1]
    close = res.closes[last_date]
    proof = merkle.proof_for_serial(close, start)
    mp = None
    if proof:
        mp = dict(close_date=last_date, root=close["root"], index=proof["index"], leaf=proof["leaf"], path=proof["path"],
                  valid=merkle.verify_proof(proof), record=proof["record"], anchor=anchors.get(last_date))
    return dict(start=start, end=end, tco2=end - start + 1, label=fmt_range(start, end), issued=issued, project_id=project_of(start),
                project_name=None if not issued else prim.project_name, country=None if not issued else prim.country,
                methodology=None if not issued else prim.methodology, vintage=None if not issued else int(prim.vintage_year),
                state=state, segments=segs, timeline=timeline, owner_chain=chain_clean, score=sc, merkle=mp, gaps=gaps,
                verdict=sc["verdict"])
