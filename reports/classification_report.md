# Classification report

Test set: `test_set.csv` (70 examples)

| System | Accuracy | Macro-F1 | ms / item (incl. model load) |
|---|---|---|---|
| regex | 0.829 | 0.837 | 0.2 |
| zero_shot | 0.514 | 0.449 | 13853.5 |
| setfit | 0.914 | 0.915 | 25.8 |

## regex

```
                        precision    recall  f1-score   support

     deceptive_urgency      1.000     1.000     1.000        10
unsubstantiated_claims      1.000     0.900     0.947        10
     subscription_trap      0.727     0.800     0.762        10
       confirm_shaming      1.000     0.800     0.889        10
          drip_pricing      1.000     0.600     0.750        10
       bait_and_switch      1.000     0.700     0.824        10
                  safe      0.526     1.000     0.690        10

              accuracy                          0.829        70
             macro avg      0.893     0.829     0.837        70
          weighted avg      0.893     0.829     0.837        70
```

## zero_shot

```
                        precision    recall  f1-score   support

     deceptive_urgency      1.000     0.700     0.824        10
unsubstantiated_claims      0.125     0.100     0.111        10
     subscription_trap      0.500     0.700     0.583        10
       confirm_shaming      0.000     0.000     0.000        10
          drip_pricing      0.500     0.200     0.286        10
       bait_and_switch      0.562     0.900     0.692        10
                  safe      0.476     1.000     0.645        10

              accuracy                          0.514        70
             macro avg      0.452     0.514     0.449        70
          weighted avg      0.452     0.514     0.449        70
```

## setfit

```
                        precision    recall  f1-score   support

     deceptive_urgency      1.000     1.000     1.000        10
unsubstantiated_claims      1.000     0.900     0.947        10
     subscription_trap      0.800     0.800     0.800        10
       confirm_shaming      1.000     1.000     1.000        10
          drip_pricing      0.818     0.900     0.857        10
       bait_and_switch      1.000     0.800     0.889        10
                  safe      0.833     1.000     0.909        10

              accuracy                          0.914        70
             macro avg      0.922     0.914     0.915        70
          weighted avg      0.922     0.914     0.915        70
```

## Full tiered pipeline

| Metric | Value |
|---|---|
| auto-decided | 69 |
| sent to human review | 1 |
| accuracy on auto-decided | 0.928 |
| passed at phase 1 (no transformer cost) | 8 |

## Phase 3 span extraction

Test set: `span_test.txt` (42 documents, 39 gold spans)

### regex (strict)

```
type       precision    recall        f1  support
micro          0.068     0.077     0.072       39
BAIT           0.000     0.000     0.000        4
CLAIM          0.000     0.000     0.000        9
DRIP           0.000     0.000     0.000        4
PRICING        0.000     0.000     0.000        9
SHAMING        0.000     0.000     0.000        4
URGENCY        0.300     0.333     0.316        9
```

### regex (lenient)

```
type       precision    recall        f1  support
micro          0.886     0.692     0.777       39
BAIT           0.000     0.000     0.000        4
CLAIM          1.000     0.889     0.941        9
DRIP           0.400     0.500     0.444        4
PRICING        1.000     0.889     0.941        9
SHAMING        1.000     0.250     0.400        4
URGENCY        0.800     0.889     0.842        9
```
