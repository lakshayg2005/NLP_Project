
import pandas as pd
import pytest

from auditor.config import PROJECT_ROOT
from auditor.heuristics import screen
from auditor.lexicon import regex_hits


@pytest.mark.parametrize(
    "text,category",
    [
        ("Hurry! Only 2 left in stock.", "deceptive_urgency"),
        ("Offer ends in 10 minutes", "deceptive_urgency"),
        ("Clinically proven to melt belly fat", "unsubstantiated_claims"),
        ("100% eco-friendly packaging", "unsubstantiated_claims"),
        (
            "Free trial, then billed monthly until you cancel",
            "subscription_trap",
        ),
        (
            "Price excludes mandatory service fees",
            "subscription_trap",
        ),
        (
            "No thanks, I hate saving money and prefer full price",
            "confirm_shaming",
        ),
        (
            "Mandatory internet handling fee and booking surcharge added at checkout",
            "drip_pricing",
        ),
        (
            "Advertised at 70% off but discount applies only if upgraded to platinum plan",
            "bait_and_switch",
        ),
    ],
)
def test_regex_detects_category(text, category):
    assert category in regex_hits(text)


@pytest.mark.parametrize(
    "text",
    [
        "Pay once, there are no recurring fees.",
        "No subscription is required to purchase this product.",
        "This is a one-time payment with no automatic renewal.",
        "You will not be billed monthly.",
        "There are no hidden charges or recurring costs.",
        "Your purchase does not renew automatically.",
        "No membership fee is required.",
        "This product has no subscription commitment.",
        "Pay the listed price once and own the product.",
        "There are no additional monthly payments.",
        "Cancellation is not required because this is not a subscription.",
        "The displayed price includes all mandatory fees.",
        "No extra service charges will be added at checkout.",
        "This offer has no automatic billing after purchase.",
        "You will only pay once, with no future charges.",
        "There is no free trial that converts into a paid plan.",
        "The price will not increase after your purchase.",
        "No recurring payment details are collected.",
        "This purchase does not require a monthly membership.",
        "There are no renewal fees associated with this order.",
    ],
)
def test_negated_subscription_language_is_not_flagged(text):
    assert "subscription_trap" not in regex_hits(text)


@pytest.mark.parametrize(
    "text",
    [
        "Free trial, then billed monthly until you cancel.",
        "Your membership automatically renews every month.",
        "After the trial period, your card will be charged monthly.",
        "Subscribe today and pay every month until cancellation.",
        "Your plan renews automatically unless you cancel.",
        "Only the first month is free; subsequent months are charged.",
        "A recurring fee will be deducted from your account each month.",
        "Your annual membership will automatically renew next year.",
        "Continue using the service and your monthly subscription will be renewed.",
        "Your card will be charged every month after the introductory offer.",
    ],
)
def test_real_subscription_traps_are_still_detected(text):
    assert "subscription_trap" in regex_hits(text)


def test_safe_sentence_does_not_hide_violation_in_another_sentence():
    text = (
        "Pay once, there are no recurring fees. "
        "Your membership automatically renews every month."
    )

    assert "subscription_trap" in regex_hits(text)


def test_plain_copy_is_clean():
    result = screen(
        "Cotton t-shirt in sizes S to XL.",
        use_semantic=False,
    )

    assert not result.suspicious
    assert result.reason == "clean"


def test_negated_subscription_copy_is_clean():
    result = screen(
        "Pay once, there are no recurring fees.",
        use_semantic=False,
    )

    assert not result.suspicious
    assert result.reason == "clean"


def test_regex_recall_on_seed_violations():
    """Phase 1 must let almost every known violation through to the classifier."""
    df = pd.read_csv(PROJECT_ROOT / "data" / "seed_corpus.csv")
    bad = df[df.label != "safe"]

    caught = sum(
        screen(text, use_semantic=False).suspicious
        for text in bad.text
    )

    assert caught / len(bad) >= 0.9
