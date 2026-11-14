"""Before/after comparison for the negation fix (issue B2).

Offline part (no models needed): the regex lexicon with negation handling switched off
("before") and on ("after"), on ``data/negation_test.csv`` and ``data/test_set.csv``.

Optional SetFit part: pass two trained model folders.

    python scripts/negation_report.py
    python scripts/negation_report.py --setfit-before models/setfit_before_b2 --setfit-after models/setfit

Writes ``reports/negation_comparison.md``.
"""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pandas as pd  # noqa: E402
from sklearn.metrics import accuracy_score, f1_score  # noqa: E402

from auditor.config import PROJECT_ROOT  # noqa: E402
from auditor.lexicon import regex_hits  # noqa: E402
from auditor.taxonomy import SAFE  # noqa: E402

KNOWN_FAILURE = "Pay once, there are no recurring fees."


def predict_regex(texts, skip_negated):
    preds = []
    for t in texts:
        hits = {k: len(v) for k, v in regex_hits(t, skip_negated=skip_negated).items()}
        preds.append(max(hits, key=hits.get) if hits else SAFE.key)
    return preds


def predict_setfit(model_dir, texts):
    from auditor.classifier import SetFitClassifier, score_documents

    clf = SetFitClassifier(model_dir)
    preds = []
    for ds in score_documents(texts, classifier=clf):
        key, score = ds.top_violation
        preds.append(key if score > ds.scores[SAFE.key] else SAFE.key)
    return preds


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--setfit-before", type=Path)
    ap.add_argument("--setfit-after", type=Path)
    args = ap.parse_args()

    sets = {
        "negation_test.csv": pd.read_csv(PROJECT_ROOT / "data" / "negation_test.csv"),
        "test_set.csv": pd.read_csv(PROJECT_ROOT / "data" / "test_set.csv"),
    }
    systems = {
        "regex, negation off (before)": lambda t: predict_regex(t, False),
        "regex, negation on (after)": lambda t: predict_regex(t, True),
    }
    if args.setfit_before and args.setfit_after:
        systems["SetFit before (corpus without negation examples)"] = lambda t: predict_setfit(args.setfit_before, t)
        systems["SetFit after (corpus with negation examples)"] = lambda t: predict_setfit(args.setfit_after, t)

    lines = ["# Negation fix: before and after (issue B2)\n"]
    lines.append("| System | Test set | N | Accuracy | Macro-F1 |\n|---|---|---|---|---|")
    results = {}
    for name, fn in systems.items():
        for set_name, df in sets.items():
            preds = fn(df.text.tolist())
            results[(name, set_name)] = preds
            acc = accuracy_score(df.label, preds)
            f1 = f1_score(df.label, preds, average="macro", zero_division=0)
            lines.append(f"| {name} | {set_name} | {len(df)} | {acc:.3f} | {f1:.3f} |")

    neg = sets["negation_test.csv"]
    idx = neg.index[neg.text == KNOWN_FAILURE][0]
    lines.append(f"\nKnown failure `{KNOWN_FAILURE}` (gold: safe):\n")
    for name in systems:
        lines.append(f"- {name}: `{results[(name, 'negation_test.csv')][idx]}`")

    after = "regex, negation on (after)"
    wrong = [(t, y, p) for t, y, p in zip(neg.text, neg.label, results[(after, "negation_test.csv")]) if y != p]
    lines.append(f"\nRemaining errors of the negation-aware regex on `negation_test.csv` ({len(wrong)}):\n")
    for t, y, p in wrong:
        lines.append(f"- gold `{y}`, predicted `{p}`: {t}")
    if not (args.setfit_before and args.setfit_after):
        lines.append("\nSetFit rows are omitted: pass `--setfit-before` and `--setfit-after` "
                     "(see `scripts/train_setfit.py` docstring) to add them.")

    out = PROJECT_ROOT / "reports" / "negation_comparison.md"
    out.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
