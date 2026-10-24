"""R06 - Article 6 style double claim: a host country counts tonnes toward its NDC *without* a corresponding
adjustment while a company also retires the same tonnes for its own claim."""
from __future__ import annotations

import pandas as pd

from .common import make_flag, overlap, project_of


def article6_flags(host_claims: pd.DataFrame, retirements: pd.DataFrame, price_by_project: dict | None = None) -> list:
    flags = []
    price_by_project = price_by_project or {}
    for h in host_claims[~host_claims.corresponding_adjustment.astype(bool)].itertuples():
        hits = []
        for r in retirements.itertuples():
            ov = overlap(int(h.serial_start), int(h.serial_end), int(r.serial_start), int(r.serial_end))
            if ov:
                hits.append((r, ov))
        if not hits:
            continue
        tco2 = sum(b - a + 1 for _, (a, b) in hits)
        r0 = hits[0][0]
        pid = project_of(h.serial_start)
        flags.append(make_flag(
            "R06", "host_claim", h.claim_id,
            f"{h.country} counts {tco2:,} tCO2 toward its NDC ({h.basis}) with NO corresponding adjustment, while "
            f"{r0.retiring_entity} retired the same tonnes for '{r0.claimed_for}': the same tonnes are claimed twice.",
            project_id=pid, serial_start=int(h.serial_start), serial_end=int(h.serial_end), tco2=tco2,
            usd=tco2 * price_by_project.get(pid, 10.0), date=h.date,
            evidence=[dict(retirement_id=r.retirement_id, entity=r.retiring_entity, date=r.date, overlap_tco2=b - a + 1)
                      for r, (a, b) in hits]))
    return flags
