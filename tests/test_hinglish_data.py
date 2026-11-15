"""B3: Hinglish data sets are balanced, valid and do not leak into each other."""

import csv
from collections import Counter

from auditor.config import PROJECT_ROOT
from auditor.taxonomy import LABEL_KEYS


def read(name):
    with (PROJECT_ROOT / "data" / name).open(encoding="utf-8") as f:
        return list(csv.DictReader(f))


def test_hinglish_seed_has_15_or_more_per_category():
    counts = Counter(r["label"] for r in read("hinglish_seed.csv"))
    assert set(counts) == set(LABEL_KEYS)
    assert min(counts.values()) >= 15


def test_hinglish_test_set_has_40_or_more_and_every_label():
    rows = read("hinglish_test.csv")
    assert len(rows) >= 40
    assert {r["label"] for r in rows} == set(LABEL_KEYS)


def test_no_overlap_between_hinglish_seed_and_test_or_english_sets():
    seed = {r["text"].strip().lower() for r in read("hinglish_seed.csv")}
    test = {r["text"].strip().lower() for r in read("hinglish_test.csv")}
    english = {r["text"].strip().lower() for r in read("seed_corpus.csv") + read("test_set.csv")}
    assert not seed & test and not (seed | test) & english


def test_hinglish_is_roman_script():
    for r in read("hinglish_seed.csv") + read("hinglish_test.csv"):
        assert r["text"].isascii(), r["text"]
