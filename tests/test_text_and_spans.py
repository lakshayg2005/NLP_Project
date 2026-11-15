from auditor.metrics import bio_to_entities, entity_prf
from auditor.spans import char_spans_to_token_labels, parse_markup
from auditor.text_utils import merge_spans, split_sentences


def test_parse_markup_offsets():
    doc = parse_markup("Hurry, [[URGENCY|only 3 left]]! [[CLAIM|Cures acne]].")
    assert doc["text"] == "Hurry, only 3 left! Cures acne."
    got = [(doc["text"][s["start"]:s["end"]], s["label"]) for s in doc["spans"]]
    assert got == [("only 3 left", "URGENCY"), ("Cures acne", "CLAIM")]


def test_token_labels_bio():
    # offsets for tokens: [CLS] hurry , only 3 left ! [SEP]
    offsets = [(0, 0), (0, 5), (5, 6), (7, 11), (12, 13), (14, 18), (18, 19), (0, 0)]
    spans = [{"start": 7, "end": 18, "label": "URGENCY"}]
    assert char_spans_to_token_labels(offsets, spans) == [
        "IGNORE", "O", "O", "B-URGENCY", "I-URGENCY", "I-URGENCY", "O", "IGNORE",
    ]


def test_split_sentences_offsets():
    text = "First one. Second one!  Third?"
    sents = split_sentences(text)
    assert [s[2] for s in sents] == ["First one.", "Second one!", "Third?"]
    assert all(text[s:e] == t for s, e, t in sents)


def test_merge_spans():
    spans = [
        {"start": 0, "end": 5, "category": "a", "score": 0.5},
        {"start": 3, "end": 9, "category": "a", "score": 0.9},
        {"start": 4, "end": 6, "category": "b", "score": 0.1},
    ]
    merged = merge_spans(spans)
    assert {(m["start"], m["end"], m["category"], m["score"]) for m in merged} == {
        (0, 9, "a", 0.9), (4, 6, "b", 0.1)
    }


def test_bio_entities_and_prf():
    gold = [["B-X", "I-X", "O", "B-Y"]]
    pred = [["B-X", "I-X", "O", "O"]]
    assert bio_to_entities(gold[0]) == {("X", 0, 2), ("Y", 3, 4)}
    report = entity_prf(gold, pred)
    assert report["micro"]["precision"] == 1.0
    assert report["micro"]["recall"] == 0.5
    assert report["Y"]["f1"] == 0.0


def test_lenient_matching_counts_overlap():
    gold = [["B-X", "I-X", "I-X", "O"]]
    pred = [["O", "B-X", "I-X", "O"]]  # shorter span, same type
    assert entity_prf(gold, pred, "strict")["micro"]["f1"] == 0.0
    assert entity_prf(gold, pred, "lenient")["micro"]["f1"] == 1.0


def test_join_fragments():
    from auditor.extractor import _join_fragments

    text = "It balances hormones and prevents illness."
    spans = [
        {"start": 3, "end": 20, "category": "c", "score": 0.9},
        {"start": 25, "end": 41, "category": "c", "score": 0.7},
    ]
    [joined] = _join_fragments(text, spans)
    assert text[joined["start"]:joined["end"]] == "balances hormones and prevents illness"


def test_normalize_boundaries_strips_edge_words():
    from auditor.extractor import normalize_boundaries

    text = "Grab it now, the timer says 4 minutes left. Hurry!"
    start = text.index("the timer")
    span = {"start": start, "end": text.index(".") + 1, "category": "deceptive_urgency", "score": 1.0}
    [out] = normalize_boundaries(text, [span])
    assert text[out["start"]:out["end"]] == "timer says 4 minutes left"


def test_normalize_boundaries_keeps_clean_span_and_single_word():
    from auditor.extractor import normalize_boundaries

    text = "Hurry, only 2 left in stock"
    span = {"start": 7, "end": len(text), "category": "deceptive_urgency", "score": 1.0}
    assert normalize_boundaries(text, [span])[0]["start"] == 7
    tiny = {"start": 0, "end": 3, "category": "deceptive_urgency", "score": 1.0}
    assert normalize_boundaries("The", [tiny])[0]["end"] == 3  # never empties a span


def test_annotation_files_follow_the_guide():
    import importlib.util
    import re

    from auditor.config import PROJECT_ROOT

    spec = importlib.util.spec_from_file_location("lint", PROJECT_ROOT / "scripts" / "lint_annotations.py")
    lint = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(lint)
    bad = []
    for path in lint.FILES:
        for tag, phrase in lint.SPAN.findall(path.read_text(encoding="utf-8")):
            if lint.problems(phrase, tag):
                bad.append((path.name, phrase))
    assert not bad, bad


def test_span_test_set_covers_every_violation_type():
    from auditor.config import PROJECT_ROOT
    from auditor.taxonomy import VIOLATIONS

    lines = (PROJECT_ROOT / "data" / "span_test.txt").read_text(encoding="utf-8").splitlines()
    docs = [parse_markup(l) for l in lines if l.strip()]
    seen = {s["label"] for d in docs for s in d["spans"]}
    assert seen == {c.span_tag for c in VIOLATIONS}
