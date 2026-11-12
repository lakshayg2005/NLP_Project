import pandas as pd
import pytest

from auditor.config import PROJECT_ROOT
from auditor.taxonomy import LABEL_KEYS
from scripts import annotation_agreement as aa

U, C, S = "deceptive_urgency", "unsubstantiated_claims", "safe"


def test_kappa_hand_computed_value():
    # 4 items: observed agreement 3/4; chance agreement 0.5*0.25 + 0.5*0.75 = 0.5 -> kappa = 0.5
    a = {"1": U, "2": U, "3": S, "4": S}
    b = {"1": U, "2": S, "3": S, "4": S}
    res = aa.agreement(a, b)
    assert res["kappa"] == pytest.approx(0.5)
    assert res["raw_agreement"] == 0.75
    assert res["disagree_ids"] == ["2"]
    assert res["confusion"].loc[U, S] == 1


def test_perfect_agreement_and_mismatched_ids():
    a = {"1": U, "2": C, "3": S}
    assert aa.agreement(a, dict(a))["kappa"] == pytest.approx(1.0)
    with pytest.raises(SystemExit):
        aa.agreement(a, {"1": U, "2": C})


@pytest.mark.parametrize("k,band", [(-0.1, "poor"), (0.1, "slight"), (0.3, "fair"), (0.5, "moderate"),
                                    (0.7, "substantial"), (0.9, "almost perfect"), (float("nan"), "undefined")])
def test_interpret_bands(k, band):
    assert aa.interpret(k) == band


def test_read_labels_rejects_blank_and_unknown(tmp_path):
    blank = tmp_path / "blank.csv"
    pd.DataFrame({"id": ["a", "b"], "text": ["x", "y"], "label": [U, ""]}).to_csv(blank, index=False)
    with pytest.raises(SystemExit):
        aa.read_labels(blank)
    unknown = tmp_path / "unknown.csv"
    pd.DataFrame({"id": ["a"], "text": ["x"], "label": ["urgent"]}).to_csv(unknown, index=False)
    with pytest.raises(SystemExit):
        aa.read_labels(unknown)


def test_build_final_uses_resolution_only_for_disagreements():
    cands = pd.DataFrame({"id": ["1", "2"], "text": ["t1", "t2"]})
    a, b = {"1": U, "2": U}, {"1": U, "2": C}
    with pytest.raises(SystemExit):
        aa.build_final(cands, a, b, {})
    final = aa.build_final(cands, a, b, {"2": S, "1": C})    # resolution for item 1 must be ignored
    assert final.label.tolist() == [U, S]


def test_validate_final_flags_short_classes():
    df = pd.DataFrame({"text": [f"t{i}" for i in range(210)], "label": [LABEL_KEYS[i % 7] for i in range(210)]})
    assert aa.validate_final(df) == []
    short = df.drop(df[df.label == S].index[:1])
    assert any(S in p for p in aa.validate_final(short))
    assert aa.validate_final(df.head(100))


def test_near_duplicates():
    ref = ["Hurry! Only 2 left in stock - this deal disappears at midnight."]
    hits = aa.near_duplicates({"x": "hurry only 2 left in stock this deal disappears at midnight",
                               "y": "Blue cotton socks, machine washable."}, ref)
    assert [h[0] for h in hits] == ["x"]


def test_candidate_pool_integrity_and_no_leakage():
    cands = pd.read_csv(aa.CANDIDATES)
    drafter = pd.read_csv(aa.DRAFTER)
    assert cands.id.is_unique and cands.text.is_unique
    assert list(cands.id) == list(drafter.id)
    assert set(drafter.label) == set(LABEL_KEYS)
    # slack above the 30/class acceptance bar, so resolving disagreements cannot push a class below it
    assert (drafter.label.value_counts() >= aa.MIN_PER_CLASS + 5).all()
    ref = []
    for name in ("seed_corpus.csv", "test_set.csv"):
        ref += pd.read_csv(PROJECT_ROOT / "data" / name).text.tolist()
    assert aa.near_duplicates(dict(zip(cands.id, cands.text)), ref) == []


def test_end_to_end_workflow_with_simulated_annotators(tmp_path, monkeypatch):
    """Plumbing check only: simulated annotators (drafter labels + noise), not a real agreement result."""
    import argparse
    import random

    drafter = pd.read_csv(aa.DRAFTER)
    cands = pd.read_csv(aa.CANDIDATES)
    sheet_a, sheet_b = tmp_path / "a.csv", tmp_path / "b.csv"
    for path, seed in ((sheet_a, 1), (sheet_b, 2)):
        rng = random.Random(seed)
        labs = [rng.choice(LABEL_KEYS) if rng.random() < 0.08 else y for y in drafter.label]
        cands.assign(label=labs).to_csv(path, index=False)

    monkeypatch.setattr(aa, "DISAGREEMENTS", tmp_path / "dis.csv")
    monkeypatch.setattr(aa, "REPORT", tmp_path / "report.md")
    monkeypatch.setattr(aa, "OUT_TEST_V2", tmp_path / "test_v2.csv")

    aa.cmd_kappa(argparse.Namespace(a=sheet_a, b=sheet_b, drafter=aa.DRAFTER))
    report = (tmp_path / "report.md").read_text(encoding="utf-8")
    assert "Cohen's kappa" in report and "Per-class kappa" in report

    # unresolved disagreements must block the merge
    with pytest.raises(SystemExit):
        aa.cmd_merge(argparse.Namespace(a=sheet_a, b=sheet_b, resolved=tmp_path / "dis.csv", allow_overlap=False))

    dis = pd.read_csv(tmp_path / "dis.csv", dtype=str, keep_default_na=False)
    truth = dict(zip(drafter.id, drafter.label))
    dis["final_label"] = dis.id.map(truth)
    dis.to_csv(tmp_path / "dis.csv", index=False)
    aa.cmd_merge(argparse.Namespace(a=sheet_a, b=sheet_b, resolved=tmp_path / "dis.csv", allow_overlap=False))
    out = pd.read_csv(tmp_path / "test_v2.csv")
    assert len(out) == 245 and set(out.label) == set(LABEL_KEYS)
