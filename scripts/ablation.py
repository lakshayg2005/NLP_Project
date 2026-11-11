"""A3: does each phase of the pipeline earn its place?

Compares three designs on the labelled test set:

  (a) classifier only                  every text goes to the Phase 2 classifier
  (b) regex + classifier               Phase 1 regex gate, then Phase 2
  (c) regex + semantic + classifier    the current design (Phase 1 regex + MiniLM similarity gate, then Phase 2)

For each: accuracy on the items the system decides automatically, how many items reach the transformer,
how many go to human review, and time per item. It then sweeps FLAG_THRESHOLD and REVIEW_THRESHOLD on
design (c) and plots the share of items sent to human review against accuracy on the rest.

    python scripts/ablation.py
    python scripts/ablation.py --data data/test_set_v2.csv --out reports/ablation_v2.md

Phase 3 (span extraction) is not ablated: it never changes the document-level decision, only the
highlighting, so it cannot change these accuracy numbers.

Uses whatever classifier ``auditor.classifier.get_classifier()`` returns: the trained SetFit model if
``models/setfit`` exists, otherwise zero-shot (the report states which). Needs the real models, so run it
on a machine that has them.
"""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pandas as pd  # noqa: E402

from auditor.classifier import score_documents  # noqa: E402
from auditor.config import PROJECT_ROOT, get_settings  # noqa: E402
from auditor.heuristics import screen  # noqa: E402
from auditor.taxonomy import SAFE, VIOLATIONS  # noqa: E402

FLAGGED, NEEDS_REVIEW, PASSED = "Flagged", "Needs Review", "Passed"

CONFIGS = {
    "(a) classifier only": "none",
    "(b) regex + classifier": "regex",
    "(c) regex + semantic + classifier": "regex+semantic",
}
FLAG_GRID = [0.5, 0.6, 0.7, 0.8, 0.9]
REVIEW_GRID = [0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8]


# --------------------------------------------------------------------------- core logic
def route(scores: dict[str, float], flag_t: float, review_t: float) -> tuple[str, set[str]]:
    """Phase 2 routing, identical to ``auditor.pipeline.audit_many`` but with explicit thresholds."""
    flagged = {c.key for c in VIOLATIONS if scores[c.key] >= flag_t}
    if flagged:
        return FLAGGED, flagged
    top = max(scores[c.key] for c in VIOLATIONS)
    if top >= review_t or scores[SAFE.key] < review_t:
        return NEEDS_REVIEW, set()
    return PASSED, set()


def phase1_suspicious(texts: list[str], mode: str) -> list[bool]:
    if mode == "none":
        return [True] * len(texts)
    return [screen(t, use_semantic=(mode == "regex+semantic")).suspicious for t in texts]


def decide(texts, suspicious, doc_scores: dict[int, dict], flag_t: float, review_t: float):
    """Per-item ``(status, flagged_categories)``; items that fail Phase 1 are passed without a transformer."""
    out = []
    for i in range(len(texts)):
        out.append((PASSED, set()) if not suspicious[i] else route(doc_scores[i], flag_t, review_t))
    return out


def summarise_decisions(decisions, labels: list[str]) -> dict:
    n = len(labels)
    review = sum(s == NEEDS_REVIEW for s, _ in decisions)
    correct = auto = 0
    for (status, cats), gold in zip(decisions, labels):
        if status == NEEDS_REVIEW:
            continue
        auto += 1
        correct += (gold in cats) if status == FLAGGED else (gold == SAFE.key)
    return {
        "n": n, "n_auto": auto, "n_review": review, "review_share": review / n if n else float("nan"),
        "accuracy_auto": correct / auto if auto else float("nan"),
    }


def run_config(texts, labels, mode: str, classifier, flag_t: float, review_t: float, warm_up: bool = True):
    """Run one design end to end, timing Phase 1 and Phase 2 separately."""
    if warm_up and texts:                 # keep one-off model load / first-call overhead out of the timing
        phase1_suspicious(texts[:1], mode)
        score_documents(texts[:1], classifier=classifier)

    t0 = time.perf_counter()
    suspicious = phase1_suspicious(texts, mode)
    t1 = time.perf_counter()
    idx = [i for i, s in enumerate(suspicious) if s]
    scored = score_documents([texts[i] for i in idx], classifier=classifier) if idx else []
    t2 = time.perf_counter()

    doc_scores = {i: ds.scores for i, ds in zip(idx, scored)}
    decisions = decide(texts, suspicious, doc_scores, flag_t, review_t)
    n = max(len(texts), 1)
    res = summarise_decisions(decisions, labels)
    res.update({
        "reached_transformer": len(idx), "share_reaching": len(idx) / n,
        "ms_phase1": (t1 - t0) * 1000 / n, "ms_phase2": (t2 - t1) * 1000 / n,
        "ms_total": (t2 - t0) * 1000 / n,
    })
    return res, decisions, suspicious, doc_scores


