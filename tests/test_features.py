import pytest

from engine import casefile, greenwash, merkle, ndvi_sim, passport, score
from engine.common import fmt_range, parse_range
from engine.pipeline import flag_dates, run


@pytest.fixture(scope="module")
def res():
    return run()


def test_greenwashing_meridian_is_unsupported(res):
    claim = res.data["corp_claims"].query("claim_id == 'CL9001'").iloc[0]
    out = greenwash.check_claim(claim.company, int(claim.claimed_tco2), res.events, res.flags)
    assert out["verdict"] == "UNSUPPORTED"
    assert out["retired_clean"] <= out["retired_valid"] < out["claimed"]
    assert out["rejected"] == 5000


def test_honest_claims_are_supported(res):
    for c in res.data["corp_claims"].itertuples():
        if c.claim_id == "CL9001":
            continue
        out = greenwash.check_claim(c.company, int(c.claimed_tco2), res.events, res.flags)
        assert out["ratio_valid"] >= 0.9, c.company


def test_passport_double_sold_range_is_blocked(res):
    t = res.events[res.events.event_id == "T9001"].iloc[0]
    p = passport.build(res, int(t.serial_start), int(t.serial_end))
    assert p["verdict"] == "BLOCKED" and any(not e["ok"] for e in p["timeline"])
    assert p["merkle"]["valid"]


def test_passport_unissued_range(res):
    t = res.events[res.events.event_id == "T9003"].iloc[0]
    p = passport.build(res, int(t.serial_start), int(t.serial_end))
    assert not p["issued"] and p["verdict"] == "BLOCKED" and p["merkle"] is None


def test_clean_range_is_safe(res):
    seg = next(s for s in res.ledger.segs if s.project_id == "P07" and s.retired and s.end - s.start > 1200)
    out = score.score_range(seg.start, seg.start + 999, res.flags, res.scores)
    assert out["verdict"] == "SAFE" and out["score"] >= 75


def test_casefile_markdown_and_pdf(res):
    f = next(x for x in res.flags if x["rule_id"] == "R01")
    md, src = casefile.build_markdown(res, f, use_llm=False)
    assert src == "template" and "Merkle proof" in md and f["subject_id"] in md
    assert casefile.to_pdf(md)[:4] == b"%PDF"


def test_ndvi_is_simulated_and_flags_only_p04(res):
    assert ndvi_sim.series("P01").simulated.all()
    d = res.divergence.set_index("project_id")
    assert d.divergence.sum() == 1 and bool(d.loc["P04", "divergence"])


def test_flag_dates_cover_every_flag(res):
    fd = flag_dates(res)
    assert set(fd) == {f["flag_id"] for f in res.flags}


def test_serial_parsing_roundtrip():
    a, b = 2507189, 2508936
    assert parse_range(fmt_range(a, b)) == (a, b)
    assert parse_range("2,507,189 - 2,508,936") == (a, b)


def test_merkle_odd_leaf_counts():
    for n in (1, 2, 3, 5, 8, 13):
        recs = [dict(i=i) for i in range(n)]
        lv = merkle.build_tree([merkle.leaf_hash(r) for r in recs])
        for i, r in enumerate(recs):
            assert merkle.verify(r, merkle.proof(lv, i), merkle.root_of(lv))
