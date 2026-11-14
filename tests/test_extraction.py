from decimal import Decimal
import socket

import pymupdf
import pytest

from reconciliation.models import Outcome
from reconciliation.parser import parse_invoice
from reconciliation.pdf import OCRUnavailableError, PDFExtractionError, extract_pdf_text
from reconciliation.pipeline import analyze_invoice


@pytest.mark.parametrize("filename,method,outcome,difference", [
    ("invoice_a_digital.pdf", "digital", Outcome.HOLD_FOR_REVIEW, Decimal("150.00")),
    ("invoice_b_scanned.pdf", "ocr", Outcome.MATCHED_DRAFT, Decimal("0.00")),
    ("invoice_c_unknown_po.pdf", "digital", Outcome.UNMATCHED_PO, None),
    ("invoice_d_wrong_equipment.pdf", "digital", Outcome.HOLD_FOR_REVIEW, None),
    ("invoice_e_missing_po.pdf", "digital", Outcome.MISSING_INFORMATION, None),
    ("invoice_f_wrong_dates.pdf", "digital", Outcome.HOLD_FOR_REVIEW, Decimal("0.00")),
])
def test_complete_workflow_without_network(demo_data, monkeypatch, filename, method, outcome, difference):
    def forbidden(*args, **kwargs):
        raise AssertionError("Application attempted a network connection")
    monkeypatch.setattr(socket.socket, "connect", forbidden)
    analysis = analyze_invoice(demo_data / "invoices" / filename, demo_data / "purchase_orders.csv")
    assert analysis.source.method == method
    assert analysis.source.pages[0].page_number == 1
    assert analysis.source.pages[0].source_filename == filename
    assert not analysis.parsed.errors
    assert analysis.result.outcome == outcome
    assert analysis.result.difference == difference


def test_scan_has_pixels_and_no_text_layer(demo_data):
    with pymupdf.open(demo_data / "invoices/invoice_b_scanned.pdf") as pdf:
        assert not pdf[0].get_text().strip()
        assert pdf[0].get_images()


def test_missing_tesseract_fails_clearly(demo_data, monkeypatch):
    monkeypatch.setattr("reconciliation.pdf.shutil.which", lambda _: None)
    with pytest.raises(OCRUnavailableError, match="Tesseract"):
        extract_pdf_text(demo_data / "invoices/invoice_b_scanned.pdf")
    assert extract_pdf_text(demo_data / "invoices/invoice_a_digital.pdf").method == "digital"


def test_mixed_document_processes_each_page(demo_data, tmp_path):
    path = tmp_path / "mixed.pdf"
    with pymupdf.open() as mixed:
        for name in ("invoice_a_digital.pdf", "invoice_b_scanned.pdf"):
            with pymupdf.open(demo_data / "invoices" / name) as source:
                mixed.insert_pdf(source)
        mixed.save(path)
    result = extract_pdf_text(path)
    assert result.method == "mixed"
    assert [p.method for p in result.pages] == ["digital", "ocr"]
    # This parser deliberately refuses multiple invoice fields in one document.
    assert parse_invoice(result.text).errors


@pytest.mark.parametrize("content", [b"", b"not a PDF"])
def test_broken_pdf_is_explicit(tmp_path, content):
    path = tmp_path / "broken.pdf"
    path.write_bytes(content)
    with pytest.raises(PDFExtractionError):
        extract_pdf_text(path)


def test_blank_page_does_not_invent_invoice(tmp_path):
    path = tmp_path / "blank.pdf"
    with pymupdf.open() as pdf:
        pdf.new_page()
        pdf.save(path)
    source = extract_pdf_text(path)
    assert source.method == "ocr"
    assert not source.text.strip()
    assert any("no readable text" in w for w in source.warnings)
    parsed = parse_invoice(source.text)
    assert parsed.invoice.po_number is None


@pytest.mark.parametrize("text,field", [
    ("Quantity: 1.5", "quantity"), ("Daily rate: $1.005", "daily_rate"),
    ("Rental start: 11/02/2026", "rental_start"), ("Rental end: 2026-02-30", "rental_end"),
    ("Quantity: 1\nQuantity: 2", "quantity"), ("Daily rate: NaN", "daily_rate"),
])
def test_ambiguous_and_invalid_text_is_flagged(text, field):
    parsed = parse_invoice(text)
    assert any(error.startswith(field + ":") for error in parsed.errors)


def test_duplicate_fields_trigger_extraction_review(demo_data, tmp_path):
    path = tmp_path / "duplicate.pdf"
    with pymupdf.open() as pdf:
        page = pdf.new_page()
        page.insert_text((50, 50), "Invoice number: FIRST\nInvoice number: SECOND\nVendor: Fictional equipment supplier")
        pdf.save(path)
    assert analyze_invoice(path, demo_data / "purchase_orders.csv").result.outcome == Outcome.EXTRACTION_REVIEW


def test_usd_thousands_and_missing_values():
    parsed = parse_invoice("Daily rate: $1,234.50\nVendor: \nQuantity: 1")
    assert parsed.invoice.daily_rate == Decimal("1234.50")
    assert parsed.invoice.vendor is None
    assert parsed.invoice.po_number is None
