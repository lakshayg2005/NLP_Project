"""Smoke-test every dashboard page with Streamlit's headless AppTest runner."""

import pytest
from streamlit.testing.v1 import AppTest

from auditor.config import PROJECT_ROOT

APP = str(PROJECT_ROOT / "dashboard" / "app.py")
PAGES = ["Overview", "Flagged products", "Human review queue", "Bulk CSV", "Seller history"]


@pytest.fixture
def seeded(stub_models, engine, monkeypatch):
    from auditor import db
    from auditor.pipeline import audit

    monkeypatch.setattr(db, "get_engine", lambda url=None: engine)
    texts = {
        "flagged": "Hurry, only 2 left in stock - offer ends tonight!",
        "review": "Our tea is natural.",
        "safe": "Blue cotton socks.",
    }
    with db.session_scope(engine) as s:
        for title, text in texts.items():
            db.apply_audit(s, db.create_product(s, title, "S1", text), audit(text))


@pytest.mark.parametrize("page", PAGES)
def test_page_renders(seeded, page):
    at = AppTest.from_file(APP, default_timeout=60).run()
    at.sidebar.radio[0].set_value(page).run()
    assert not at.exception, at.exception


def test_review_submission_updates_status(seeded, engine):
    from auditor import db

    at = AppTest.from_file(APP, default_timeout=60).run()
    at.sidebar.radio[0].set_value("Human review queue").run()
    at.button(key=next(b.key for b in at.button if b.key and b.key.startswith("sub-"))).click().run()
    assert not at.exception
    with db.session_scope(engine) as s:
        assert s.query(db.HumanFeedback).count() == 1


def test_bulk_csv_controls_render(seeded):
    at = AppTest.from_file(APP, default_timeout=60).run()
    at.sidebar.radio[0].set_value("Bulk CSV").run()
    assert not at.exception, at.exception
    assert at.file_uploader


def test_seller_history_renders_events(seeded):
    at = AppTest.from_file(APP, default_timeout=60).run()
    at.sidebar.radio[0].set_value("Seller history").run()
    assert not at.exception, at.exception
    assert any(select.label == "Seller" for select in at.selectbox)


def test_product_csv_parser_requires_columns():
    from io import StringIO

    from dashboard.features import parse_product_csv

    frame = parse_product_csv(StringIO("title,seller_id,text\nBottle,S1,Only 2 left"))
    assert frame.iloc[0].to_dict() == {"title": "Bottle", "seller_id": "S1", "text": "Only 2 left"}
    with pytest.raises(ValueError, match="seller_id"):
        parse_product_csv(StringIO("title,text\nBottle,Only 2 left"))


def test_flagged_csv_contains_only_open_flags(seeded, engine):
    import csv
    from io import StringIO

    from auditor import db
    from dashboard.features import flagged_products_csv

    with db.session_scope(engine) as s:
        products = list(s.query(db.AuditedProduct).all())
        content = flagged_products_csv(products)
    rows = list(csv.DictReader(StringIO(content)))
    assert rows
    assert all(row["status"] == "Flagged" for row in rows)
    assert all(row["categories"] for row in rows)
