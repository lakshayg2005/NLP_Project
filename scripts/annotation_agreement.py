"""A4 tooling: build the enlarged test set with two independent annotators and report Cohen's kappa.

Workflow (see docs/annotation_protocol_v2.md for the labelling rules):

    python scripts/annotation_agreement.py check-leakage     # candidates vs. seed_corpus/test_set
    python scripts/annotation_agreement.py make-sheets       # -> data/annotation/annotator_{a,b}.csv
    # ... each annotator fills the `label` column of THEIR sheet, alone ...
    python scripts/annotation_agreement.py kappa             # -> reports/annotation_agreement.md
    #     (also writes data/annotation/disagreements.csv: fill its `final_label` column together)
    python scripts/annotation_agreement.py merge             # -> data/test_set_v2.csv
    python scripts/evaluate.py --data data/test_set_v2.csv --out reports/classification_report_v2.md

The pool in ``data/annotation/candidates_v2.csv`` was drafted without labels shown to annotators.
``data/annotation/drafter_labels.csv`` holds the drafter's intended label for each item. Annotators
must not open it; ``kappa --drafter`` uses it only as a third, non-independent reference.
"""

from __future__ import annotations

import argparse
import random
import re
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from auditor.config import PROJECT_ROOT  # noqa: E402
from auditor.taxonomy import LABEL_KEYS  # noqa: E402

ANN = PROJECT_ROOT / "data" / "annotation"
CANDIDATES = ANN / "candidates_v2.csv"
SHEET_A, SHEET_B = ANN / "annotator_a.csv", ANN / "annotator_b.csv"
DISAGREEMENTS = ANN / "disagreements.csv"
DRAFTER = ANN / "drafter_labels.csv"
OUT_TEST_V2 = PROJECT_ROOT / "data" / "test_set_v2.csv"
REPORT = PROJECT_ROOT / "reports" / "annotation_agreement.md"

MIN_TOTAL, MIN_PER_CLASS = 150, 30


# --------------------------------------------------------------------------- helpers
def _tokens(text: str) -> set[str]:
    return set(re.findall(r"[a-z0-9]+", text.lower()))


def _norm(text: str) -> str:
    return " ".join(re.findall(r"[a-z0-9]+", text.lower()))


def near_duplicates(texts: dict[str, str], reference: list[str], threshold: float = 0.8):
    """Return ``[(id, matched_reference, jaccard)]`` for texts that (nearly) repeat a reference text."""
    ref = [(r, _norm(r), _tokens(r)) for r in reference]
    hits = []
    for tid, text in texts.items():
        n, tok = _norm(text), _tokens(text)
        for raw, rn, rt in ref:
            if n == rn:
                hits.append((tid, raw, 1.0))
                break
            union = tok | rt
            j = len(tok & rt) / len(union) if union else 0.0
            if j >= threshold:
                hits.append((tid, raw, round(j, 3)))
                break
    return hits


def read_labels(path: Path) -> dict[str, str]:
    """Read an annotator sheet. Raises on blank or unknown labels so kappa is never computed on gaps."""
    df = pd.read_csv(path, dtype=str, keep_default_na=False)
    missing = df[df.label.str.strip() == ""].id.tolist()
    if missing:
        raise SystemExit(f"{path.name}: {len(missing)} unlabelled rows, e.g. {missing[:5]}")
    bad = sorted(set(df.label.str.strip()) - set(LABEL_KEYS))
    if bad:
        raise SystemExit(f"{path.name}: unknown labels {bad}. Allowed: {LABEL_KEYS}")
    return dict(zip(df.id, df.label.str.strip()))


def interpret(kappa: float) -> str:
    """Landis & Koch (1977) bands."""
    if kappa != kappa:
        return "undefined"
    if kappa < 0:
        return "poor"
    for upper, name in [(0.20, "slight"), (0.40, "fair"), (0.60, "moderate"), (0.80, "substantial")]:
        if kappa <= upper:
            return name
    return "almost perfect"


