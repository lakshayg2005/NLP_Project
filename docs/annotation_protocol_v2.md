# Annotation protocol: test set v2 (issue A4)

Goal: two people label the same 245 product texts independently, we report Cohen's kappa, resolve the
disagreements together, and publish the result as `data/test_set_v2.csv` (target: at least 150 items and
30+ per class; the pool has 35 per intended class so resolution cannot push a class under 30).

## Rules for annotators

1. **Work alone.** Do not discuss items, and do not open `data/annotation/drafter_labels.csv`.
2. Generate your sheet with `python scripts/annotation_agreement.py make-sheets`. Annotator A edits
   `annotator_a.csv`, annotator B edits `annotator_b.csv`. Fill only the `label` column.
3. Judge **the text alone**. You cannot verify whether a deadline or a health claim is true, so label
   what the wording does, not what you suspect about the seller.
4. Use exactly one of these labels:

| Label | Use it when the text... |
|---|---|
| `deceptive_urgency` | pushes the buyer to act now with a countdown, "only N left", "X people are viewing this", or a deadline phrased as pressure |
| `unsubstantiated_claims` | makes a medical, health or environmental claim that is absolute, miraculous, unsourced or unverifiable |
| `subscription_trap` | hides or plays down a recurring charge, auto-renewal, trial-to-paid conversion, or makes cancelling hard |
| `confirm_shaming` | words the decline/opt-out option so that it shames or guilts the reader |
| `drip_pricing` | advertises a low price while mandatory fees or charges only appear later (checkout, arrival, final step) |
| `bait_and_switch` | advertises an offer that is unavailable, restricted, differently specified, or replaced at purchase time |
| `safe` | is honest, factual copy; fees, renewals and deadlines are stated plainly, or nothing manipulative is present |

## Tie-break rules (agree on these before you start)

- **Several violation types in one text:** pick the type of the **first** manipulative cue in the text.
- **Recurring fee vs. extra fee:** a charge that repeats over time is `subscription_trap`; a one-off
  mandatory fee revealed late is `drip_pricing`. If the late fee is attached to an offer that changes
  at purchase (a different price or product), prefer `bait_and_switch`.
- **Transparent fees and dates are safe:** "Shipping $4.99, shown in your cart before you pay" or
  "Sale runs 1 to 7 December" contains no pressure and no concealment.
- **Negated or reassuring wording is safe:** "No subscription, no recurring charges" is not a
  subscription trap. Read the sentence, do not match keywords.
- **Substantiated claims:** a claim that points to a checkable source ("full study at the link below")
  is `safe`; a bare "clinically proven" is `unsubstantiated_claims`.
- A neutral decline button ("No thanks, maybe later") is `safe`.
- If you are really unsure, still pick your best label. Do not leave rows blank (the tool refuses blanks).

## After labelling

```bash
python scripts/annotation_agreement.py kappa --drafter data/annotation/drafter_labels.csv
```

This writes `reports/annotation_agreement.md` (kappa overall and per class, confusion matrix) and
`data/annotation/disagreements.csv`. Resolve each disagreement **together**, writing the agreed label into
its `final_label` column, then:

```bash
python scripts/annotation_agreement.py merge
python scripts/evaluate.py --data data/test_set_v2.csv --out reports/classification_report_v2.md
```

`merge` refuses to run if any disagreement is unresolved, if an item repeats training or old test data, or
if the 150-item / 30-per-class bar is not met.

Report kappa **before** resolution. It measures how well-defined the task is; the resolved labels are
only the answer key.

## Notes on the candidate pool

- 245 texts, 35 per intended class, shuffled. About 3% are multi-violation items (flagged in
  `drafter_labels.csv`); there are also tricky `safe` items (transparent fees, negated wording, a
  stock count stated factually) and near-boundary cases such as drip pricing vs. bait and switch.
- The pool was drafted by one person, so it shares that person's phrasing habits. Treat accuracy on it
  as another controlled benchmark, not as real-world performance (see the Princeton evaluation for that).
- No item repeats `seed_corpus.csv` or `test_set.csv` (checked by `check-leakage` and a unit test).
