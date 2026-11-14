# Span annotation guide

Phase 3 learns to highlight the exact manipulative phrase. The earlier benchmark scored
**0.41 strict F1 against 0.92 lenient F1**: the model found the right phrase but the edges
disagreed with the gold (for example the prediction `timer says 4 minutes left` against the
gold `the timer says 4 minutes left`). The cause was inconsistent edge conventions across the
seed data, the templates and the test set, not the model. These rules remove the ambiguity.
`scripts/lint_annotations.py` enforces them.

## Markup

`[[TAG|phrase]]` marks a phrase. Tags: `URGENCY`, `CLAIM`, `PRICING`, `SHAMING`, `DRIP`, `BAIT`.

## Rules

1. **No edge punctuation or whitespace.** Sentence punctuation (`. , ; : ! ?`, dashes) stays
   outside the span: `[[URGENCY|Last chance]]!`.
2. **No leading article, demonstrative or possessive.** Start at the first word that carries
   the manipulation. Words excluded: *the, a, an, this, that, these, those, our, your, my, their, its*.
   - `the [[URGENCY|timer says 4 minutes left]]`
   - `Your [[URGENCY|cart is reserved for 5 minutes only]]`
3. **No leading or trailing connective** (*and, or, but, so, then*):
   `then [[PRICING|automatically renews at full price]]`.
4. **Include the numbers and units that complete the statement**: `4 minutes left`,
   `$39 is charged each month`, `10 minutes`. The trailing number is part of the span.
5. **Cover the whole manipulative statement, nothing more.** If the offending clause has a
   subject, verb and object, include all three (`booking fee and a platform fee are added on the final payment page`).
   Do not extend the span over neutral sentences next to it, or over imperatives such as
   "buy now" unless they are the manipulation (`Act now` is urgency; `buy now` after an urgency span is not).
6. **Lists inside one clause are one span.** `balances hormones and prevents illness` is one
   CLAIM; the "and" is inside, not at an edge. Two separate clauses are two spans.
7. **One sentence per span.** A span does not cross `. ! ?`. The exception is a confirm-shaming
   opt-out label, which is one unit of button text: `[[SHAMING|No thanks! I don't like deals, I prefer to stay poor]]`.
8. **No overlap between spans.** If two categories fit one phrase, use the category the
   sentence is mainly about.
9. **Safe copy has no span**, even when it reuses risky words ("no hidden fees", "does not
   auto-renew", "not clinically tested"). See `data/negation_test.csv`.

## Decisions that came up in review

| Question | Decision |
|---|---|
| Leading "the" (`the timer runs out`)? | Excluded (rule 2). The old test set included it; the templates mostly did not. |
| Trailing number (`only 5 left`, `4 minutes left`)? | Included (rule 4). |
| Leading "Your" (`Your card will be charged...`)? | Excluded (rule 2). |
| "then ..." after a price? | `then` is outside (rule 3). |
| Trailing "." or "!"? | Outside (rule 1). |
| Quantity words (`only a handful remain`)? | Included, they are the claim. |

## Applying and checking

```bash
python scripts/lint_annotations.py          # list violations (exit code 1 if any)
python scripts/lint_annotations.py --fix    # move offending edge words outside the span
```

`data/span_test_v1.txt` keeps the original test annotation so that
`python scripts/span_boundary_report.py` can report the effect of the re-annotation.

At inference the same rules are applied to the model's output by
`auditor.extractor.normalize_boundaries`, so a model that still predicts a leading "the"
does not lose strict F1 for it.
