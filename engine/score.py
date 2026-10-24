"""Trust score 0-100 per project and per credit range, with a plain-English "why". Fully offline.

Components (all explainable):
  1. Rule flags      - weighted by severity (CRITICAL 25, HIGH 15, MEDIUM 8; geo-overlap 28 and impossible-yield 35), diminishing, capped at 70
  2. Isolation Forest - unsupervised anomaly detector on trade features (size, price vs project median, lag after issuance,
                        counterparty concentration); share of a project's trades in the anomalous tail costs up to 15 pts
  3. Benford's law   - first-digit distribution of reported trade volumes; a project that deviates much more than the
                        portfolio median costs up to 10 pts (statistical hint only, never a flag by itself)
  4. Simulated vegetation divergence - 10 pts (simulated NDVI, clearly labelled)
"""
from __future__ import annotations

import math

import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest

from .common import SEV_RANK, overlap, project_of

SEV_W = {"CRITICAL": 25, "HIGH": 15, "MEDIUM": 8, "LOW": 3}
# project-level integrity failures (the credits themselves are in doubt) weigh more than a single bad trade
RULE_W = {"R04": 28, "R05": 35}
RANGE_DIRECT_W = {"CRITICAL": 60, "HIGH": 40, "MEDIUM": 20, "LOW": 5}
BENFORD = np.array([math.log10(1 + 1 / d) for d in range(1, 10)])


def benford_mad(values) -> tuple[float, int]:
    v = np.asarray([x for x in values if x and x > 0], dtype=float)
    if len(v) < 15:
        return float("nan"), len(v)
    lead = np.array([int(str(int(x))[0]) for x in v])
    obs = np.array([(lead == d).mean() for d in range(1, 10)])
    return float(np.abs(obs - BENFORD).mean()), len(v)


def trade_anomalies(trades: pd.DataFrame, issuances: pd.DataFrame) -> pd.DataFrame:
    tr = trades.copy()
    tr["project_id"] = tr.serial_start.map(project_of)
    tr["tco2"] = tr.serial_end - tr.serial_start + 1
    med = tr.groupby("project_id").price_usd.transform("median")
    tr["price_ratio"] = tr.price_usd / med
    iss_date = issuances.set_index("project_id").groupby(level=0).issuance_date.min()
    tr["lag_days"] = (pd.to_datetime(tr.date) - pd.to_datetime(tr.project_id.map(iss_date))).dt.days
    seller_n = tr.groupby("seller").trade_id.transform("count")
    pair_n = tr.groupby(["seller", "buyer"]).trade_id.transform("count")
    tr["pair_share"] = pair_n / seller_n
    X = np.column_stack([np.log1p(tr.tco2), np.log(tr.price_ratio.clip(lower=0.05)), tr.lag_days.fillna(0) / 365.0, tr.pair_share])
    iso = IsolationForest(n_estimators=200, contamination=0.04, random_state=7).fit(X)
    tr["anomaly"] = -iso.score_samples(X)             # higher = stranger
    tr["is_outlier"] = iso.predict(X) == -1
    return tr[["trade_id", "project_id", "tco2", "price_ratio", "lag_days", "pair_share", "anomaly", "is_outlier"]]


def project_scores(issuances, trades, flags, divergence) -> pd.DataFrame:
    an = trade_anomalies(trades, issuances)
    ben = {}
    for pid, g in trades.assign(project_id=trades.serial_start.map(project_of)).groupby("project_id"):
        ben[pid] = benford_mad((g.serial_end - g.serial_start + 1).tolist())
    valid = [m for m, _ in ben.values() if not math.isnan(m)]
    med_mad = float(np.median(valid)) if valid else 0.0
    rows = []
    for p in issuances.drop_duplicates("project_id").itertuples():
        pid = p.project_id
        pf = [f for f in flags if f["project_id"] == pid and f["subject_type"] != "claim"]
        ws = sorted((RULE_W.get(f["rule_id"], SEV_W[f["severity"]]) for f in pf), reverse=True)
        pen_rules = min(70.0, sum(w * (0.7 ** i) for i, w in enumerate(ws)))
        a = an[an.project_id == pid]
        flagged_trades = {f["subject_id"] for f in flags if f["subject_type"] == "event"}   # already penalised by a rule
        share = float((a.is_outlier & ~a.trade_id.isin(flagged_trades)).mean()) if len(a) else 0.0
        pen_iso = min(15.0, share * 100 * 0.9)
        mad, n = ben.get(pid, (float("nan"), 0))
        pen_ben = 0.0 if math.isnan(mad) else float(min(10.0, max(0.0, (mad - med_mad) * 250)))
        dv = divergence[divergence.project_id == pid]
        pen_nd = 10.0 if (len(dv) and bool(dv.iloc[0].divergence)) else 0.0
        score = max(0.0, 100 - pen_rules - pen_iso - pen_ben - pen_nd)
        why = []
        for f in sorted(pf, key=lambda f: -SEV_RANK[f["severity"]])[:4]:
            why.append(f"{f['severity']} {f['rule_name']} - {f['reason']}")
        if pen_iso >= 3:
            why.append(f"{int(round(share*100))}% of this project's trades are statistical outliers (Isolation Forest).")
        if pen_ben >= 3:
            why.append(f"Trade volumes deviate from Benford's law more than the portfolio median (MAD {mad:.3f} vs {med_mad:.3f}).")
        if pen_nd:
            why.append("SIMULATED vegetation signal declines while claimed sequestration grows.")
        if not why:
            why.append("No rule flags, no statistical anomalies: reconciles cleanly.")
        rows.append(dict(project_id=pid, project_name=p.project_name, country=p.country, score=round(score, 1),
                         pen_rules=round(pen_rules, 1), pen_iforest=round(pen_iso, 1), pen_benford=round(pen_ben, 1),
                         pen_ndvi=pen_nd, n_flags=len(pf), tier=tier(score), why=why))
    return pd.DataFrame(rows).sort_values("score").reset_index(drop=True)


def tier(score: float) -> str:
    return "VERIFIED" if score >= 85 else ("RISKY" if score >= 55 else "BLOCKED")


def score_range(start: int, end: int, flags: list, proj_scores: pd.DataFrame) -> dict:
    """Score a serial range. Direct flags on the range dominate; project health adds a softer penalty."""
    hits = [f for f in flags if any(overlap(start, end, a, b) for a, b in f["ranges"]) and f["subject_type"] != "claim"]
    direct = max([RANGE_DIRECT_W[f["severity"]] for f in hits], default=0) + 5 * max(len(hits) - 1, 0)
    pid = project_of(start)
    ps = proj_scores[proj_scores.project_id == pid]
    pscore = float(ps.iloc[0].score) if len(ps) else 50.0
    score = max(0.0, min(100.0, 100 - direct - 0.4 * (100 - pscore)))
    has_crit = any(f["severity"] == "CRITICAL" for f in hits)
    verdict = "BLOCKED" if has_crit else ("RISKY" if (hits or score < 75) else "SAFE")
    why = [f"{f['rule_id']} {f['rule_name']} ({f['severity']}): {f['reason']}" for f in sorted(hits, key=lambda f: -SEV_RANK[f['severity']])[:5]]
    if not why:
        why = [f"No flags touch this range. Project {pid} trust score is {pscore:.0f}/100."]
    return dict(score=round(score, 1), verdict=verdict, project_id=pid, project_score=pscore, flags=hits, why=why)
