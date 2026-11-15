# Span boundaries: before and after re-annotation (issue B4)

* before gold: `span_test_v1.txt`, 30 docs, 27 spans
* after gold, same 30 docs: re-annotated per `docs/annotation_guide.md`, 27 spans
* after gold, full file: 42 docs, 39 spans (adds confirm-shaming, drip pricing, bait and switch)

| Extractor | v1 gold strict F1 | v1 lenient F1 | v2 (same 30 docs) strict F1 | v2 lenient F1 | v2 full strict F1 | v2 full lenient F1 |
|---|---|---|---|---|---|---|
| regex lexicon | 0.088 | 0.883 | 0.088 | 0.883 | 0.072 | 0.777 |
| distilbert | 0.385 | 0.826 | 0.423 | 0.826 | 0.416 | 0.844 |
| distilbert + boundary normaliser | 0.385 | 0.826 | 0.423 | 0.826 | 0.442 | 0.844 |
| roberta | 0.038 | 0.868 | 0.038 | 0.868 | 0.052 | 0.896 |
| roberta + boundary normaliser | 0.453 | 0.868 | 0.491 | 0.868 | 0.545 | 0.896 |
