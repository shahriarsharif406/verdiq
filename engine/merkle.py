"""Day-End Close: reconciliation snapshot -> Merkle tree -> root anchored on-chain.

Hashing scheme (mirrored in VerdiqRegistry.verifyProof):
  leaf   = sha256(0x00 || canonical_json(record))
  parent = sha256(0x01 || min(l, r) || max(l, r))     (sorted pair => proof needs no left/right flags)
  odd node on a level is promoted by pairing with itself.
"""
from __future__ import annotations

import hashlib
import json


def canon(record: dict) -> bytes:
    return json.dumps(record, sort_keys=True, separators=(",", ":")).encode()


def leaf_hash(record: dict) -> bytes:
    return hashlib.sha256(b"\x00" + canon(record)).digest()


def node_hash(a: bytes, b: bytes) -> bytes:
    lo, hi = (a, b) if a <= b else (b, a)
    return hashlib.sha256(b"\x01" + lo + hi).digest()


def build_tree(leaves: list) -> list:
    """Return levels, levels[0] = leaf hashes, levels[-1] = [root]."""
    if not leaves:
        return [[hashlib.sha256(b"").digest()]]
    levels = [list(leaves)]
    while len(levels[-1]) > 1:
        cur = levels[-1]
        nxt = []
        for i in range(0, len(cur), 2):
            nxt.append(node_hash(cur[i], cur[i + 1] if i + 1 < len(cur) else cur[i]))
        levels.append(nxt)
    return levels


def root_of(levels: list) -> bytes:
    return levels[-1][0]


def proof(levels: list, index: int) -> list:
    path = []
    for lvl in levels[:-1]:
        sib = index ^ 1
        path.append(lvl[sib] if sib < len(lvl) else lvl[index])
        index //= 2
    return path


def verify(record_or_leaf, path: list, root: bytes) -> bool:
    h = leaf_hash(record_or_leaf) if isinstance(record_or_leaf, dict) else record_or_leaf
    for p in path:
        h = node_hash(h, p)
    return h == root


def snapshot_records(segments: list, flags: list, close_date: str) -> list:
    """One record per ledger segment of the closing state; status DISPUTED if any flag touches it."""
    from .common import overlap
    flagged = [f for f in flags if f["severity"] in ("CRITICAL", "HIGH") and (f.get("date") is None or f["date"] <= close_date)]
    recs = []
    for s in sorted(segments, key=lambda x: x["start"]):
        hit = sorted({f["rule_id"] for f in flagged if any(overlap(s["start"], s["end"], a, b) for a, b in f["ranges"])})
        recs.append(dict(project=s["project_id"], issuance=s["issuance_id"], start=int(s["start"]), end=int(s["end"]),
                         owner=s["owner"], state="RETIRED" if s["retired"] else "ACTIVE",
                         status="DISPUTED" if hit else "VERIFIED", rules=hit))
    return recs


def make_close(segments: list, flags: list, close_date: str) -> dict:
    recs = snapshot_records(segments, flags, close_date)
    levels = build_tree([leaf_hash(r) for r in recs])
    return dict(date=close_date, root=root_of(levels).hex(), n_leaves=len(recs),
                n_verified=sum(r["status"] == "VERIFIED" for r in recs), n_disputed=sum(r["status"] == "DISPUTED" for r in recs),
                records=recs, _levels=levels)


def proof_for_serial(close: dict, serial: int):
    """Merkle proof for the segment containing `serial` (or None)."""
    for i, r in enumerate(close["records"]):
        if r["start"] <= serial <= r["end"]:
            return dict(index=i, record=r, leaf=leaf_hash(r).hex(), path=[p.hex() for p in proof(close["_levels"], i)],
                        root=close["root"])
    return None


def verify_proof(p: dict) -> bool:
    return verify(p["record"], [bytes.fromhex(x) for x in p["path"]], bytes.fromhex(p["root"]))
