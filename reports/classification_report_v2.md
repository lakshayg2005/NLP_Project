# Classification report

Test set: `test_set_v2.csv` (245 examples)

| System | Accuracy | Macro-F1 | ms / item (incl. model load) |
|---|---|---|---|
| regex | 0.465 | 0.439 | 0.1 |
| setfit | 0.829 | 0.825 | 21.9 |

## regex

```
                        precision    recall  f1-score   support

     deceptive_urgency      0.903     0.800     0.848        35
unsubstantiated_claims      0.840     0.600     0.700        35
     subscription_trap      0.553     0.743     0.634        35
       confirm_shaming      1.000     0.171     0.293        35
          drip_pricing      1.000     0.114     0.205        35
       bait_and_switch      1.000     0.029     0.056        35
                  safe      0.214     0.800     0.337        35

              accuracy                          0.465       245
             macro avg      0.787     0.465     0.439       245
          weighted avg      0.787     0.465     0.439       245
```

## setfit

```
                        precision    recall  f1-score   support

     deceptive_urgency      0.833     1.000     0.909        35
unsubstantiated_claims      0.919     0.971     0.944        35
     subscription_trap      0.574     1.000     0.729        35
       confirm_shaming      0.944     0.971     0.958        35
          drip_pricing      0.958     0.657     0.780        35
       bait_and_switch      0.923     0.686     0.787        35
                  safe      0.947     0.514     0.667        35

              accuracy                          0.829       245
             macro avg      0.871     0.829     0.825       245
          weighted avg      0.871     0.829     0.825       245
```
