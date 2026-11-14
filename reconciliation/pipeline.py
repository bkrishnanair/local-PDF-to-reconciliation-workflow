from dataclasses import dataclass
from pathlib import Path

from reconciliation.models import Outcome, ReconciliationResult, Thresholds
from reconciliation.parser import ParsedInvoice, parse_invoice
from reconciliation.pdf import PDFText, extract_pdf_text
from reconciliation.reconcile import load_purchase_orders, reconcile


@dataclass
class Analysis:
    source: PDFText
    parsed: ParsedInvoice
    result: ReconciliationResult


def analyze_invoice(path: str | Path, po_path: str | Path, thresholds: Thresholds | None = None) -> Analysis:
    source = extract_pdf_text(path)
    parsed = parse_invoice(source.text)
    if parsed.errors or parsed.invoice is None:
        result = ReconciliationResult(outcome=Outcome.EXTRACTION_REVIEW,
                                      reasons=parsed.errors or ["No validated invoice was recovered."])
    else:
        result = reconcile(parsed.invoice, load_purchase_orders(po_path), thresholds)
    return Analysis(source, parsed, result)
