"""Runs every engine module and returns one result bundle. `python -m engine.pipeline` writes data/out/*."""
from __future__ import annotations

import json
from dataclasses import dataclass, field

import pandas as pd

from . import article6, geo, greenwash, merkle, ndvi_sim, plausibility, score, wash
from .common import DATA, OUT, SEV_RANK, load_data, project_of
from .match import issuance_summary, reconcile, status_flags

EQUIV_TCO2_PER_CAR_YEAR = 4.6      # US EPA: typical passenger vehicle emits ~4.6 t CO2/yr
EQUIV_TCO2_PER_TREE_10YR = 0.060   # US EPA: urban tree seedling grown 10 yrs sequesters ~0.060 t CO2


@dataclass
class Result:
    data: dict
    events: pd.DataFrame
    ledger: object
    flags: list
    flags_df: pd.DataFrame
    issuance_summary: pd.DataFrame
    scores: pd.DataFrame
    divergence: pd.DataFrame
    anomalies: pd.DataFrame
    closes: dict = field(default_factory=dict)
    price_by_project: dict = field(default_factory=dict)


def month_ends(events: pd.DataFrame) -> list:
    d = pd.to_datetime(events.date)
    rng = pd.period_range(d.min(), d.max(), freq="M")
    return [str(p.end_time.date()) for p in rng]


def run(data_dir=None, with_closes: bool = True, data: dict | None = None) -> Result:
    data = data or load_data(data_dir)
    iss, trades, rets = data["issuances"], data["trades"], data["retirements"]
    tr = trades.assign(project_id=trades.serial_start.map(project_of))
    price = tr.groupby("project_id").price_usd.median().to_dict()
    ends = month_ends(pd.concat([trades[["date"]], rets[["date"]]])) if with_closes else []
    ev, led, snaps = reconcile(iss, trades, rets, snapshot_dates=ends)
    flags = status_flags(ev, price)
    flags += geo.geo_flags(iss)
    flags += plausibility.plausibility_flags(iss)
    flags += article6.article6_flags(data["host_claims"], rets, price)
    flags += wash.wash_flags(trades)
    flags += wash.price_spike_flags(trades, project_of)
    for f in flags:
        if f["project_id"] is None and f["serial_start"] is not None:
            f["project_id"] = project_of(f["serial_start"])
    # a trade can trip both R07 and R08: keep both (distinct rules)
    flags += greenwash.greenwash_flags(data["corp_claims"], ev, flags)
    div = ndvi_sim.divergence(iss)
    sc = score.project_scores(iss, trades, flags, div)
    res = Result(data=data, events=ev, ledger=led, flags=flags, flags_df=flags_frame(flags),
                 issuance_summary=issuance_summary(iss, ev, led), scores=sc, divergence=div,
                 anomalies=score.trade_anomalies(trades, iss), price_by_project=price)
    for d, segs in snaps.items():
        res.closes[d] = merkle.make_close(segs, flags, d)
    return res


def flags_frame(flags: list) -> pd.DataFrame:
    cols = ["flag_id", "rule_id", "rule_name", "severity", "fraud_type", "subject_type", "subject_id", "project_id",
            "serial_start", "serial_end", "tco2", "usd_at_risk", "date", "reason"]
    df = pd.DataFrame([{k: f[k] for k in cols} for f in flags], columns=cols)
    if len(df):
        df["rank"] = df.severity.map(SEV_RANK)
        df = df.sort_values(["rank", "usd_at_risk"], ascending=[False, False]).drop(columns="rank").reset_index(drop=True)
    return df


def impact(res: Result, asof: str | None = None) -> dict:
    """Climate Impact Counter: tonnes protected from double counting and fraudulent USD volume blocked."""
    fl = [f for f in res.flags if f["subject_type"] in ("event", "host_claim") and (asof is None or (f["date"] or "") <= asof)]
    by_event = {}
    for f in fl:
        by_event[f["subject_id"]] = max(by_event.get(f["subject_id"], f), f, key=lambda x: x["usd_at_risk"])
    tonnes = sum(f["tco2"] for f in by_event.values())
    usd = sum(f["usd_at_risk"] for f in by_event.values())
    return dict(tonnes_protected=int(tonnes), usd_blocked=float(usd), events_blocked=len(by_event),
                cars_per_year=tonnes / EQUIV_TCO2_PER_CAR_YEAR, trees=tonnes / EQUIV_TCO2_PER_TREE_10YR)


def evaluate(res: Result, ground_truth: dict | None = None) -> dict:
    """Detection report versus injected ground truth."""
    gt = ground_truth or json.loads((DATA / "ground_truth.json").read_text(encoding="utf-8"))
    flagged = {f["subject_id"] for f in res.flags}
    expected = set(gt["expected_subjects"])
    tp = flagged & expected
    cases = []
    for c in gt["cases"]:
        got = {f["subject_id"]: f["rule_id"] for f in res.flags if f["subject_id"] in c["subject_ids"]}
        ok = all(s in got for s in c["subject_ids"])
        cases.append(dict(case_id=c["case_id"], fraud_type=c["fraud_type"], name=c["name"], detected=ok, rules=sorted(set(got.values()))))
    types = sorted({c["fraud_type"] for c in gt["cases"]})
    det_types = [t for t in types if all(c["detected"] for c in cases if c["fraud_type"] == t)]
    return dict(precision=len(tp) / len(flagged) if flagged else 1.0, recall=len(tp) / len(expected),
                false_positives=sorted(flagged - expected), missed=sorted(expected - flagged),
                types_total=len(types), types_detected=len(det_types), cases=cases)


def write_outputs(res: Result) -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    res.events.drop(columns=["evidence"]).to_csv(OUT / "reconciliation_events.csv", index=False)
    res.flags_df.to_csv(OUT / "flags.csv", index=False)
    res.scores.drop(columns=["why"]).to_csv(OUT / "trust_scores.csv", index=False)
    closes = {d: {k: v for k, v in c.items() if k not in ("records", "_levels")} for d, c in res.closes.items()}
    (OUT / "closes.json").write_text(json.dumps(closes, indent=2), encoding="utf-8")


if __name__ == "__main__":
    r = run()
    write_outputs(r)
    ev = evaluate(r)
    print(f"flags: {len(r.flags)} | detected {ev['types_detected']}/{ev['types_total']} fraud types | "
          f"precision {ev['precision']:.2f} recall {ev['recall']:.2f}")
    print("false positives:", ev["false_positives"], "missed:", ev["missed"])
