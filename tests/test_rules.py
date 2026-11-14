from datetime import date
from decimal import Decimal

from pydantic import ValidationError
import pytest

from reconciliation.models import Invoice, Outcome, Thresholds
from reconciliation.reconcile import reconcile, within_tolerance


def changed(invoice, **updates):
    return Invoice.model_validate({**invoice.model_dump(), **updates})


@pytest.mark.parametrize("field,value", [
    ("quantity", 0), ("quantity", 1.2), ("quantity", "1"), ("rental_days", -1),
    ("daily_rate", "-1.00"), ("daily_rate", "NaN"), ("daily_rate", "1.005"),
    ("stated_line_total", "Infinity"), ("vendor", " "), ("rental_start", "not-a-date"),
])
def test_validation_rejects_invalid_fields(invoice, field, value):
    with pytest.raises(ValidationError):
        changed(invoice, **{field: value})


def test_overcharge_decimal_calculation(invoice, orders):
    result = reconcile(invoice, orders)
    assert result.expected_vendor_cost == Decimal("1200.00")
    assert result.invoiced_cost == Decimal("1350.00")
    assert result.difference == Decimal("150.00")
    assert result.percent_difference == Decimal("12.5")
    assert result.outcome == Outcome.HOLD_FOR_REVIEW


@pytest.mark.parametrize("delta,baseline,expected", [
    ("0.50", "100", True), ("-0.50", "100", True),
    ("0.51", "10000", False),  # passes percentage but fails absolute
    ("0.40", "10", False),     # passes absolute but fails percentage
    ("0.00", "0", True), ("0.01", "0", False),
])
def test_both_thresholds_and_zero_baseline(delta, baseline, expected):
    assert within_tolerance(Decimal(delta), Decimal(baseline), Thresholds()) is expected


@pytest.mark.parametrize("rate,total,outcome", [
    ("400.00", "1200.00", Outcome.MATCHED_DRAFT),
    ("400.10", "1200.30", Outcome.MINOR_VARIANCE_REVIEW),
    ("399.90", "1199.70", Outcome.MINOR_VARIANCE_REVIEW),
    ("400.20", "1200.60", Outcome.HOLD_FOR_REVIEW),
    ("400.00", "1300.00", Outcome.HOLD_FOR_REVIEW),
    ("400.00", "1200.20", Outcome.MINOR_VARIANCE_REVIEW),
])
def test_variance_classifications(invoice, orders, rate, total, outcome):
    assert reconcile(changed(invoice, daily_rate=rate, stated_line_total=total), orders).outcome == outcome


@pytest.mark.parametrize("field", ["po_number", "quantity", "rental_days", "rental_start", "daily_rate", "equipment_id", "invoice_number"])
def test_missing_required_information(invoice, orders, field):
    result = reconcile(changed(invoice, **{field: None}), orders)
    assert result.outcome == Outcome.MISSING_INFORMATION
    assert field in result.reasons[0]


@pytest.mark.parametrize("updates,reason", [
    ({"equipment_id": "WRONG"}, "Equipment ID"),
    ({"equipment_name": "Wrong name"}, "equipment_name"),
    ({"vendor": "Wrong vendor"}, "vendor"),
    ({"rental_start": date(2026, 11, 1)}, "rental_start"),
    ({"rental_end": date(2026, 10, 31)}, "Rental dates"),
    ({"quantity": 2}, "quantity"),
    ({"rental_days": 4}, "rental_days"),
    ({"rate_basis": "weekly"}, "Only daily"),
])
def test_structural_exceptions_cannot_be_tolerated(invoice, orders, updates, reason):
    result = reconcile(changed(invoice, **updates), orders, Thresholds(absolute="999999.00", percent="100"))
    assert result.outcome == Outcome.HOLD_FOR_REVIEW
    assert any(reason in text for text in result.reasons)


def test_unsupported_rate_has_no_daily_calculation(invoice, orders):
    result = reconcile(changed(invoice, rate_basis="weekly"), orders)
    assert result.invoiced_cost is None


def test_unknown_po(invoice, orders):
    assert reconcile(changed(invoice, po_number="PO-404"), orders).outcome == Outcome.UNMATCHED_PO


def test_duplicate_po_lines_require_review(invoice, orders):
    result = reconcile(invoice, orders + [orders[0]])
    assert result.outcome == Outcome.HOLD_FOR_REVIEW
    assert "ambiguous" in result.reasons[0]


def test_dates_disambiguate_equipment_lines(invoice, orders):
    other = orders[0].model_copy(update={"rental_start": date(2026, 12, 1), "rental_end": date(2026, 12, 3)})
    assert reconcile(invoice, orders + [other]).purchase_order == orders[0]


def test_optional_stated_total_is_disclosed(invoice, orders):
    result = reconcile(changed(invoice, daily_rate="400.00", stated_line_total=None), orders)
    assert result.outcome == Outcome.MATCHED_DRAFT
    assert any("absent" in text for text in result.reasons)


def test_bad_po_dates_are_not_ignored(invoice, orders):
    bad = orders[0].model_copy(update={"rental_end": date(2026, 11, 9)})
    assert any("Approved PO dates" in text for text in reconcile(invoice, [bad]).reasons)


@pytest.mark.parametrize("values", [{"absolute": "-0.01"}, {"percent": "NaN"}, {"percent": "101"}])
def test_invalid_thresholds(values):
    with pytest.raises(ValidationError):
        Thresholds(**values)