def agreement(a: dict[str, str], b: dict[str, str]) -> dict:
    from sklearn.metrics import cohen_kappa_score

    if set(a) != set(b):
        raise SystemExit("Annotator sheets cover different ids; both must label the same items.")
    ids = sorted(a)
    ya, yb = [a[i] for i in ids], [b[i] for i in ids]
    per_class = {}
    for lab in LABEL_KEYS:
        ba, bb = [y == lab for y in ya], [y == lab for y in yb]
        per_class[lab] = float(cohen_kappa_score(ba, bb)) if len(set(ba) | set(bb)) > 1 else float("nan")
    return {
        "n": len(ids),
        "kappa": float(cohen_kappa_score(ya, yb)),
        "raw_agreement": sum(x == y for x, y in zip(ya, yb)) / len(ids),
        "per_class_kappa": per_class,
        "confusion": pd.crosstab(pd.Series(ya, name="annotator A"), pd.Series(yb, name="annotator B"))
                       .reindex(index=LABEL_KEYS, columns=LABEL_KEYS, fill_value=0),
        "disagree_ids": [i for i, x, y in zip(ids, ya, yb) if x != y],
    }


def build_final(cands: pd.DataFrame, a: dict, b: dict, resolved: dict[str, str]) -> pd.DataFrame:
    """Agreed label where A == B, the jointly resolved label otherwise."""
    rows, unresolved = [], []
    for cid, text in zip(cands.id, cands.text):
        if a[cid] == b[cid]:
            rows.append((cid, text, a[cid]))
        elif resolved.get(cid, "").strip() in LABEL_KEYS:
            rows.append((cid, text, resolved[cid].strip()))
        else:
            unresolved.append(cid)
    if unresolved:
        raise SystemExit(f"{len(unresolved)} disagreements still need a valid final_label, e.g. {unresolved[:5]}")
    return pd.DataFrame(rows, columns=["id", "text", "label"])


def validate_final(df: pd.DataFrame, min_total: int = MIN_TOTAL, min_per_class: int = MIN_PER_CLASS) -> list[str]:
    """Return a list of acceptance-criteria problems (empty list = OK)."""
    problems = []
    if len(df) < min_total:
        problems.append(f"only {len(df)} items (need >= {min_total})")
    counts = df.label.value_counts().reindex(LABEL_KEYS, fill_value=0)
    for lab, n in counts.items():
        if n < min_per_class:
            problems.append(f"class {lab} has {n} items (need >= {min_per_class})")
    return problems


# --------------------------------------------------------------------------- commands
def cmd_check_leakage(args):
    cands = pd.read_csv(CANDIDATES)
    ref = []
    for name in ("seed_corpus.csv", "test_set.csv"):
        ref += pd.read_csv(PROJECT_ROOT / "data" / name).text.tolist()
    hits = near_duplicates(dict(zip(cands.id, cands.text)), ref, args.threshold)
    if hits:
        print(f"{len(hits)} candidate(s) (near-)duplicate existing training/test data:")
        for tid, raw, j in hits:
            print(f"  {tid} (jaccard {j}): {raw[:90]}")
        raise SystemExit(1)
    print(f"OK: none of {len(cands)} candidates repeats seed_corpus.csv or test_set.csv (jaccard < {args.threshold}).")


def cmd_make_sheets(args):
    cands = pd.read_csv(CANDIDATES)
    for path, seed in ((SHEET_A, 1), (SHEET_B, 2)):
        if path.exists() and not args.force:
            raise SystemExit(f"{path} exists; refusing to overwrite someone's labels (use --force).")
        order = list(range(len(cands)))
        random.Random(seed).shuffle(order)     # different order per annotator
        sheet = cands.iloc[order].assign(label="")
        sheet.to_csv(path, index=False)
        print(f"wrote {path} ({len(sheet)} rows)")
    print(f"Allowed labels: {', '.join(LABEL_KEYS)}")


