"""A2: how many labelled examples does SetFit need?

Trains SetFit on k = 2, 5, 10, 15, 20 examples per class (3 seeds each), evaluates every model on
``data/test_set.csv`` with the same decision rule as ``scripts/evaluate.py``, and plots accuracy vs. k with
the zero-shot and regex results as horizontal reference lines.

    python scripts/learning_curve.py                 # full experiment (GPU recommended; downloads models)
    python scripts/learning_curve.py --no-zero-shot  # skip the bart-large-mnli reference line
    python scripts/learning_curve.py --dry-run       # fast plumbing check with TF-IDF + logistic regression

Outputs: ``reports/learning_curve.csv`` (every run), ``reports/learning_curve.md`` (table) and
``reports/learning_curve.png``. A ``--dry-run`` writes to a temp directory and its numbers are NOT results.

Notes on reading the plot:
* ``data/seed_corpus.csv`` has exactly 20 examples per class, so at k = 20 every seed trains on the same
  data and the spread only reflects training randomness (pair sampling), not data selection.
* Each k < 20 uses a different random subset per seed (stratified: k per class).
"""

from __future__ import annotations

import argparse
import sys
import tempfile
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

from auditor.config import PROJECT_ROOT  # noqa: E402
from auditor.lexicon import regex_hits  # noqa: E402
from auditor.taxonomy import LABEL_KEYS, SAFE  # noqa: E402

DEFAULT_KS = [2, 5, 10, 15, 20]
DEFAULT_SEEDS = [0, 1, 2]


# --------------------------------------------------------------------------- data / metrics
def sample_per_class(df: pd.DataFrame, k: int, seed: int) -> pd.DataFrame:
    """Stratified subset: exactly ``k`` examples of every class, reproducible for a given seed."""
    counts = df.label.value_counts()
    short = counts[counts < k]
    if len(short):
        raise ValueError(f"cannot draw {k} per class; too few examples for: {short.to_dict()}")
    parts = [g.sample(n=k, random_state=seed) for _, g in df.groupby("label", sort=True)]
    return pd.concat(parts).sample(frac=1, random_state=seed).reset_index(drop=True)


def predict_with(classifier, texts: list[str]) -> list[str]:
    """Same rule as scripts/evaluate.py: sentence scores -> document scores -> violation vs. safe."""
    from auditor.classifier import score_documents

    preds = []
    for ds in score_documents(texts, classifier=classifier):
        key, score = ds.top_violation
        preds.append(key if score > ds.scores[SAFE.key] else SAFE.key)
    return preds


def predict_regex(texts: list[str]) -> list[str]:
    preds = []
    for t in texts:
        hits = {k: len(v) for k, v in regex_hits(t).items()}
        preds.append(max(hits, key=hits.get) if hits else SAFE.key)
    return preds


def score(labels: list[str], preds: list[str]) -> tuple[float, float]:
    from sklearn.metrics import accuracy_score, f1_score

    return (accuracy_score(labels, preds),
            f1_score(labels, preds, labels=sorted(set(labels)), average="macro", zero_division=0))


# --------------------------------------------------------------------------- classifiers under test
class InMemorySetFit:
    """Adapter giving a freshly trained SetFitModel the ``predict_proba(sentences)`` interface."""

    name = "setfit"

    def __init__(self, model):
        self._model = model

    def predict_proba(self, sentences):
        if not sentences:
            return []
        probs = self._model.predict_proba(sentences, as_numpy=True)
        return [{k: float(p) for k, p in zip(LABEL_KEYS, row)} for row in probs]


class TfidfClassifier:
    """Cheap stand-in used only by ``--dry-run`` to verify the plumbing without any model download."""

    name = "tfidf-dry-run"

    def __init__(self, train: pd.DataFrame):
        from sklearn.feature_extraction.text import TfidfVectorizer
        from sklearn.linear_model import LogisticRegression

        self._vec = TfidfVectorizer(ngram_range=(1, 2), sublinear_tf=True)
        self._clf = LogisticRegression(max_iter=1000).fit(self._vec.fit_transform(train.text), train.label)

    def predict_proba(self, sentences):
        if not sentences:
            return []
        p = self._clf.predict_proba(self._vec.transform(sentences))
        cols = list(self._clf.classes_)
        return [{k: float(row[cols.index(k)]) if k in cols else 0.0 for k in LABEL_KEYS} for row in p]


