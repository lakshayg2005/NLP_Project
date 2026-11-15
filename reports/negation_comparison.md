# Negation fix: before and after (issue B2)

| System | Test set | N | Accuracy | Macro-F1 |
|---|---|---|---|---|
| regex, negation off (before) | negation_test.csv | 69 | 0.522 | 0.576 |
| regex, negation off (before) | test_set.csv | 70 | 0.829 | 0.840 |
| regex, negation on (after) | negation_test.csv | 69 | 0.971 | 0.905 |
| regex, negation on (after) | test_set.csv | 70 | 0.829 | 0.837 |
| SetFit before (corpus without negation examples) | negation_test.csv | 69 | 0.478 | 0.371 |
| SetFit before (corpus without negation examples) | test_set.csv | 70 | 0.929 | 0.931 |
| SetFit after (corpus with negation examples) | negation_test.csv | 69 | 0.957 | 0.816 |
| SetFit after (corpus with negation examples) | test_set.csv | 70 | 0.914 | 0.915 |

Known failure `Pay once, there are no recurring fees.` (gold: safe):

- regex, negation off (before): `subscription_trap`
- regex, negation on (after): `safe`
- SetFit before (corpus without negation examples): `subscription_trap`
- SetFit after (corpus with negation examples): `safe`

Remaining errors of the negation-aware regex on `negation_test.csv` (2):

- gold `drip_pricing`, predicted `subscription_trap`: You will not know the final price until the last page; fees are added at checkout.
- gold `drip_pricing`, predicted `subscription_trap`: No problem, just pay a mandatory convenience fee at checkout.
