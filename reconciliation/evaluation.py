"""Field-level measurements against synthetic truth, independent of reconciliation."""
import json
from decimal import Decimal
from pathlib import Path

import pandas as pd

from reconciliation.parser import parse_invoice
from reconciliation.pdf import extract_pdf_text


def evaluate(data_dir: str | Path):
    data_dir = Path(data_dir)
    truth = json.loads((data_dir / "ground_truth.json").read_text())
    rows, documents = [], []
    for filename, expected in truth.items():
        source = extract_pdf_text(data_dir / "invoices" / filename)
        parsed = parse_invoice(source.text)
        actual = parsed.invoice.model_dump(mode="json") if parsed.invoice else {}
        documents.append({"filename": filename, "method": source.method, "text": source.text,
                          "errors": parsed.errors, "warnings": source.warnings})
        for field, target in expected.items():
            found = actual.get(field)
            if field in {"daily_rate", "stated_line_total"} and target is not None and found is not None:
                correct = Decimal(str(found)) == Decimal(str(target))
            else:
                correct = found == target
            # A parser error invalidates the record even if a duplicate field equals truth.
            if any(error.startswith(field + ":") for error in parsed.errors):
                correct = False
            rows.append({"filename": filename, "method": source.method, "field": field,
                         "expected": target, "actual": found, "correct": bool(correct)})
    comparisons = pd.DataFrame(rows)
    summary = comparisons.groupby("method")["correct"].agg(correct="sum", total="count")
    summary["accuracy"] = summary["correct"] / summary["total"]
    return documents, comparisons, summary.reset_index()
