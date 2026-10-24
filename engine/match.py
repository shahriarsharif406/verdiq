"""Three-way reconciliation: registry issuance (voucher) x retirements (ledger) x market trades (payment).

The ledger is replayed chronologically against an interval ownership map. An invalid event is flagged
and NOT applied - exactly what the on-chain firewall (contracts/VerdiqRegistry.sol) does.

Status vocabulary
  MATCHED            event is consistent with issuance, ownership and retirement state
  UNISSUED           range (partly) outside anything the registry issued
  ORPHAN             range is issued but the actor never held it (no provenance)
  DOUBLE_SOLD        seller already sold this range to someone else
  DOUBLE_RETIRED     range already retired
  RETIRED_NOT_OWNED  retiring entity does not currently own the range (or a trade of retired credits)
"""
from __future__ import annotations

import bisect
from dataclasses import dataclass

import pandas as pd

from .common import STATUS_RULE, make_flag, overlap, project_of


@dataclass
class Seg:
    start: int
    end: int
    owner: str
    retired: bool = False
    retired_by: str | None = None
    claimed_for: str | None = None
    history: tuple = ()
    project_id: str | None = None
    issuance_id: str | None = None

    def clone(self, start, end):
        return Seg(start, end, self.owner, self.retired, self.retired_by, self.claimed_for, self.history,
                   self.project_id, self.issuance_id)


class Ledger:
    """Sorted, non-overlapping owned-serial segments."""

    def __init__(self):
        self.segs: list[Seg] = []
        self._starts: list[int] = []

    def issue(self, start, end, owner, project_id, issuance_id):
        i = bisect.bisect_left(self._starts, start)
        self.segs.insert(i, Seg(start, end, owner, project_id=project_id, issuance_id=issuance_id))
        self._starts.insert(i, start)

    def pieces(self, start, end):
        """Return (covered_pieces[(a, b, seg)], uncovered_gaps[(a, b)]) for [start, end]."""
        i = max(bisect.bisect_right(self._starts, start) - 1, 0)
        covered, gaps, cur = [], [], start
        while i < len(self.segs) and self.segs[i].start <= end:
            s = self.segs[i]
            ov = overlap(start, end, s.start, s.end)
            if ov:
                if ov[0] > cur:
                    gaps.append((cur, ov[0] - 1))
                covered.append((ov[0], ov[1], s))
                cur = ov[1] + 1
            i += 1
        if cur <= end:
            gaps.append((cur, end))
        return covered, gaps

    def _split(self, at):
        i = bisect.bisect_right(self._starts, at) - 1
        if i < 0:
            return
        s = self.segs[i]
        if s.start < at <= s.end:
            right = s.clone(at, s.end)
            s.end = at - 1
            self.segs.insert(i + 1, right)
            self._starts.insert(i + 1, at)

    def apply(self, start, end, fn):
        self._split(start)
        self._split(end + 1)
        i = bisect.bisect_left(self._starts, start)
        while i < len(self.segs) and self.segs[i].start <= end:
            fn(self.segs[i])
            i += 1

    def snapshot(self):
        return [dict(vars(s)) for s in self.segs]

    def copy(self):
        c = Ledger()
        c.segs = [s.clone(s.start, s.end) for s in self.segs]
        c._starts = list(self._starts)
        return c


PRECEDENCE = ["UNISSUED", "ORPHAN", "DOUBLE_SOLD", "DOUBLE_RETIRED", "RETIRED_NOT_OWNED"]


def classify(ledger: Ledger, kind: str, start: int, end: int, actor: str):
    """Return (status, reason). Does not mutate the ledger."""
    covered, gaps = ledger.pieces(start, end)
    if gaps:
        gtot = sum(b - a + 1 for a, b in gaps)
        where = "outside every registry issuance" if not covered else "partly outside registry issuance"
        return "UNISSUED", f"{gtot:,} of {end-start+1:,} tCO2 are {where}: the registry never issued these serials."
    found: dict = {}
    for a, b, s in covered:
        if kind == "TRADE":
            if s.retired:
                st = "RETIRED_NOT_OWNED"
            elif s.owner != actor:
                st = "DOUBLE_SOLD" if actor in s.history else "ORPHAN"
            else:
                continue
        else:
            if s.retired:
                st = "DOUBLE_RETIRED"
            elif s.owner != actor:
                st = "RETIRED_NOT_OWNED"
            else:
                continue
        found.setdefault(st, []).append((a, b, s))
    if not found:
        return "MATCHED", "Issued, owned by the acting party and not yet retired."
    st = next(p for p in PRECEDENCE if p in found)
    a, b, s = found[st][0]
    n = sum(y - x + 1 for x, y, _ in found[st])
    if st == "DOUBLE_SOLD":
        reason = (f"{actor} had already transferred these {n:,} tCO2 (current owner: {s.owner}). "
                  "The same serials are being sold a second time.")
    elif st == "ORPHAN":
        reason = f"{actor} never held these {n:,} tCO2 (owner: {s.owner}); the sale has no provenance."
    elif st == "DOUBLE_RETIRED":
        reason = (f"{n:,} tCO2 were already retired by {s.retired_by} for '{s.claimed_for}'. "
                  "Retiring them again would count the same tonnes twice.")
    else:
        reason = f"{actor} does not own these {n:,} tCO2 (owner: {s.owner}{', already retired' if s.retired else ''})."
    return st, reason


