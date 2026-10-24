"""Shared helpers: data loading, serial-interval maths, rule catalogue, flag construction."""
from __future__ import annotations

import re
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
OUT = DATA / "out"
BLOCK = 2_000_000

# rule_id -> (name, severity, fraud_type)
RULES = {
    "R01": ("DOUBLE_SOLD", "CRITICAL", 1),
    "R02": ("DOUBLE_RETIRED", "CRITICAL", 2),
    "R03": ("UNISSUED", "CRITICAL", 3),
    "R04": ("GEO_OVERLAP", "HIGH", 4),
    "R05": ("IMPLAUSIBLE_YIELD", "HIGH", 5),
    "R06": ("ARTICLE6_DOUBLE_CLAIM", "HIGH", 6),
    "R07": ("WASH_TRADE", "HIGH", 7),
    "R08": ("PRICE_SPIKE", "MEDIUM", 7),
    "R09": ("GREENWASHING", "HIGH", 8),
    "R10": ("ORPHAN", "CRITICAL", 1),
    "R11": ("RETIRED_NOT_OWNED", "HIGH", 2),
}
SEV_RANK = {"LOW": 1, "MEDIUM": 2, "HIGH": 3, "CRITICAL": 4}
STATUS_RULE = {"DOUBLE_SOLD": "R01", "DOUBLE_RETIRED": "R02", "UNISSUED": "R03", "ORPHAN": "R10",
               "RETIRED_NOT_OWNED": "R11"}


def fmt_serial(n: int) -> str:
    return f"VQ-{int(n):08d}"


def fmt_range(a: int, b: int) -> str:
    return f"{fmt_serial(a)} → {fmt_serial(b)}"


def parse_range(text: str) -> tuple[int, int]:
    """Accepts 'VQ-01000001 - VQ-01005000', '1000001-1005000', '1,000,001 → 1,005,000'."""
    nums = re.findall(r"\d+", str(text).replace(",", ""))
    if not nums:
        raise ValueError("expected a serial number")
    a = int(nums[0])
    b = int(nums[1]) if len(nums) > 1 else a
    return (a, b) if a <= b else (b, a)


def overlap(a0: int, a1: int, b0: int, b1: int):
    lo, hi = max(a0, b0), min(a1, b1)
    return (lo, hi) if lo <= hi else None


def project_of(serial: int):
    k = int(serial) // BLOCK
    return f"P{k:02d}" if 1 <= k <= 99 else None


def load_data(data_dir=None) -> dict:
    d = Path(data_dir) if data_dir else DATA
    return dict(
        issuances=pd.read_csv(d / "registry_issuances.csv"),
        trades=pd.read_csv(d / "market_trades.csv"),
        retirements=pd.read_csv(d / "retirements.csv"),
        host_claims=pd.read_csv(d / "host_country_claims.csv"),
        corp_claims=pd.read_csv(d / "corporate_claims.csv"),
    )


def make_flag(rule_id, subject_type, subject_id, reason, *, project_id=None, serial_start=None, serial_end=None,
              tco2=0, usd=0.0, date=None, evidence=None, ranges=None, severity=None) -> dict:
    name, sev, ftype = RULES[rule_id]
    if ranges is None:
        ranges = [(int(serial_start), int(serial_end))] if serial_start is not None else []
    return dict(
        flag_id=f"F-{rule_id}-{subject_id}", rule_id=rule_id, rule_name=name, severity=severity or sev,
        fraud_type=ftype, subject_type=subject_type, subject_id=subject_id, project_id=project_id,
        serial_start=serial_start, serial_end=serial_end, tco2=int(tco2 or 0), usd_at_risk=float(usd or 0),
        date=date, reason=reason, evidence=evidence or [], ranges=ranges,
    )
