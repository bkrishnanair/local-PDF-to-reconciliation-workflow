"""Deterministic vendor-cost rules, independent of PDF processing and the UI."""
from decimal import Decimal
from pathlib import Path

import pandas as pd

from reconciliation.models import Invoice, Outcome, PurchaseOrder, ReconciliationResult, Thresholds


def load_purchase_orders(path: str | Path) -> list[PurchaseOrder]:
    frame = pd.read_csv(path, dtype=str, keep_default_na=False)
    records = frame.to_dict(orient="records")
    for row in records:
        for field in ("quantity", "rental_days"):
            row[field] = int(row[field])
    return [PurchaseOrder.model_validate(row) for row in records]


def within_tolerance(difference: Decimal, baseline: Decimal, thresholds: Thresholds) -> bool:
    """BOTH limits must pass. A zero baseline allows only an exact match."""
    if baseline == 0:
        return difference == 0
    return (abs(difference) <= thresholds.absolute
            and abs(difference) * 100 <= abs(baseline) * thresholds.percent)


def reconcile(invoice: Invoice, orders: list[PurchaseOrder], thresholds: Thresholds | None = None) -> ReconciliationResult:
    thresholds = thresholds or Thresholds()
    # Stated total is optional; every other field is required for this format.
    missing = [name for name in Invoice.model_fields if name != "stated_line_total" and getattr(invoice, name) is None]
    if missing:
        return ReconciliationResult(outcome=Outcome.MISSING_INFORMATION, reasons=["Missing required fields: " + ", ".join(missing)])
    candidates = [po for po in orders if po.po_number == invoice.po_number]
    if not candidates:
        return ReconciliationResult(outcome=Outcome.UNMATCHED_PO, reasons=[f"No approved PO found for {invoice.po_number}."])
    equipment = [po for po in candidates if po.equipment_id == invoice.equipment_id]
    if not equipment:
        return ReconciliationResult(outcome=Outcome.HOLD_FOR_REVIEW,
                                    reasons=["Equipment ID does not match any line on the PO; no line selected."])
    if len(equipment) > 1:
        equipment = [po for po in equipment if po.rental_start == invoice.rental_start and po.rental_end == invoice.rental_end]
    if len(equipment) != 1:
        return ReconciliationResult(outcome=Outcome.HOLD_FOR_REVIEW, reasons=["PO line match is ambiguous; cannot select a unique equipment/date line."])
    po = equipment[0]
    structural = []
    for field in ("vendor", "equipment_name", "quantity", "rental_days", "rental_start", "rental_end", "rate_basis"):
        actual, approved = getattr(invoice, field), getattr(po, field)
        if isinstance(actual, str):
            actual, approved = actual.casefold(), approved.casefold()
        if actual != approved:
            structural.append(f"{field}: invoice {getattr(invoice, field)} differs from PO {getattr(po, field)}.")
    if invoice.rate_basis != "daily" or po.rate_basis != "daily":
        structural.append("Only daily rates are supported; no daily calculation performed for another rate basis.")
        return ReconciliationResult(outcome=Outcome.HOLD_FOR_REVIEW, reasons=structural, purchase_order=po)
    if invoice.rental_end < invoice.rental_start or (invoice.rental_end - invoice.rental_start).days + 1 != invoice.rental_days:
        structural.append("Rental dates are reversed or inconsistent with inclusive rental days.")
    if po.rental_end < po.rental_start or (po.rental_end - po.rental_start).days + 1 != po.rental_days:
        structural.append("Approved PO dates are inconsistent with inclusive rental days.")
    # Use invoice quantity/days as requested; structural differences still force a hold.
    expected = po.approved_daily_rate * invoice.quantity * invoice.rental_days
    invoiced = invoice.daily_rate * invoice.quantity * invoice.rental_days
    difference = invoiced - expected
    stated_delta = None if invoice.stated_line_total is None else invoice.stated_line_total - invoiced
    variances = [("Calculated vendor-cost variance", difference, expected)]
    if stated_delta is not None:
        variances.extend([("Stated total versus calculated invoice amount", stated_delta, invoiced),
                          ("Stated total versus expected vendor cost", invoice.stated_line_total - expected, expected)])
    monetary = [f"{label}: USD {delta:+.2f}." for label, delta, _ in variances if delta != 0]
    hold = structural or any(not within_tolerance(delta, baseline, thresholds) for _, delta, baseline in variances)
    outcome = Outcome.HOLD_FOR_REVIEW if hold else Outcome.MINOR_VARIANCE_REVIEW if monetary else Outcome.MATCHED_DRAFT
    reasons = structural + monetary
    if invoice.stated_line_total is None:
        reasons.append("Stated line total is absent; calculated amounts only were compared.")
    if not structural and not monetary:
        reasons.append("Required fields and calculated vendor costs match. Draft only; human review is still required.")
    return ReconciliationResult(outcome=outcome, reasons=reasons, purchase_order=po,
                                expected_vendor_cost=expected, invoiced_cost=invoiced, difference=difference,
                                stated_total_difference=stated_delta,
                                percent_difference=None if expected == 0 else difference / expected * 100)
