"""English-only vs multilingual SetFit on English and Hinglish test sets (issue B3).

    python scripts/compare_models.py \\
        --model english=models/setfit \\
        --model multilingual=models/setfit_multilingual \\
        --model multilingual+hinglish=models/setfit_multilingual_hinglish

The regex lexicon is always scored (it needs no model) as the offline reference.
Writes ``reports/hinglish_comparison.md`` including a recommendation derived from the numbers.

Train the models first (see ``scripts/train_setfit.py``)::

    python scripts/train_setfit.py --output models/setfit
    python scripts/train_setfit.py --base-model sentence-transformers/paraphrase-multilingual-mpnet-base-v2 \\
        --output models/setfit_multilingual
    python scripts/train_setfit.py --base-model sentence-transformers/paraphrase-multilingual-mpnet-base-v2 \\
        --with-hinglish --output models/setfit_multilingual_hinglish
"""

import argparse
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pandas as pd  # noqa: E402
from sklearn.metrics import accuracy_score, f1_score  # noqa: E402

from auditor.config import PROJECT_ROOT  # noqa: E402
from auditor.lexicon import regex_hits  # noqa: E402
from auditor.taxonomy import SAFE  # noqa: E402

SETS = {"English (test_set.csv)": "test_set.csv", "Hinglish (hinglish_test.csv)": "hinglish_test.csv"}
MAX_ENGLISH_DROP = 0.03   # a multilingual model may lose at most this much English accuracy
MIN_HINGLISH_GAIN = 0.05  # ... and must gain at least this much Hinglish accuracy


def predict_regex(texts):
    preds = []
    for t in texts:
        hits = {k: len(v) for k, v in regex_hits(t).items()}
        preds.append(max(hits, key=hits.get) if hits else SAFE.key)
    return preds


def predict_setfit(model_dir, texts):
    from auditor.classifier import SetFitClassifier, score_documents

    clf = SetFitClassifier(Path(model_dir))
    preds = []
    for ds in score_documents(texts, classifier=clf):
        key, score = ds.top_violation
        preds.append(key if score > ds.scores[SAFE.key] else SAFE.key)
    return preds


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", action="append", default=[], metavar="NAME=DIR")
    ap.add_argument("--out", type=Path, default=PROJECT_ROOT / "reports" / "hinglish_comparison.md")
    args = ap.parse_args()

    data = {name: pd.read_csv(PROJECT_ROOT / "data" / f) for name, f in SETS.items()}
    systems = {"regex lexicon (reference)": predict_regex}
    for item in args.model:
        name, _, path = item.partition("=")
        systems[f"SetFit: {name}"] = lambda texts, p=path: predict_setfit(p, texts)

    rows, acc = [], {}
    for sys_name, fn in systems.items():
        for set_name, df in data.items():
            t0 = time.perf_counter()
            preds = fn(df.text.tolist())
            ms = (time.perf_counter() - t0) * 1000 / len(df)
            a = accuracy_score(df.label, preds)
            f = f1_score(df.label, preds, average="macro", zero_division=0)
            acc[(sys_name, set_name)] = a
            rows.append(f"| {sys_name} | {set_name} | {len(df)} | {a:.3f} | {f:.3f} | {ms:.1f} |")

    lines = ["# English-only vs multilingual model (issue B3)\n",
             "| System | Test set | N | Accuracy | Macro-F1 | ms / item |", "|---|---|---|---|---|---|", *rows, ""]

    en, hi = list(SETS)
    names = [n for n in systems if n.startswith("SetFit: ")]
    if len(names) >= 2:
        base = names[0]
        lines.append(f"## Recommendation (baseline = `{base}`)\n")
        best, best_gain = base, 0.0
        for n in names[1:]:
            gain, drop = acc[(n, hi)] - acc[(base, hi)], acc[(base, en)] - acc[(n, en)]
            ok = gain >= MIN_HINGLISH_GAIN and drop <= MAX_ENGLISH_DROP
            lines.append(f"- `{n}`: Hinglish {gain:+.3f}, English {-drop:+.3f} -> "
                         f"{'meets' if ok else 'does not meet'} the rule "
                         f"(Hinglish gain >= {MIN_HINGLISH_GAIN}, English drop <= {MAX_ENGLISH_DROP})")
            if ok and gain > best_gain:
                best, best_gain = n, gain
        lines.append(f"\n**Ship `{best}`.** Speed matters too: the multilingual mpnet model is larger than the "
                     "English one, so check the ms / item column before deciding.")
    else:
        lines.append("Only the regex reference was scored. Add `--model NAME=DIR` for trained SetFit models "
                     "(commands in the docstring of this script) to get the comparison and recommendation.")
    lines.append("\nNote: Phase 1's embedding filter (`all-MiniLM-L6-v2`) is English-only. For Hinglish traffic "
                 "set `EMBEDDING_MODEL=sentence-transformers/paraphrase-multilingual-mpnet-base-v2` "
                 "or rely on the regex branch.")
    args.out.parent.mkdir(exist_ok=True)
    args.out.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