def sweep(texts, labels, suspicious, doc_scores, flag_grid=FLAG_GRID, review_grid=REVIEW_GRID) -> pd.DataFrame:
    rows = []
    for f in flag_grid:
        for r in review_grid:
            if r > f:                      # a review band above the flag threshold is meaningless
                continue
            s = summarise_decisions(decide(texts, suspicious, doc_scores, f, r), labels)
            rows.append({"flag_threshold": f, "review_threshold": r, **s})
    return pd.DataFrame(rows)


def pareto_frontier(df: pd.DataFrame) -> pd.DataFrame:
    """Settings not beaten on both axes (lower review share AND higher accuracy)."""
    d = df.dropna(subset=["accuracy_auto"]).sort_values(["review_share", "accuracy_auto"], ascending=[True, False])
    keep, best = [], -1.0
    for row in d.itertuples():
        if row.accuracy_auto > best:
            keep.append(row.Index)
            best = row.accuracy_auto
    return d.loc[keep]


# --------------------------------------------------------------------------- output
def plot_sweep(df: pd.DataFrame, default: tuple[float, float], path: Path):
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    fig, ax = plt.subplots(figsize=(7, 4.6), dpi=150)
    sc = ax.scatter(df.review_share * 100, df.accuracy_auto, c=df.flag_threshold, cmap="viridis",
                    s=38, alpha=0.85, edgecolor="white", linewidth=0.5)
    fr = pareto_frontier(df)
    ax.plot(fr.review_share * 100, fr.accuracy_auto, color="#334155", linewidth=1, label="Pareto frontier")
    cur = df[(df.flag_threshold == default[0]) & (df.review_threshold == default[1])]
    if len(cur):
        ax.scatter(cur.review_share * 100, cur.accuracy_auto, s=160, facecolor="none", edgecolor="#dc2626",
                   linewidth=2, label=f"current ({default[0]:.2f} / {default[1]:.2f})")
    fig.colorbar(sc, ax=ax, label="FLAG_THRESHOLD")
    ax.set_xlabel("Share of items sent to human review (%)")
    ax.set_ylabel("Accuracy on the remaining (auto-decided) items")
    ax.set_title("Review workload vs. accuracy on the rest")
    ax.grid(alpha=0.3)
    ax.legend(loc="best", fontsize=8)
    fig.tight_layout()
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path)
    plt.close(fig)


def _fmt(x, pct=False):
    return "n/a" if x != x else (f"{x:.1%}" if pct else f"{x:.3f}")


def comparison_table(results: dict[str, dict]) -> str:
    lines = ["| Design | Accuracy (auto-decided) | Auto-decided | Human review | Reach transformer | ms/item (Phase 1 + Phase 2) |",
             "|---|---|---|---|---|---|"]
    for name, r in results.items():
        lines.append(f"| {name} | {_fmt(r['accuracy_auto'])} | {r['n_auto']} / {r['n']} | {r['n_review']} | "
                     f"{r['reached_transformer']} ({r['share_reaching']:.0%}) | "
                     f"{r['ms_total']:.1f} ({r['ms_phase1']:.1f} + {r['ms_phase2']:.1f}) |")
    return "\n".join(lines)


def factual_summary(results: dict[str, dict]) -> list[str]:
    """Plain restatements of the numbers. The interpretation is for a human to write."""
    names = list(results)
    a, b, c = (results[n] for n in names)
    return [
        f"- Phase 1 regex gate: {a['reached_transformer'] - b['reached_transformer']} of {a['n']} items "
        f"skip the transformer; accuracy on auto-decided items goes from {_fmt(a['accuracy_auto'])} to "
        f"{_fmt(b['accuracy_auto'])}; time per item {a['ms_total']:.1f} ms to {b['ms_total']:.1f} ms.",
        f"- Adding the semantic gate: {b['reached_transformer'] - c['reached_transformer']} further items skip the "
        f"transformer; accuracy {_fmt(b['accuracy_auto'])} to {_fmt(c['accuracy_auto'])}; "
        f"time per item {b['ms_total']:.1f} ms to {c['ms_total']:.1f} ms.",
        f"- Human-review items: {a['n_review']} (a), {b['n_review']} (b), {c['n_review']} (c).",
    ]


