"""Label-based parsing of the ONE-line synthetic format. No model inference."""
from dataclasses import dataclass
from datetime import date
from decimal import Decimal, InvalidOperation
import re

from pydantic import ValidationError

from reconciliation.models import Invoice

LABELS = {
    "invoice_number": "Invoice number", "vendor": "Vendor", "po_number": "PO number",
    "equipment_id": "Equipment ID", "equipment_name": "Equipment name",
    "quantity": "Quantity", "rental_days": "Rental days", "rental_start": "Rental start",
    "rental_end": "Rental end", "rate_basis": "Rate basis", "daily_rate": "Daily rate",
    "stated_line_total": "Line total",
}


@dataclass
class ParsedInvoice:
    invoice: Invoice | None
    raw_fields: dict[str, str | None]
    errors: list[str]


def parse_invoice(text: str) -> ParsedInvoice:
    raw, values, errors = {}, {}, []
    for key, label in LABELS.items():
        matches = re.findall(rf"^\s*{re.escape(label)}\s*:[ \t]*([^\r\n]*)$", text, re.I | re.M)
        raw[key] = matches[0].strip() if len(matches) == 1 else None
        if len(matches) > 1:
            errors.append(f"{key}: multiple occurrences; cannot choose a value.")
        value = raw[key]
        if value is None or not value.strip():
            values[key] = None
            continue
        try:
            if key in {"quantity", "rental_days"}:
                if not re.fullmatch(r"[0-9]+", value):
                    raise ValueError("Expected a positive whole number")
                value = int(value)
            elif key in {"daily_rate", "stated_line_total"}:
                if not re.fullmatch(r"\$?(?:[0-9]+|[0-9]{1,3}(?:,[0-9]{3})+)(?:\.[0-9]{1,2})?", value):
                    raise ValueError("Expected USD amount with at most two decimal places")
                value = Decimal(value.replace("$", "").replace(",", ""))
            elif key in {"rental_start", "rental_end"}:
                if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", value):
                    raise ValueError("Date must use unambiguous YYYY-MM-DD format")
                value = date.fromisoformat(value)
            elif key == "rate_basis":
                value = value.lower()
            values[key] = value
        except (ValueError, InvalidOperation) as exc:
            errors.append(f"{key}: {exc}")
    try:
        invoice = Invoice.model_validate(values)
    except ValidationError as exc:
        errors.extend(f"{'.'.join(map(str, e['loc']))}: {e['msg']}" for e in exc.errors())
        invoice = None
    return ParsedInvoice(invoice, raw, errors)
