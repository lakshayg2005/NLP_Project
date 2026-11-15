# E-Commerce Compliance and Dark Pattern Auditor

## Abstract

This project audits marketplace product descriptions for copy associated with deceptive
urgency, unsubstantiated claims, subscription traps, and three CCPA patterns: confirm-shaming,
drip pricing, and bait and switch. It combines a heuristic screen, a risk classifier, and a
span extractor, then stores results for review in a dashboard. The available held-out results
show 0.871 accuracy and 0.868 macro-F1 for the seven-class SetFit experiment. Those results
come from a small, hand-written test set and should be treated as preliminary.

## Introduction and motivation

Product descriptions can contain pressure tactics, unsupported claims, and price or renewal
terms that are difficult to notice. The repository frames the task around consumer-protection
guidance including the FTC and India's CCPA 2023 taxonomy. The system is a copy-screening aid;
it does not determine legal compliance.

## Related work

The project's real-world evaluation uses the Princeton *Dark Patterns at Scale* corpus
(Mathur et al., 2019). Its source and label mapping are documented in
[`label_mapping.md`](label_mapping.md). The implementation compares regular-expression rules,
zero-shot NLI, and a SetFit classifier, with a token classifier for highlighting spans.

## Method

1. **Heuristic screen:** regex patterns and sentence-embedding similarity identify copy that
   can pass directly or needs further review.
2. **Risk classification:** SetFit or zero-shot NLI scores sentences against seven labels.
   High scores are flagged; uncertain cases enter the human review queue.
3. **Span extraction:** a token classifier identifies text offsets for dashboard highlighting.
   Regex spans are used when no trained extractor is present.

The FastAPI service stores products, findings, and reviewer feedback in PostgreSQL or SQLite.
The Streamlit dashboard presents aggregate counts, flagged items, review tasks, bulk CSV
handling, seller history, and an unsaved live audit page.

## Experiments and results

| Experiment | Result | Evidence |
|---|---|---|
| Four-class held-out classification | SetFit accuracy 0.950; macro-F1 0.950 on 40 examples | [`README.md`](../README.md), [`classification_report.md`](../reports/classification_report.md) |
| Seven-class CCPA extension | SetFit accuracy 0.871; macro-F1 0.868 on 70 examples | [`classification_report.md`](../reports/classification_report.md) |
| Princeton real-world regex baseline | Accuracy 0.636; urgency F1 0.777; subscription F1 0.779 on 1,275 texts | [`princeton_report.md`](../reports/princeton_report.md) |
| Span extraction | DistilBERT strict F1 0.414; overlap F1 0.915 on 30 documents | [`span_extractor_report.txt`](../reports/span_extractor_report.txt) |

The Princeton report provides individual failure examples. The current repository does not
contain results for the learning-curve and three-phase ablation experiments, so this report
does not claim results for them.

## Error analysis

The real-world report describes missed open-ended phrasing and implicit scarcity as recurring
regex failures. The span report and README distinguish exact-boundary errors from overlapping
matches. The README also records a negation false positive: “Pay once, there are no recurring
fees” can be classified as a subscription trap. These examples show why the reviewer queue and
feedback path are part of the product design.

## Limitations

- Test sets are small and partly authored alongside the taxonomy and lexicon.
- The Princeton table evaluates a regex baseline; it does not establish transformer
  performance on that corpus.
- Several reported scores come from different test-set sizes and are not directly comparable.
- CCPA labels are a text-detection taxonomy, not a legal determination.
- Training, ablation, learning-curve, and multilingual results are not all present in the
  checked-in reports.
- Model predictions depend on trained artifacts; the repository keeps those large files out
  of Git.

## Conclusion

The repository demonstrates an end-to-end review workflow and preliminary results across
synthetic and real-world text. The seven-class score is promising but not enough to establish
reliable marketplace performance. Larger independently annotated data and the missing
ablation and learning-curve results are needed before making stronger claims.

## Contributions

Contributor names and task ownership were not supplied in the repository. Complete this table
with the project team before publication; do not infer attribution from commit authorship.

| Contributor | Workstream / contribution |
|---|---|
| To be completed by project team | Data and evaluation |
| To be completed by project team | Taxonomy and models |
| To be completed by project team | Engineering and delivery |

## Sources

- Mathur et al. (2019), *Dark Patterns at Scale*: <https://github.com/aruneshmathur/dark-patterns-at-scale>
- Result details: [`reports/`](../reports/)
