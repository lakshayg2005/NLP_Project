"""B1: the three CCPA categories are wired through every layer of the project."""

import ast
import csv
from collections import Counter

import pytest

from auditor.config import PROJECT_ROOT
from auditor.lexicon import PATTERNS, PHRASE_BANK, regex_hits
from auditor.spans import parse_markup
from auditor.taxonomy import BY_KEY, BY_TAG, CATEGORIES, LABEL_KEYS, SPAN_LABELS, VIOLATIONS

NEW = ["confirm_shaming", "drip_pricing", "bait_and_switch"]
DATA = PROJECT_ROOT / "data"


def read(name):
    with (DATA / name).open(encoding="utf-8") as f:
        return list(csv.DictReader(f))


def test_taxonomy_has_seven_labels_and_new_categories():
    assert len(CATEGORIES) == 7 and len(VIOLATIONS) == 6
    assert all(k in LABEL_KEYS for k in NEW)
    assert len(SPAN_LABELS) == 1 + 2 * len(VIOLATIONS)
    for key in NEW:
        cat = BY_KEY[key]
        assert cat.span_tag and cat.hypothesis and BY_TAG[cat.span_tag] is cat


@pytest.mark.parametrize("key", NEW)
def test_lexicon_covers_new_category(key):
    assert PATTERNS[key] and len(PHRASE_BANK[key]) >= 5


@pytest.mark.parametrize("key", [c.key for c in VIOLATIONS])
def test_seed_and_test_set_sizes(key):
    seed = Counter(r["label"] for r in read("seed_corpus.csv"))
    test = Counter(r["label"] for r in read("test_set.csv"))
    assert seed[key] >= 20
    assert test[key] >= 10


def test_no_label_outside_taxonomy_and_no_train_test_leak():
    seed, test = read("seed_corpus.csv"), read("test_set.csv")
    assert {r["label"] for r in seed + test} <= set(LABEL_KEYS)
    assert not {r["text"].strip().lower() for r in seed} & {r["text"].strip().lower() for r in test}


@pytest.mark.parametrize("key", NEW)
def test_regex_finds_most_seed_examples_of_new_category(key):
    rows = [r["text"] for r in read("seed_corpus.csv") if r["label"] == key]
    caught = sum(key in regex_hits(t) for t in rows)
    assert caught / len(rows) >= 0.8


def test_span_data_annotates_every_new_tag():
    for name in ("span_seed.txt", "span_test.txt"):
        lines = (DATA / name).read_text(encoding="utf-8").splitlines()
        tags = {s["label"] for l in lines if l.strip() for s in parse_markup(l)["spans"]}
        assert {BY_KEY[k].span_tag for k in NEW} <= tags, name


def test_dashboard_has_a_colour_and_label_for_every_violation():
    tree = ast.parse((PROJECT_ROOT / "dashboard" / "app.py").read_text(encoding="utf-8"))
    tables = {}
    for node in tree.body:
        if isinstance(node, ast.Assign) and isinstance(node.value, ast.Dict) and node.targets[0].id in (
                "COLORS", "SOLID", "SHORT"):
            tables[node.targets[0].id] = {k.value for k in node.value.keys}
    for name in ("COLORS", "SOLID", "SHORT"):
        assert {c.key for c in VIOLATIONS} <= tables[name], name
