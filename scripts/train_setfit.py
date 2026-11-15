"""Phase 2 fine-tuning: train a SetFit classifier on the seed corpus.

SetFit fine-tunes a sentence transformer with a contrastive objective on pairs of
same-label / different-label sentences, then fits a logistic-regression head on the
resulting embeddings. 20 examples per class are enough to beat zero-shot NLI.

Human reviewer corrections stored in the database (``human_feedback`` table) are merged
into the training data with ``--with-feedback``; this is the weekly retraining loop that
counters concept drift.

    python scripts/train_setfit.py [--with-feedback] [--epochs 1]

Experiments (issues B2 and B3):

    # "before" model for the negation comparison: the original 140-row corpus only
    head -n 141 data/seed_corpus.csv > /tmp/seed_before_b2.csv
    python scripts/train_setfit.py --corpus /tmp/seed_before_b2.csv --output models/setfit_before_b2

    # multilingual base model, optionally with the Hinglish seed examples
    python scripts/train_setfit.py --base-model sentence-transformers/paraphrase-multilingual-mpnet-base-v2 \
        --output models/setfit_multilingual
    python scripts/train_setfit.py --base-model sentence-transformers/paraphrase-multilingual-mpnet-base-v2 \
        --with-hinglish --output models/setfit_multilingual_hinglish
"""

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import auditor  # noqa: F401, E402
import torch  # noqa: F401, E402

import argparse  # noqa: E402
import pandas as pd  # noqa: E402

from auditor.config import PROJECT_ROOT, get_settings  # noqa: E402
from auditor.taxonomy import LABEL_KEYS  # noqa: E402


def load_training_frame(with_feedback: bool, corpus: Path | None = None,
                        with_hinglish: bool = False) -> pd.DataFrame:
    df = pd.read_csv(corpus or PROJECT_ROOT / "data" / "seed_corpus.csv")
    if with_hinglish:
        extra = pd.read_csv(PROJECT_ROOT / "data" / "hinglish_seed.csv")
        print(f"Adding {len(extra)} Hinglish seed examples")
        df = pd.concat([df, extra], ignore_index=True)
    if with_feedback:
        from auditor.db import fetch_feedback_examples

        fb = pd.DataFrame(fetch_feedback_examples(), columns=["text", "label"])
        print(f"Adding {len(fb)} human-reviewed examples from the database")
        df = pd.concat([df, fb], ignore_index=True)
    unknown = set(df.label) - set(LABEL_KEYS)
    if unknown:
        raise ValueError(f"Unknown labels in training data: {unknown}")
    return df.drop_duplicates("text")


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--base-model", default="sentence-transformers/paraphrase-mpnet-base-v2")
    parser.add_argument("--epochs", type=int, default=1)
    parser.add_argument("--iterations", type=int, default=20, help="contrastive pairs per example")
    parser.add_argument("--batch-size", type=int, default=16)
    parser.add_argument("--with-feedback", action="store_true")
    parser.add_argument("--corpus", type=Path, default=None,
                        help="training CSV (text,label); default data/seed_corpus.csv")
    parser.add_argument("--with-hinglish", action="store_true",
                        help="also train on data/hinglish_seed.csv (issue B3)")
    parser.add_argument("--output", type=Path, default=get_settings().setfit_model_dir)
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()

    from datasets import Dataset
    from setfit import SetFitModel, Trainer, TrainingArguments

    df = load_training_frame(args.with_feedback, args.corpus, args.with_hinglish)
    df["label"] = df.label.map(LABEL_KEYS.index)
    print(df.label.map(lambda i: LABEL_KEYS[i]).value_counts().to_string())

    train_ds = Dataset.from_pandas(df[["text", "label"]], preserve_index=False)
    model = SetFitModel.from_pretrained(args.base_model, labels=LABEL_KEYS)

    trainer = Trainer(
        model=model,
        args=TrainingArguments(
            batch_size=args.batch_size,
            num_epochs=args.epochs,
            num_iterations=args.iterations,
            seed=args.seed,
            report_to="none",  # don't auto-enable wandb/tensorboard if installed
            output_dir=str(PROJECT_ROOT / "models" / "_setfit_checkpoints"),
            save_strategy="no",
        ),
        train_dataset=train_ds,
    )
    trainer.train()

    args.output.mkdir(parents=True, exist_ok=True)
    model.save_pretrained(str(args.output))
    print(f"Saved SetFit model to {args.output}")


if __name__ == "__main__":
    main()
