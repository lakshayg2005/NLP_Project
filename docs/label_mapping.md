# Princeton "Dark Patterns at Scale" Label Mapping

This document details the mapping between the dark-pattern taxonomy from **Mathur et al. (2019)** (*"Dark Patterns at Scale: Findings from a Crawl of 11K Shopping Websites"*, Princeton University) and our compliance auditor risk categories.

---

## 1. Taxonomies Overview

### Auditor Target Categories (6 violations + safe)
| Category Key | Category Name | Scope & NLI Hypothesis |
|---|---|---|
| `deceptive_urgency` | Deceptive Urgency (Fake Countdown Timers) | Pressures the buyer with fake scarcity, countdown timers, artificial deadlines, or social proof viewing/buying counts. |
| `subscription_trap` | Hidden Subscription Traps or Obfuscated Pricing | Hides recurring billing, automatic renewal, hidden fees, forced add-on items, or obstruction during cancellation. |
| `unsubstantiated_claims` | Unsubstantiated Health or Environmental Claims | Makes unverified medical, health, wellness, or greenwashing environmental claims. |
| `confirm_shaming` | Confirm-shaming (Guilt-inducing Opt-outs) | Uses guilt, shame or emotional manipulation to discourage opting out (CCPA 2023, added in B1). |
| `drip_pricing` | Drip Pricing (Hidden Incremental Charges) | Conceals mandatory fees, surcharges or taxes that are revealed step by step at checkout (CCPA 2023, added in B1). |
| `bait_and_switch` | Bait and Switch (Misleading Offer or Terms) | Advertises an attractive offer that is unavailable, restricted or replaced with higher charges (CCPA 2023, added in B1). |
| `safe` | Safe E-Commerce Copy | Honest, factual product and checkout copy. |

The Princeton evaluation (issue A1) keeps the original four targets (`deceptive_urgency`,
`subscription_trap`, `unsubstantiated_claims`, `safe`) in `scripts/load_princeton.py`, so those
numbers stay comparable with the first run. The three CCPA categories are the intended targets
for the Misdirection and Sneaking types listed below.

### Princeton Dataset Categories (7 Classes, 15 Types)
Mathur et al. collected 1,818 dark-pattern instances (1,512 with textual strings) across ~11,000 e-commerce websites.

---

## 2. Category & Type Mapping Table

| Princeton Category | Princeton Pattern Type | Auditor Category (`label`) | Justification & Rationale |
|---|---|---|---|
| **Urgency** | `Countdown Timer` | `deceptive_urgency` | Artificial time limit imposing psychological purchase pressure. |
| **Urgency** | `Limited-time Message` | `deceptive_urgency` | "Offer ends in 10 mins", "Deal closes tonight" triggers urgency rules. |
| **Scarcity** | `Low-stock Message` | `deceptive_urgency` | "Only 2 left in stock", "Almost sold out" creates fake purchase urgency via scarcity. |
| **Scarcity** | `High-demand Message` | `deceptive_urgency` | "Selling fast!", "In high demand" pressures immediate checkout. |
| **Social Proof** | `Activity Notification` | `deceptive_urgency` | Peer activity feeds ("31 people looking right now", "Keith in Illinois just bought...") induce FOMO and accelerate decisions. Matches our `\b\d+\s+people\s+are\s+viewing\b` and `\bjust bought\b` patterns. |
| **Social Proof** | `Testimonials of Uncertain Origin` | `deceptive_urgency` | Social proof used to bypass buyer hesitation. |
| **Obstruction** | `Hard to Cancel` | `subscription_trap` | Burdensome cancellation loops ("cancel by calling a number", "email support to cancel Smartship") intended to lock consumers in subscriptions. |
| **Sneaking** | `Hidden Subscription` | `subscription_trap` | VIP trial memberships automatically enrolled at checkout, converting to recurring monthly bills. |
| **Sneaking** | `Hidden Costs` | `subscription_trap` (loader default); `drip_pricing` in the CCPA taxonomy | Mandatory service charges, handling fees, or resort fees revealed only at final checkout step. |
| **Sneaking** | `Sneak into Basket` | `subscription_trap` | Pre-checked optional products, shipping protection, or donations slipped into the cart. |
| **Forced Action** | `Forced Enrollment` | `subscription_trap` | Requiring subscription enrollment or agreement to continuous care terms to access purchase. |
| **Misdirection** | `Confirmshaming` | `confirm_shaming` (CCPA taxonomy, B1); not mapped by the Princeton loader's default 4-target mode | Emotionally manipulative opt-out buttons ("No thanks, I hate saving money"). |
| **Misdirection** | `Pressured Selling` | *Unmapped / Ambiguous* | Upsell/cross-sell suggestions ("Why not add fabric warranty?"). Many lack explicit urgency/pricing manipulation. |
| **Misdirection** | `Trick Questions` | *Unmapped* (CCPA `trick_wording` is not one of the implemented categories) | Confusing double-negatives in opt-in checkboxes. |
| **Misdirection** | `Visual Interference` | *Unmapped in 4-class baseline* | De-emphasized or hidden opt-out text; requires DOM/CSS analysis rather than text classification alone. |

---

## 3. Dataset Characteristics & Considerations

1. **Absence of Negative (Safe) Samples**: The Princeton crawl exclusively collected dark patterns discovered by heuristics or manual validation. For end-to-end evaluation with specificity metrics, negative control samples from benign product copy (`data/test_set.csv` safe class) are optionally integrated via `scripts/load_princeton.py --include-safe-controls`.
2. **Missing Strings**: 306 entries in the Princeton dataset lack `Pattern String` (e.g., pure CSS timers, graphic badges). `scripts/load_princeton.py` drops these null records, yielding 1,512 usable text strings (1,275 directly mapped to `deceptive_urgency` and `subscription_trap`).
3. **Misdirection Gap**: In the baseline 4-class model, `Misdirection` patterns fail to trigger urgency or pricing rules, predictably being classified as `safe`. Rather than distorting the baseline with an artificial mapping, this gap is documented as empirical justification for extending our taxonomy with India's CCPA guidelines (Issue B1: `confirm_shaming`, `drip_pricing`, `bait_and_switch`).