def pivot_table(df: pd.DataFrame, value: str, pct: bool) -> str:
    pv = df.pivot(index="flag_threshold", columns="review_threshold", values=value)
    head = "| FLAG \\ REVIEW | " + " | ".join(f"{c:.1f}" for c in pv.columns) + " |"
    sep = "|---|" + "---|" * len(pv.columns)
    body = [f"| {idx:.1f} | " + " | ".join("" if v != v else _fmt(v, pct) for v in row) + " |"
            for idx, row in pv.iterrows()]
    return "\n".join([head, sep, *body])


def write_report(path: Path, data_desc: str, clf_name: str, results, sweep_df, default, sweep_png: Path):
    cur = sweep_df[(sweep_df.flag_threshold == default[0]) & (sweep_df.review_threshold == default[1])]
    md = [
        "# Ablation of the three-phase design\n",
        f"Test set: {data_desc}. Phase 2 classifier: `{clf_name}`. "
        f"Thresholds for the comparison: FLAG = {default[0]}, REVIEW = {default[1]} (current defaults).\n",
        "Accuracy is measured on auto-decided items only (Flagged: gold label among the flagged categories; "
        "Passed: gold is `safe`). Items sent to human review are counted separately. "
        "Time per item excludes one-off model loading.\n",
        "## Design comparison\n", comparison_table(results), "",
        *factual_summary(results), "",
        "## Threshold sweep (design c)\n",
        f"![Review share vs accuracy]({sweep_png.name})\n",
        "Accuracy on auto-decided items:\n", pivot_table(sweep_df, "accuracy_auto", False), "",
        "Share of items sent to human review:\n", pivot_table(sweep_df, "review_share", True), "",
    ]
    if len(cur):
        r = cur.iloc[0]
        md.append(f"Current setting: {_fmt(r.review_share, True)} to review, "
                  f"{_fmt(r.accuracy_auto)} accuracy on the rest.\n")
    md += ["## Findings\n",
           "_Write 3 to 5 honest sentences here after reading the tables: what each phase bought, what it cost, "
           "and whether any phase did not help. The test set was written by the same team as the lexicon, so "
           "say so if that flatters Phase 1._\n"]
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(md), encoding="utf-8")


def main(classifier=None):
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--data", type=Path, default=PROJECT_ROOT / "data" / "test_set.csv")
    p.add_argument("--out", type=Path, default=PROJECT_ROOT / "reports" / "ablation.md")
    p.add_argument("--flag-threshold", type=float, default=get_settings().flag_threshold)
    p.add_argument("--review-threshold", type=float, default=get_settings().review_threshold)
    args = p.parse_args()

    if classifier is None:
        from auditor.classifier import get_classifier

        classifier = get_classifier()
    df = pd.read_csv(args.data)
    texts, labels = df.text.tolist(), df.label.tolist()
    default = (args.flag_threshold, args.review_threshold)

    results, last = {}, None
    for name, mode in CONFIGS.items():
        res, _, suspicious, doc_scores = run_config(texts, labels, mode, classifier, *default)
        results[name] = res
        last = (suspicious, doc_scores)
        print(f"{name:36s} acc(auto)={_fmt(res['accuracy_auto'])}  review={res['n_review']}  "
              f"to-transformer={res['reached_transformer']}  {res['ms_total']:.1f} ms/item", flush=True)

    sweep_df = sweep(texts, labels, *last)
    sweep_png = args.out.with_name(args.out.stem + "_sweep.png")
    sweep_df.to_csv(args.out.with_name(args.out.stem + "_sweep.csv"), index=False)
    plot_sweep(sweep_df, default, sweep_png)
    write_report(args.out, f"`{args.data.name}` ({len(df)} items)", getattr(classifier, "name", "?"),
                 results, sweep_df, default, sweep_png)
    print(f"\nWrote {args.out}, {sweep_png.name} and the sweep CSV")


if __name__ == "__main__":
    main()
