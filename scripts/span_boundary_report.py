"""Strict vs lenient span F1 before and after the boundary re-annotation (issue B4).

* "before": ``data/span_test_v1.txt`` (original gold, mixed conventions)
* "after":  ``data/span_test.txt`` (re-annotated with docs/annotation_guide.md, plus
  confirm-shaming / drip / bait documents)

The regex extractor needs no model. Trained extractors are added with
``--model NAME=DIR``; each is scored with and without the boundary normaliser.

    python scripts/span_boundary_report.py
    python scripts/span_boundary_report.py --model distilbert=models/span_distilbert --model roberta=models/span_roberta

Writes ``reports/span_boundary_comparison.md``.
"""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from auditor.config import PROJECT_ROOT  # noqa: E402
from auditor.extractor import RegexSpanExtractor  # noqa: E402
from auditor.metrics import span_prf  # noqa: E402
from auditor.spans import parse_markup  # noqa: E402
from auditor.taxonomy import BY_KEY  # noqa: E402

DATA = PROJECT_ROOT / "data"


def load(path: Path):
    docs = [parse_markup(l) for l in path.read_text(encoding="utf-8").splitlines() if l.strip()]
    gold = [{(s["label"], s["start"], s["end"]) for s in d["spans"]} for d in docs]
    return docs, gold


def score(extractor, docs, gold):
    pred = [{(BY_KEY[s["category"]].span_tag, s["start"], s["end"]) for s in extractor.extract(d["text"])}
            for d in docs]
    return {m: span_prf(gold, pred, m)["micro"]["f1"] for m in ("strict", "lenient")}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", action="append", default=[], metavar="NAME=DIR")
    args = ap.parse_args()

    v1_docs, v1_gold = load(DATA / "span_test_v1.txt")
    v2_docs, v2_gold = load(DATA / "span_test.txt")
    n_old = len(v1_docs)
    assert [d["text"] for d in v1_docs] == [d["text"] for d in v2_docs[:n_old]], "texts must match"
    gold_counts = (sum(map(len, v1_gold)), sum(map(len, v2_gold[:n_old])), sum(map(len, v2_gold)))

    extractors = {"regex lexicon": RegexSpanExtractor()}
    for item in args.model:
        name, _, path = item.partition("=")
        from auditor.extractor import TransformerSpanExtractor

        extractors[f"{name}"] = TransformerSpanExtractor(Path(path), normalize=False)
        extractors[f"{name} + boundary normaliser"] = TransformerSpanExtractor(Path(path), normalize=True)

    lines = [
        "# Span boundaries: before and after re-annotation (issue B4)\n",
        f"* before gold: `span_test_v1.txt`, {n_old} docs, {gold_counts[0]} spans",
        f"* after gold, same {n_old} docs: re-annotated per `docs/annotation_guide.md`, {gold_counts[1]} spans",
        f"* after gold, full file: {len(v2_docs)} docs, {gold_counts[2]} spans "
        "(adds confirm-shaming, drip pricing, bait and switch)\n",
        "| Extractor | v1 gold strict F1 | v1 lenient F1 | v2 (same 30 docs) strict F1 | v2 lenient F1 | v2 full strict F1 | v2 full lenient F1 |",
        "|---|---|---|---|---|---|---|",
    ]
    for name, ex in extractors.items():
        a = score(ex, v1_docs, v1_gold)
        b = score(ex, v2_docs[:n_old], v2_gold[:n_old])
        c = score(ex, v2_docs, v2_gold)
        lines.append(f"| {name} | {a['strict']:.3f} | {a['lenient']:.3f} | {b['strict']:.3f} | "
                     f"{b['lenient']:.3f} | {c['strict']:.3f} | {c['lenient']:.3f} |")
    if not args.model:
        lines.append("\nNo trained extractor was supplied; add `--model NAME=DIR` "
                     "(see `scripts/train_span_extractor.py`) to include DistilBERT and RoBERTa rows.")
    out = PROJECT_ROOT / "reports" / "span_boundary_comparison.md"
    out.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