def train_setfit(train: pd.DataFrame, args, seed: int):
    from datasets import Dataset
    from setfit import SetFitModel, Trainer, TrainingArguments

    data = train.assign(label=train.label.map(LABEL_KEYS.index))
    model = SetFitModel.from_pretrained(args.base_model, labels=LABEL_KEYS)
    trainer = Trainer(
        model=model,
        args=TrainingArguments(
            batch_size=args.batch_size, num_epochs=args.epochs, num_iterations=args.iterations,
            seed=seed, report_to="none", save_strategy="no",
            output_dir=str(Path(tempfile.gettempdir()) / "_setfit_lc_checkpoints"),
        ),
        train_dataset=Dataset.from_pandas(data[["text", "label"]], preserve_index=False),
    )
    trainer.train()
    return InMemorySetFit(model)


def free_memory():
    try:
        import gc

        import torch

        gc.collect()
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
    except Exception:
        pass


# --------------------------------------------------------------------------- aggregation / plot
def summarise(runs: pd.DataFrame) -> pd.DataFrame:
    g = runs.groupby("k")
    return pd.DataFrame({
        "n_runs": g.accuracy.size(),
        "acc_mean": g.accuracy.mean(), "acc_std": g.accuracy.std(ddof=1).fillna(0.0),
        "acc_min": g.accuracy.min(), "acc_max": g.accuracy.max(),
        "f1_mean": g.macro_f1.mean(), "f1_std": g.macro_f1.std(ddof=1).fillna(0.0),
    }).reset_index()


def plot_curve(summary: pd.DataFrame, refs: dict[str, float], path: Path, title_suffix: str = "",
               model_name: str = "SetFit"):
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    fig, ax = plt.subplots(figsize=(7, 4.4), dpi=150)
    ax.plot(summary.k, summary.acc_mean, marker="o", color="#2563eb", label=f"{model_name} (mean of seeds)")
    ax.fill_between(summary.k, summary.acc_min, summary.acc_max, color="#2563eb", alpha=0.18,
                    label=f"{model_name} (min to max over seeds)")
    ax.errorbar(summary.k, summary.acc_mean, yerr=summary.acc_std, fmt="none", ecolor="#1d4ed8", capsize=3)
    styles = {"zero-shot": ("#dc2626", "--"), "regex": ("#16a34a", ":")}
    for name, val in refs.items():
        color, ls = styles.get(name, ("#64748b", "-."))
        ax.axhline(val, color=color, linestyle=ls, label=f"{name} ({val:.3f})")
    ax.set_xticks(list(summary.k))
    ax.set_xlabel("Training examples per class")
    ax.set_ylabel("Accuracy on data/test_set.csv")
    ax.set_ylim(0, 1.02)
    ax.set_title(f"{model_name} learning curve" + title_suffix)
    ax.grid(alpha=0.3)
    ax.legend(loc="lower right", fontsize=8)
    fig.tight_layout()
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path)
    plt.close(fig)


def markdown_table(summary: pd.DataFrame, refs: dict[str, float]) -> str:
    lines = ["| Examples / class | Runs | Accuracy (mean ± std) | Min – Max | Macro-F1 (mean ± std) |",
             "|---|---|---|---|---|"]
    for r in summary.itertuples():
        lines.append(f"| {r.k} | {r.n_runs} | {r.acc_mean:.3f} ± {r.acc_std:.3f} | "
                     f"{r.acc_min:.3f} – {r.acc_max:.3f} | {r.f1_mean:.3f} ± {r.f1_std:.3f} |")
    if refs:
        lines += ["", "Reference lines: " + ", ".join(f"{k} = {v:.3f}" for k, v in refs.items())]
    return "\n".join(lines)


