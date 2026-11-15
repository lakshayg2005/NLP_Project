# English-only vs multilingual model (issue B3)

| System | Test set | N | Accuracy | Macro-F1 | ms / item |
|---|---|---|---|---|---|
| regex lexicon (reference) | English (test_set.csv) | 70 | 0.829 | 0.837 | 0.2 |
| regex lexicon (reference) | Hinglish (hinglish_test.csv) | 42 | 0.310 | 0.299 | 0.1 |
| SetFit: english | English (test_set.csv) | 70 | 0.914 | 0.915 | 89.4 |
| SetFit: english | Hinglish (hinglish_test.csv) | 42 | 0.405 | 0.395 | 17.7 |
| SetFit: multilingual | English (test_set.csv) | 70 | 0.914 | 0.914 | 29.5 |
| SetFit: multilingual | Hinglish (hinglish_test.csv) | 42 | 0.476 | 0.520 | 28.0 |
| SetFit: english+hinglish | English (test_set.csv) | 70 | 0.929 | 0.929 | 15.2 |
| SetFit: english+hinglish | Hinglish (hinglish_test.csv) | 42 | 0.952 | 0.952 | 16.6 |
| SetFit: multilingual+hinglish | English (test_set.csv) | 70 | 0.929 | 0.928 | 20.4 |
| SetFit: multilingual+hinglish | Hinglish (hinglish_test.csv) | 42 | 0.976 | 0.976 | 27.8 |

## Recommendation (baseline = `SetFit: english`)

- `SetFit: multilingual`: Hinglish +0.071, English -0.000 -> meets the rule (Hinglish gain >= 0.05, English drop <= 0.03)
- `SetFit: english+hinglish`: Hinglish +0.548, English +0.014 -> meets the rule (Hinglish gain >= 0.05, English drop <= 0.03)
- `SetFit: multilingual+hinglish`: Hinglish +0.571, English +0.014 -> meets the rule (Hinglish gain >= 0.05, English drop <= 0.03)

**Ship `SetFit: multilingual+hinglish`.** Speed matters too: the multilingual mpnet model is larger than the English one, so check the ms / item column before deciding.

Note: Phase 1's embedding filter (`all-MiniLM-L6-v2`) is English-only. For Hinglish traffic set `EMBEDDING_MODEL=sentence-transformers/paraphrase-multilingual-mpnet-base-v2` or rely on the regex branch.
