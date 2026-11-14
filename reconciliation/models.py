"""Validated data contracts. Missing values stay missing; money uses Decimal."""
from datetime import date
from decimal import Decimal
from enum import StrEnum
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, field_validator

Money = Annotated[Decimal, Field(ge=0, max_digits=12, decimal_places=2, allow_inf_nan=False)]
Count = Annotated[int, Field(gt=0, strict=True)]


class Invoice(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    invoice_number: str | None = None
    vendor: str | None = None
    po_number: str | None = None
    equipment_id: str | None = None
    equipment_name: str | None = None
    quantity: Count | None = None
    rental_days: Count | None = None
    rental_start: date | None = None
    rental_end: date | None = None
    rate_basis: str | None = None
    daily_rate: Money | None = None
    stated_line_total: Money | None = None

    @field_validator("invoice_number", "vendor", "po_number", "equipment_id", "equipment_name", "rate_basis")
    @classmethod
    def no_empty_strings(cls, value):
        if value is not None and not value.strip():
            raise ValueError("Blank fields must be represented as missing")
        return value


class PurchaseOrder(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    po_number: str = Field(min_length=1)
    vendor: str = Field(min_length=1)
    equipment_id: str = Field(min_length=1)
    equipment_name: str = Field(min_length=1)
    quantity: Count
    rental_days: Count
    rental_start: date
    rental_end: date
    rate_basis: str = Field(min_length=1)
    approved_daily_rate: Money


class Thresholds(BaseModel):
    model_config = ConfigDict(frozen=True)
    absolute: Money = Decimal("0.50")
    percent: Annotated[Decimal, Field(ge=0, le=100, allow_inf_nan=False)] = Decimal("0.5")


class Outcome(StrEnum):
    MATCHED_DRAFT = "MATCHED_DRAFT"
    MINOR_VARIANCE_REVIEW = "MINOR_VARIANCE_REVIEW"
    HOLD_FOR_REVIEW = "HOLD_FOR_REVIEW"
    MISSING_INFORMATION = "MISSING_INFORMATION"
    UNMATCHED_PO = "UNMATCHED_PO"
    EXTRACTION_REVIEW = "EXTRACTION_REVIEW"


class ReconciliationResult(BaseModel):
    outcome: Outcome
    reasons: list[str]
    purchase_order: PurchaseOrder | None = None
    expected_vendor_cost: Decimal | None = None
    invoiced_cost: Decimal | None = None
    difference: Decimal | None = None
    stated_total_difference: Decimal | None = None
    percent_difference: Decimal | None = None