def cmd_kappa(args):
    a, b = read_labels(args.a), read_labels(args.b)
    res = agreement(a, b)
    cands = pd.read_csv(CANDIDATES).set_index("id")

    dis = pd.DataFrame({"id": res["disagree_ids"]})
    dis["text"] = dis.id.map(cands.text)
    dis["label_a"], dis["label_b"] = dis.id.map(a), dis.id.map(b)
    dis["final_label"] = ""
    dis.to_csv(DISAGREEMENTS, index=False)

    lines = [
        "# Annotation agreement (test set v2)\n",
        f"- Items labelled independently by both annotators: **{res['n']}**",
        f"- Cohen's kappa (7 classes): **{res['kappa']:.3f}** ({interpret(res['kappa'])}, Landis & Koch)",
        f"- Raw agreement: {res['raw_agreement']:.1%} ({len(res['disagree_ids'])} disagreements, "
        "listed in `data/annotation/disagreements.csv` for joint resolution)\n",
        "## Per-class kappa (one class vs. the rest)\n",
        "| Class | kappa |", "|---|---|",
    ]
    lines += [f"| {k} | {'n/a' if v != v else f'{v:.3f}'} |" for k, v in res["per_class_kappa"].items()]
    lines += ["\n## Confusion matrix (rows: annotator A, columns: annotator B)\n",
              res["confusion"].to_markdown() if _has_tabulate() else "```\n" + res["confusion"].to_string() + "\n```"]

    if args.drafter and args.drafter.exists():
        d = dict(pd.read_csv(args.drafter, dtype=str).set_index("id").label)
        lines += ["\n## Agreement with the drafter's intended label (not independent)\n",
                  "| Annotator | agreement | kappa |", "|---|---|---|"]
        from sklearn.metrics import cohen_kappa_score

        for name, lab in (("A", a), ("B", b)):
            ids = sorted(lab)
            yl, yd = [lab[i] for i in ids], [d[i] for i in ids]
            lines.append(f"| {name} | {sum(x == y for x, y in zip(yl, yd)) / len(ids):.1%} | "
                         f"{cohen_kappa_score(yl, yd):.3f} |")

    REPORT.parent.mkdir(exist_ok=True)
    REPORT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines))
    print(f"\nReport written to {REPORT}\nDisagreements written to {DISAGREEMENTS}")


def _has_tabulate() -> bool:
    try:
        import tabulate  # noqa: F401

        return True
    except ImportError:
        return False


def cmd_merge(args):
    cands = pd.read_csv(CANDIDATES)
    a, b = read_labels(args.a), read_labels(args.b)
    resolved = {}
    if args.resolved.exists():
        r = pd.read_csv(args.resolved, dtype=str, keep_default_na=False)
        resolved = dict(zip(r.id, r.final_label))
    final = build_final(cands, a, b, resolved)

    ref = []
    for name in ("seed_corpus.csv", "test_set.csv"):
        ref += pd.read_csv(PROJECT_ROOT / "data" / name).text.tolist()
    leaks = near_duplicates(dict(zip(final.id, final.text)), ref)
    if leaks and not args.allow_overlap:
        raise SystemExit(f"{len(leaks)} items overlap training/test data (run check-leakage); use --allow-overlap to ignore.")

    print("Class counts:\n" + final.label.value_counts().reindex(LABEL_KEYS, fill_value=0).to_string())
    problems = validate_final(final)
    if problems:
        raise SystemExit("Acceptance criteria not met: " + "; ".join(problems)
                         + ". Draft more candidates for the short class(es) and annotate them.")
    final[["text", "label"]].to_csv(OUT_TEST_V2, index=False)
    print(f"Wrote {OUT_TEST_V2} ({len(final)} items).")


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)

    s = sub.add_parser("check-leakage"); s.add_argument("--threshold", type=float, default=0.8)
    s.set_defaults(fn=cmd_check_leakage)

    s = sub.add_parser("make-sheets"); s.add_argument("--force", action="store_true")
    s.set_defaults(fn=cmd_make_sheets)

    s = sub.add_parser("kappa")
    s.add_argument("--a", type=Path, default=SHEET_A); s.add_argument("--b", type=Path, default=SHEET_B)
    s.add_argument("--drafter", type=Path, default=None, help="optional drafter_labels.csv")
    s.set_defaults(fn=cmd_kappa)

    s = sub.add_parser("merge")
    s.add_argument("--a", type=Path, default=SHEET_A); s.add_argument("--b", type=Path, default=SHEET_B)
    s.add_argument("--resolved", type=Path, default=DISAGREEMENTS)
    s.add_argument("--allow-overlap", action="store_true")
    s.set_defaults(fn=cmd_merge)

    args = p.parse_args()
    args.fn(args)


if __name__ == "__main__":
    main()
