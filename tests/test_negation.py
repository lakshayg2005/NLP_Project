import csv
from pathlib import Path

import pytest

from auditor.heuristics import screen
from auditor.lexicon import regex_hits
from auditor.negation import is_negated

ROWS = list(csv.DictReader((Path(__file__).resolve().parent.parent / "data" / "negation_test.csv")
                           .open(encoding="utf-8")))
SAFE = [r["text"] for r in ROWS if r["label"] == "safe"]
BAD = [(r["text"], r["label"]) for r in ROWS if r["label"] != "safe"]


def test_negation_test_set_is_big_enough():
    assert len(SAFE) >= 30


@pytest.mark.parametrize("text", SAFE)
def test_negated_copy_has_no_regex_hit(text):
    assert regex_hits(text) == {}


@pytest.mark.parametrize("text", SAFE)
def test_negated_copy_is_not_suspicious(text):
    assert not screen(text, use_semantic=False).suspicious


@pytest.mark.parametrize("text,category", BAD)
def test_real_violation_with_negation_still_flagged(text, category):
    assert category in regex_hits(text)


def test_known_failure_pay_once():
    assert regex_hits("Pay once, there are no recurring fees.") == {}


def test_raw_hits_still_available():
    assert "subscription_trap" in regex_hits("There are no recurring fees.", skip_negated=False)


@pytest.mark.parametrize("text,start,expected", [
    ("no hidden fees", 3, True),
    ("does not auto-renew", 9, True),
    ("No thanks, only 2 left", 11, False),        # comma ends the clause
    ("You can't cancel online", 10, False),       # can't is not a reassuring cue
    ("Not intended to diagnose, treat, or cure", 36, True),   # comma list under one cue
    ("No setup fees or activation fees", 18, True),            # coordinated noun phrase
])
def test_is_negated(text, start, expected):
    assert is_negated(text, start) is expected


def test_confirm_shaming_is_not_cancelled_by_its_own_no():
    assert "confirm_shaming" in regex_hits("No thanks, I hate saving money and prefer paying full price.")
