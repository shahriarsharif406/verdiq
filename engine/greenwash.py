"""R09 - greenwashing: public offset claims versus what the ledger shows was actually retired (and how much of
it is clean, i.e. not touching any HIGH/CRITICAL flag)."""
from __future__ import annotations

import pandas as pd

from .common import SEV_RANK, make_flag, overlap

SUPPORTED_AT = 0.90   # retired >= 90% of the claim -> supported


def taint_flags(flags: list, a: int, b: int, min_sev: str = "HIGH") -> list:
    out = []
    for f in flags:
        if SEV_RANK[f["severity"]] < SEV_RANK[min_sev]:
            continue
        if any(overlap(a, b, x, y) for x, y in f["ranges"]):
            out.append(f)
    return out


def company_ledger(company: str, events: pd.DataFrame, flags: list) -> dict:
    """What a company actually retired, valid vs clean."""
    ret = events[(events.kind == "RETIREMENT") & (events.actor == company)]
    valid = ret[ret.status == "MATCHED"]
    clean_t, dirty_rows = 0, []
    for r in valid.itertuples():
        bad = [f for f in taint_flags(flags, int(r.serial_start), int(r.serial_end)) if f["subject_id"] != r.event_id]
        if bad:
            dirty_rows.append(dict(retirement_id=r.event_id, tco2=r.tco2, why="; ".join(sorted({f"{x['rule_id']} {x['rule_name']}" for x in bad}))))
        else:
            clean_t += r.tco2
    return dict(company=company, retired_all=int(ret.tco2.sum()), retired_valid=int(valid.tco2.sum()),
                retired_clean=int(clean_t), rejected=int(ret[ret.status != "MATCHED"].tco2.sum()),
                n_retirements=len(ret), tainted=dirty_rows,
                rejected_rows=[dict(retirement_id=r.event_id, tco2=r.tco2, status=r.status, reason=r.reason)
                               for r in ret[ret.status != "MATCHED"].itertuples()])


def check_claim(company: str, claimed_tco2: int, events: pd.DataFrame, flags: list) -> dict:
    led = company_ledger(company, events, flags)
    claimed = max(int(claimed_tco2), 1)
    ratio_valid = led["retired_valid"] / claimed
    ratio_clean = led["retired_clean"] / claimed
    if ratio_clean >= SUPPORTED_AT:
        verdict, sev = "SUPPORTED", "OK"
    elif ratio_valid >= SUPPORTED_AT:
        verdict, sev = "PARTLY SUPPORTED", "WARN"
    else:
        verdict, sev = "UNSUPPORTED", "BAD"
    gap = max(claimed - led["retired_clean"], 0)
    summary = (f"{company} claims {claimed:,} tCO2. The ledger shows {led['retired_valid']:,} tCO2 validly retired "
               f"({ratio_valid:.0%} of the claim) and {led['retired_clean']:,} tCO2 retired from credits with no integrity flags "
               f"({ratio_clean:.0%}). ")
    if led["rejected"]:
        summary += f"A further {led['rejected']:,} tCO2 of retirement attempts were rejected as invalid. "
    summary += f"{gap:,} tCO2 of the claim ({gap/claimed:.0%}) is not backed by clean, verified retirements."
    return dict(led, claimed=claimed, ratio_valid=ratio_valid, ratio_clean=ratio_clean, verdict=verdict, verdict_level=sev,
                gap=gap, summary=summary)


def greenwash_flags(corp_claims: pd.DataFrame, events: pd.DataFrame, flags: list) -> list:
    out = []
    for c in corp_claims.itertuples():
        res = check_claim(c.company, int(c.claimed_tco2), events, flags)
        if res["ratio_valid"] < SUPPORTED_AT:
            out.append(make_flag(
                "R09", "claim", c.claim_id,
                f"Public claim '{c.claim_text}' ({c.channel}, {c.date}) is not supported: only {res['retired_valid']:,} tCO2 "
                f"({res['ratio_valid']:.0%}) were validly retired.",
                tco2=res["claimed"] - res["retired_valid"], date=c.date,
                evidence=[dict(company=c.company, claimed=res["claimed"], retired_valid=res["retired_valid"],
                               retired_clean=res["retired_clean"], rejected=res["rejected"])]))
    return out