# --------------------------------------------------------------------------- main
def run_experiment(train_df, test_df, ks, seeds, make_classifier):
    """Core loop (separated from CLI/IO so it can be unit-tested). ``make_classifier(train, seed)``."""
    texts, labels = test_df.text.tolist(), test_df.label.tolist()
    rows = []
    for k in ks:
        for seed in seeds:
            sub = sample_per_class(train_df, k, seed)
            t0 = time.perf_counter()
            clf = make_classifier(sub, seed)
            acc, f1 = score(labels, predict_with(clf, texts))
            rows.append({"k": k, "seed": seed, "accuracy": acc, "macro_f1": f1,
                         "seconds": round(time.perf_counter() - t0, 1)})
            print(f"k={k:>2} seed={seed}  acc={acc:.3f}  macro-F1={f1:.3f}  ({rows[-1]['seconds']}s)", flush=True)
            del clf
            free_memory()
    return pd.DataFrame(rows)


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--train", type=Path, default=PROJECT_ROOT / "data" / "seed_corpus.csv")
    p.add_argument("--test", type=Path, default=PROJECT_ROOT / "data" / "test_set.csv")
    p.add_argument("--ks", type=int, nargs="+", default=DEFAULT_KS)
    p.add_argument("--seeds", type=int, nargs="+", default=DEFAULT_SEEDS)
    p.add_argument("--base-model", default="sentence-transformers/paraphrase-mpnet-base-v2")
    p.add_argument("--epochs", type=int, default=1)
    p.add_argument("--iterations", type=int, default=20)
    p.add_argument("--batch-size", type=int, default=16)
    p.add_argument("--no-zero-shot", action="store_true", help="skip the bart-large-mnli reference line")
    p.add_argument("--out-dir", type=Path, default=None)
    p.add_argument("--dry-run", action="store_true", help="TF-IDF stand-in; verifies plumbing only")
    args = p.parse_args()

    out_dir = args.out_dir or (Path(tempfile.mkdtemp(prefix="lc_dry_run_")) if args.dry_run
                               else PROJECT_ROOT / "reports")
    train_df, test_df = pd.read_csv(args.train), pd.read_csv(args.test)
    labels = test_df.label.tolist()

    refs = {"regex": score(labels, predict_regex(test_df.text.tolist()))[0]}
    if not args.dry_run and not args.no_zero_shot:
        from auditor.classifier import ZeroShotClassifier

        refs["zero-shot"] = score(labels, predict_with(ZeroShotClassifier(), test_df.text.tolist()))[0]
        free_memory()

    if args.dry_run:
        print("DRY RUN: TF-IDF + logistic regression stand-in. These numbers are NOT SetFit results.")
        make = lambda sub, seed: TfidfClassifier(sub)  # noqa: E731
    else:
        make = lambda sub, seed: train_setfit(sub, args, seed)  # noqa: E731

    runs = run_experiment(train_df, test_df, args.ks, args.seeds, make)
    summary = summarise(runs)

    out_dir.mkdir(parents=True, exist_ok=True)
    runs.to_csv(out_dir / "learning_curve.csv", index=False)
    plot_curve(summary, refs, out_dir / "learning_curve.png",
               " (DRY RUN)" if args.dry_run else "", "TF-IDF stand-in" if args.dry_run else "SetFit")
    table = markdown_table(summary, refs)
    header = "# SetFit learning curve\n\n" + (
        "> DRY RUN with a TF-IDF stand-in. Not a result.\n\n" if args.dry_run else
        f"Test set: `{args.test.name}` ({len(test_df)} items). Seeds: {args.seeds}. "
        f"Base model: `{args.base_model}`.\n\n")
    (out_dir / "learning_curve.md").write_text(header + table + "\n", encoding="utf-8")
    print("\n" + table + f"\n\nWrote results to {out_dir}")


if __name__ == "__main__":
    main()
