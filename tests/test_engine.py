import json
import subprocess
import sys

import pytest

from engine import merkle
from engine.common import DATA, overlap, parse_range
from engine.match import Ledger, classify, apply_event
from engine.pipeline import evaluate, impact, run


@pytest.fixture(scope="module")
def res():
    return run()


@pytest.fixture(scope="module")
def gt():
    return json.loads((DATA / "ground_truth.json").read_text(encoding="utf-8"))


def test_generator_is_deterministic(tmp_path):
    before = (DATA / "market_trades.csv").read_bytes()
    subprocess.run([sys.executable, str(DATA / "generate.py")], check=True, capture_output=True)
    assert (DATA / "market_trades.csv").read_bytes() == before


def test_every_injected_fraud_type_detected(res, gt):
    ev = evaluate(res, gt)
    assert ev["types_detected"] == ev["types_total"] == 8
    assert all(c["detected"] for c in ev["cases"]), [c for c in ev["cases"] if not c["detected"]]


def test_precision_and_recall(res, gt):
    ev = evaluate(res, gt)
    assert ev["recall"] == 1.0
    assert ev["precision"] == 1.0, ev["false_positives"]


def test_expected_rules_fire(res, gt):
    by_subject = {}
    for f in res.flags:
        by_subject.setdefault(f["subject_id"], set()).add(f["rule_id"])
    for c in gt["cases"]:
        for sid, rule in zip(c["subject_ids"], c["expected_rules"] if len(c["expected_rules"]) == len(c["subject_ids"]) else c["expected_rules"] * len(c["subject_ids"])):
            assert rule in by_subject[sid], (c["case_id"], sid, rule, by_subject.get(sid))


def test_every_flag_has_evidence_fields(res):
    for f in res.flags:
        assert f["rule_id"] and f["severity"] and f["reason"] and f["subject_id"]
        assert f["severity"] in ("LOW", "MEDIUM", "HIGH", "CRITICAL")


def test_all_issuances_balance(res):
    assert res.issuance_summary.balanced.all()


def test_clean_ledger_events_all_matched(res, gt):
    bad = set(res.events[res.events.status != "MATCHED"].event_id)
    injected = {s for c in gt["cases"] for s in c["subject_ids"]}
    assert bad <= injected


def test_interval_overlap_logic():
    assert overlap(1, 10, 10, 20) == (10, 10)
    assert overlap(1, 9, 10, 20) is None
    assert overlap(5, 6, 1, 100) == (5, 6)
    assert parse_range("VQ-01000001 → VQ-01005000") == (1000001, 1005000)


def test_ledger_partial_overlap_double_sale():
    led = Ledger()
    led.issue(1, 100, "dev", "P01", "I")
    assert classify(led, "TRADE", 1, 50, "dev")[0] == "MATCHED"
    apply_event(led, "TRADE", 1, 50, "dev", "A")
    assert classify(led, "TRADE", 40, 60, "dev")[0] == "DOUBLE_SOLD"      # overlap 40-50 already sold
    assert classify(led, "TRADE", 51, 100, "dev")[0] == "MATCHED"
    assert classify(led, "TRADE", 90, 120, "dev")[0] == "UNISSUED"        # 101-120 never issued
    assert classify(led, "TRADE", 1, 10, "zed")[0] == "ORPHAN"
    apply_event(led, "RETIREMENT", 1, 20, "A", "claim")
    assert classify(led, "RETIREMENT", 10, 30, "A")[0] == "DOUBLE_RETIRED"
    assert classify(led, "RETIREMENT", 21, 30, "B")[0] == "RETIRED_NOT_OWNED"


def test_merkle_proofs_verify_and_tamper_fails(res):
    close = list(res.closes.values())[-1]
    p = merkle.proof_for_serial(close, close["records"][3]["start"])
    assert merkle.verify_proof(p)
    p["record"] = dict(p["record"], owner="Mallory")
    assert not merkle.verify_proof(p)


def test_merkle_every_leaf_verifies(res):
    close = list(res.closes.values())[-1]
    for i, r in enumerate(close["records"]):
        pr = merkle.proof(close["_levels"], i)
        assert merkle.verify(r, pr, bytes.fromhex(close["root"]))


def test_close_root_changes_when_fraud_appears(res):
    dates = sorted(res.closes)
    roots = [res.closes[d]["root"] for d in dates]
    assert len(set(roots)) > 10


def test_impact_counters_positive(res):
    im = impact(res)
    assert im["tonnes_protected"] > 0 and im["usd_blocked"] > 0 and im["cars_per_year"] > 0


def test_trust_scores_rank_fraud_projects_lower(res):
    s = res.scores.set_index("project_id").score
    assert s["P03"] < s["P07"] and s["P09"] < 100 and s.between(0, 100).all()
