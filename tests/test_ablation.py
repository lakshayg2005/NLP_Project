import pandas as pd
import pytest

from auditor.config import PROJECT_ROOT, get_settings
from scripts import ablation as ab

TEST = pd.read_csv(PROJECT_ROOT / "data" / "test_set.csv")
TEXTS, LABELS = TEST.text.tolist(), TEST.label.tolist()


def test_route_matches_pipeline_decisions(stub_models):
    """The script's explicit-threshold router must agree with the production pipeline."""
    from auditor.pipeline import audit_many

    s = get_settings()
    _, decisions, _, _ = ab.run_config(TEXTS, LABELS, "regex", stub_models, s.flag_threshold,
                                       s.review_threshold, warm_up=False)
    for (status, cats), r in zip(decisions, audit_many(TEXTS)):
        assert status == r.status
        if status == ab.FLAGGED:
            assert cats == {f.category for f in r.flags}


def test_phase1_gate_reduces_transformer_load(stub_models):
    a, *_ = ab.run_config(TEXTS, LABELS, "none", stub_models, 0.7, 0.5, warm_up=False)
    b, *_ = ab.run_config(TEXTS, LABELS, "regex", stub_models, 0.7, 0.5, warm_up=False)
    assert a["reached_transformer"] == len(TEXTS)
    assert b["reached_transformer"] < a["reached_transformer"]
    for r in (a, b):
        assert r["n_auto"] + r["n_review"] == len(TEXTS)
        assert 0 <= r["accuracy_auto"] <= 1


def test_sweep_contains_current_setting_and_is_consistent(stub_models):
    res, _, suspicious, doc_scores = ab.run_config(TEXTS, LABELS, "regex", stub_models, 0.7, 0.5, warm_up=False)
    df = ab.sweep(TEXTS, LABELS, suspicious, doc_scores)
    assert (df.review_threshold <= df.flag_threshold).all()
    row = df[(df.flag_threshold == 0.7) & (df.review_threshold == 0.5)].iloc[0]
    assert row.n_review == res["n_review"] and row.accuracy_auto == pytest.approx(res["accuracy_auto"])


def test_pareto_frontier_keeps_only_undominated_points():
    df = pd.DataFrame({"review_share": [0.0, 0.1, 0.2, 0.3], "accuracy_auto": [0.80, 0.78, 0.90, 0.90]})
    assert ab.pareto_frontier(df).index.tolist() == [0, 2]


def test_report_and_plot_are_written(stub_models, tmp_path):
    results = {}
    for name, mode in ab.CONFIGS.items():
        mode = "regex" if mode == "regex+semantic" else mode      # avoid the embedding model in unit tests
        results[name], _, susp, scores = ab.run_config(TEXTS, LABELS, mode, stub_models, 0.7, 0.5, warm_up=False)
    df = ab.sweep(TEXTS, LABELS, susp, scores)
    png = tmp_path / "ablation_sweep.png"
    ab.plot_sweep(df, (0.7, 0.5), png)
    ab.write_report(tmp_path / "ablation.md", "`test_set.csv`", "stub", results, df, (0.7, 0.5), png)
    text = (tmp_path / "ablation.md").read_text(encoding="utf-8")
    assert png.exists() and "## Design comparison" in text and "## Findings" in text
