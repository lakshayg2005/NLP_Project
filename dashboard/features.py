"""Pure CSV helpers for dashboard bulk import and export."""

import pandas as pd

from auditor.pipeline import FLAGGED


def parse_product_csv(uploaded) -> pd.DataFrame:
    frame = pd.read_csv(uploaded)
    missing = {"title", "seller_id", "text"} - set(frame.columns)
    if missing:
        raise ValueError(f"CSV is missing required columns: {', '.join(sorted(missing))}")
    return frame


def flagged_products_csv(products) -> str:
    rows = [{"product_id": p.product_id, "title": p.title, "seller_id": p.seller_id,
             "status": p.status, "text": p.raw_text,
             "categories": ", ".join(f.violation_category for f in p.flags if not f.resolved)}
            for p in products if p.status == FLAGGED]
    columns = ["product_id", "title", "seller_id", "status", "text", "categories"]
    return pd.DataFrame(rows, columns=columns).to_csv(index=False)