def apply_event(led: Ledger, kind: str, start: int, end: int, actor: str, counterparty: str):
    if kind == "TRADE":
        def fn(s):
            s.history = s.history + (s.owner,)
            s.owner = counterparty
    else:
        def fn(s):
            s.retired, s.retired_by, s.claimed_for = True, actor, counterparty
    led.apply(start, end, fn)


def build_events(trades: pd.DataFrame, retirements: pd.DataFrame) -> pd.DataFrame:
    t = trades.rename(columns={"trade_id": "event_id", "seller": "actor", "buyer": "counterparty"}).copy()
    t["kind"] = "TRADE"
    r = retirements.rename(columns={"retirement_id": "event_id", "retiring_entity": "actor"}).copy()
    r["kind"] = "RETIREMENT"
    r["counterparty"] = r["claimed_for"]
    r["price_usd"] = float("nan")
    ev = pd.concat([t, r], ignore_index=True)
    ev["tco2"] = ev.serial_end - ev.serial_start + 1
    ev["order"] = ev.kind.map({"TRADE": 0, "RETIREMENT": 1})
    ev = ev.sort_values(["date", "order", "event_id"]).reset_index(drop=True)
    ev["project_id"] = ev.serial_start.map(project_of)
    return ev.drop(columns=["order", "claimed_for"], errors="ignore")


def seed_ledger(issuances: pd.DataFrame) -> Ledger:
    led = Ledger()
    for r in issuances.sort_values("serial_start").itertuples():
        led.issue(int(r.serial_start), int(r.serial_end), r.developer, r.project_id, r.issuance_id)
    return led


def reconcile(issuances, trades, retirements, snapshot_dates=None):
    """Replay everything. Returns (events_df, final_ledger, snapshots{date: [seg dict]}).

    A snapshot dated D is the ledger state after all events with date <= D.
    """
    ev = build_events(trades, retirements)
    led = seed_ledger(issuances)
    status, rule, reason, evidence = [], [], [], []
    snaps: dict = {}
    pending = sorted(snapshot_dates or [])
    applied: list = []

    def take_snaps(before_date):
        while pending and pending[0] < before_date:
            snaps[pending.pop(0)] = led.snapshot()

    for row in ev.itertuples():
        take_snaps(row.date)
        a, b = int(row.serial_start), int(row.serial_end)
        st, why = classify(led, row.kind, a, b, row.actor)
        if st == "MATCHED":
            apply_event(led, row.kind, a, b, row.actor, row.counterparty)
            applied.append(dict(event_id=row.event_id, kind=row.kind, date=row.date, actor=row.actor,
                                counterparty=row.counterparty, serial_start=a, serial_end=b))
            evid = []
        else:
            evid = [dict(p, relation="earlier ledger entry on the same serials") for p in applied
                    if overlap(p["serial_start"], p["serial_end"], a, b)][-4:]
        status.append(st); rule.append(STATUS_RULE.get(st)); reason.append(why); evidence.append(evid)
    take_snaps("9999-12-31")
    ev["status"], ev["rule_id"], ev["reason"], ev["evidence"] = status, rule, reason, evidence
    return ev, led, snaps


def status_flags(ev: pd.DataFrame, price_by_project: dict) -> list:
    flags = []
    for r in ev[ev.status != "MATCHED"].itertuples():
        px = r.price_usd if r.kind == "TRADE" else price_by_project.get(r.project_id, 10.0)
        flags.append(make_flag(r.rule_id, "event", r.event_id, r.reason, project_id=r.project_id,
                               serial_start=int(r.serial_start), serial_end=int(r.serial_end), tco2=r.tco2,
                               usd=px * r.tco2, date=r.date, evidence=r.evidence))
    return flags


def issuance_summary(issuances: pd.DataFrame, ev: pd.DataFrame, led: Ledger) -> pd.DataFrame:
    """Bank-style balance per issuance: issued = unsold + in market + retired; plus tonnes the ledger rejected."""
    bad = ev[ev.status != "MATCHED"]
    rows = []
    for r in issuances.itertuples():
        segs = [s for s in led.segs if s.issuance_id == r.issuance_id]
        n = lambda ss: sum(s.end - s.start + 1 for s in ss)
        retired = n([s for s in segs if s.retired])
        market = n([s for s in segs if not s.retired and s.owner != r.developer])
        held = n([s for s in segs if not s.retired and s.owner == r.developer])
        rej = bad[(bad.serial_start <= r.serial_end) & (bad.serial_end >= r.serial_start)].tco2.sum()
        rows.append(dict(issuance_id=r.issuance_id, project_id=r.project_id, vintage=r.vintage_year, issued=r.issued_tco2,
                         unsold=held, in_market=market, retired=retired,
                         balanced=bool(held + market + retired == r.issued_tco2), rejected_tco2=int(rej)))
    return pd.DataFrame(rows)
