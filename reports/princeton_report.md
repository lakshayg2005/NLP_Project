# Classification report

Test set: Princeton 'Dark Patterns at Scale' dataset (1285 examples)

| System | Accuracy | Macro-F1 | ms / item (incl. model load) |
|---|---|---|---|
| regex | 0.638 | 0.528 | 0.1 |
| setfit | 0.825 | 0.599 | 6.4 |

## regex

```
                   precision    recall  f1-score   support

deceptive_urgency      1.000     0.635     0.777      1229
subscription_trap      0.938     0.652     0.769        46
             safe      0.019     0.900     0.038        10

        micro avg      0.640     0.638     0.639      1285
        macro avg      0.652     0.729     0.528      1285
     weighted avg      0.990     0.638     0.771      1285
```

## setfit

```
                   precision    recall  f1-score   support

deceptive_urgency      0.998     0.823     0.902      1229
subscription_trap      0.702     0.870     0.777        46
             safe      0.063     0.900     0.118        10

        micro avg      0.874     0.825     0.849      1285
        macro avg      0.588     0.864     0.599      1285
     weighted avg      0.980     0.825     0.891      1285
```

## Real-World Failure Analysis (Princeton Dataset)

Below are representative failure cases of the regex baseline on real-world shopping sites, along with root-cause explanations:

### Example 1: Social Proof (Activity Notification)
- **Text:** `Faith in Glendale, United States purchased a Choose Your Flavors 5 Bag Sample Pack (Whole Bean) about 1 hour ago`
- **Gold label:** `deceptive_urgency`
- **Predicted:** `safe`
- **Why it fails:** Phrasing variation: Uses past tense 'purchased a' instead of 'just bought' or 'sold in the last', missing the urgency lexicon's strict keyword patterns.

### Example 2: Social Proof (Activity Notification)
- **Text:** `31 people seeing this product right now`
- **Gold label:** `deceptive_urgency`
- **Predicted:** `safe`
- **Why it fails:** Synonym gap: Uses 'seeing' instead of the expected observation verbs ('looking', 'viewing', 'watching').

### Example 3: Scarcity (High-demand Message)
- **Text:** `An item you ordered is in high demand. No worries, we have reserved your order.`
- **Gold label:** `deceptive_urgency`
- **Predicted:** `safe`
- **Why it fails:** Implicit pressure: Creates artificial urgency ('in high demand', 'reserved your order') without explicit low-stock numbers ('only 2 left').

### Example 4: Sneaking (Hidden Costs)
- **Text:** `Merchandise: $69.99iService Charge: $14.99 Total Before Tax: $84.98 Estimated Tax: $0.00 Order Total: $84.98`
- **Gold label:** `subscription_trap`
- **Predicted:** `safe`
- **Why it fails:** Malformed scraped text: Concatenation without whitespace ('$69.99iService Charge') breaks regex word boundary \b(service|handling) fees?\b.

### Example 5: Obstruction (Hard to Cancel)
- **Text:** `If you wish to cancel your subscription, you can email us at getflat@flattummyco`
- **Gold label:** `subscription_trap`
- **Predicted:** `safe`
- **Why it fails:** Polite customer-service phrasing: Phrased conditionally ('If you wish to cancel') rather than aggressive recurring terms ('until cancelled', 'auto-renews').

## Failure examples: setfit (Princeton)

225 items misclassified; the first 10 are listed. Replace each placeholder with a one-line root-cause explanation before citing these in the README or report.

### setfit failure 1: Social Proof / Activity Notification
- **Text:** `Faith in Glendale, United States purchased a Choose Your Flavors 5 Bag Sample Pack (Whole Bean) about 1 hour ago`
- **Gold label:** `deceptive_urgency`
- **Predicted:** `safe`
- **Why it fails:** Neutral past-tense purchase notice with no hurry, countdown or scarcity wording, so it reads as ordinary text and is predicted `safe`.

### setfit failure 2: Social Proof / Activity Notification
- **Text:** `Sharmeen Atif From Karachi just bought Stylish Metal Glasses Frames For Kids-Assorted-NA7157`
- **Gold label:** `deceptive_urgency`
- **Predicted:** `safe`
- **Why it fails:** Same pattern: a 'just bought' notice with a name and product but no pressure cue.

### setfit failure 3: Social Proof / Activity Notification
- **Text:** `Keith in Champaign, Illinois bought Mini USB Audio Cassette to MP3 Converterabout 56 minutes ago`
- **Gold label:** `deceptive_urgency`
- **Predicted:** `bait_and_switch`
- **Why it fails:** Same notice type, and the scraped text runs words together ('Converterabout'). No urgency cue is present; why it chose `bait_and_switch` was not investigated.

### setfit failure 4: Social Proof / Activity Notification
- **Text:** `Jamie from Eloy United States purchased a CBD Oil Vape Additives 4 Pack About 7 hours ago`
- **Gold label:** `deceptive_urgency`
- **Predicted:** `safe`
- **Why it fails:** Purchase notice with a time stamp ('7 hours ago') but no pressure wording.

### setfit failure 5: Social Proof / Activity Notification
- **Text:** `Crystal Li in Flushing, United States purchased a`
- **Gold label:** `deceptive_urgency`
- **Predicted:** `safe`
- **Why it fails:** Scraped text is cut off after 'purchased a', so there is no product or cue left to classify.

### setfit failure 6: Social Proof / Activity Notification
- **Text:** `Ken in Oakland, United States purchased a Dreamville Hoodie a month ago`
- **Gold label:** `deceptive_urgency`
- **Predicted:** `safe`
- **Why it fails:** An old time stamp ('a month ago') is the opposite of an urgency signal, and there is no pressure wording.

### setfit failure 7: Social Proof / Activity Notification
- **Text:** `Someone from Menlo Park, California just purchased Electric Skateboard Motor 6374 190KV.`
- **Gold label:** `deceptive_urgency`
- **Predicted:** `safe`
- **Why it fails:** 'Someone ... just purchased' notice with no pressure wording.

### setfit failure 8: Social Proof / Activity Notification
- **Text:** `Mitchell H. Purchased a Dimplex IgniteXL 100" Linear Built in Electric Fireplace`
- **Gold label:** `deceptive_urgency`
- **Predicted:** `safe`
- **Why it fails:** Only a name and a product ('Purchased a ...') with no timing or pressure wording.

### setfit failure 9: Social Proof / Activity Notification
- **Text:** `Favored By: 400 people!`
- **Gold label:** `deceptive_urgency`
- **Predicted:** `unsubstantiated_claims`
- **Why it fails:** A popularity count ('400 people'), not an urgency cue; the nearest class in our taxonomy was `unsubstantiated_claims`.

### setfit failure 10: Social Proof / Activity Notification
- **Text:** `Annie in Cheras, Malaysia just bought: An Abundance of Flowers - Van-Go Paint-By-Number Kit`
- **Gold label:** `deceptive_urgency`
- **Predicted:** `safe`
- **Why it fails:** 'just bought' notice from a foreign location with only a product name and no pressure cue.

## Note on the Princeton label mapping

All 10 listed failures are Princeton "Social Proof / Activity Notification" items, which the loader maps to
`deceptive_urgency`. Our 7-class taxonomy has no social-proof class, so this mapping is a judgment call.
Across the full set (1,275 mapped violations), SetFit was correct on 54.9% of 284 Activity Notifications that
Princeton did not mark as verified deceptive and 72.4% of 29 that it did. Misses on the verified ones suggest a
real gap and not only a labelling mismatch. Low-stock messages (631 items) were classified correctly 96% or more
of the time. These are per-type accuracies from one training run.
