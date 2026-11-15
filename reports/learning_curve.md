# SetFit learning curve

Test set: `test_set.csv` (70 items). Seeds: [0, 1, 2]. Base model: `sentence-transformers/paraphrase-mpnet-base-v2`.

| Examples / class | Runs | Accuracy (mean ± std) | Min – Max | Macro-F1 (mean ± std) |
|---|---|---|---|---|
| 2 | 3 | 0.748 ± 0.073 | 0.686 – 0.829 | 0.748 ± 0.071 |
| 5 | 3 | 0.810 ± 0.030 | 0.786 – 0.843 | 0.812 ± 0.029 |
| 10 | 3 | 0.881 ± 0.008 | 0.871 – 0.886 | 0.880 ± 0.007 |
| 15 | 3 | 0.910 ± 0.036 | 0.871 – 0.943 | 0.909 ± 0.034 |
| 20 | 3 | 0.924 ± 0.016 | 0.914 – 0.943 | 0.925 ± 0.016 |

Reference lines: regex = 0.829
