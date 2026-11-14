"""Session-only human review of bundled synthetic invoices."""
from decimal import Decimal, InvalidOperation
from hashlib import sha256
from pathlib import Path

import pandas as pd
import pymupdf
from pydantic import ValidationError
import streamlit as st

from reconciliation.models import Thresholds
from reconciliation.pdf import PDFExtractionError
from reconciliation.pipeline import analyze_invoice
from reconciliation.reconcile import load_purchase_orders

ROOT = Path(__file__).resolve().parent
st.set_page_config(page_title="Invoice reconciliation demo", layout="wide")
st.title("Equipment invoice review")
st.caption("LOCAL FEASIBILITY DEMO — SYNTHETIC DATA — NO PRODUCTION WRITES")
st.write("Compare fictional vendor invoices with approved purchase orders. Every outcome is a draft for human review.")

with st.sidebar:
    st.header("Review settings")
    files = sorted((ROOT / "data/invoices").glob("*.pdf"))
    if not files:
        st.error("Generate the demo data first: python -m scripts.generate_demo")
        st.stop()
    selected = st.selectbox("Synthetic invoice", [path.name for path in files])
    absolute = st.text_input("Absolute tolerance (USD)", "0.50")
    percent = st.text_input("Percentage tolerance (%)", "0.5")
    st.caption("Example policy only. Both limits must pass for a minor variance. Identity and date exceptions always require review.")
    try:
        thresholds = Thresholds(absolute=Decimal(absolute), percent=Decimal(percent))
    except (ValidationError, InvalidOperation):
        st.error("Enter a nonnegative USD tolerance (up to two decimal places) and a percentage from 0 to 100.")
        st.stop()

path = ROOT / "data/invoices" / selected


@st.cache_data(show_spinner=False)
def analyze_cached(filename, document_digest, po_digest, absolute, percent):
    # Digests invalidate the cache when either source file changes.
    return analyze_invoice(ROOT / "data/invoices" / filename, ROOT / "data/purchase_orders.csv",
                           Thresholds(absolute=absolute, percent=percent))


try:
    with st.spinner("Reading PDF and comparing vendor costs…"):
        digest = sha256(path.read_bytes()).hexdigest()
        po_digest = sha256((ROOT / "data/purchase_orders.csv").read_bytes()).hexdigest()
        analysis = analyze_cached(selected, digest, po_digest, thresholds.absolute, thresholds.percent)
except (PDFExtractionError, OSError, ValidationError, ValueError) as exc:
    st.error(f"Cannot complete analysis: {exc}")
    st.stop()

result = analysis.result
st.subheader(result.outcome.value)
for reason in result.reasons:
    st.write(f"• {reason}")


def usd(value):
    return "Not calculated" if value is None else f"${value:,.2f}"


metrics = st.columns(3)
metrics[0].metric("Expected vendor cost", usd(result.expected_vendor_cost))
metrics[1].metric("Calculated invoice cost", usd(result.invoiced_cost))
metrics[2].metric("Invoice − expected", usd(result.difference))

left, right = st.columns([1.1, 1])
with left:
    st.subheader("Source document")
    st.caption(f"{analysis.source.source_filename} · Processing: {analysis.source.method}")
    page_number = st.selectbox("Page", range(1, len(analysis.source.pages) + 1))
    with pymupdf.open(path) as document:
        st.image(document[page_number - 1].get_pixmap(dpi=110).tobytes("png"), width="stretch")
    for warning in analysis.source.warnings:
        st.warning(warning)
    with st.expander("Extracted text and page provenance"):
        for page in analysis.source.pages:
            st.caption(f"{page.source_filename} · page {page.page_number} · {page.method}")
            st.text(page.text)

with right:
    st.subheader("Extracted invoice fields")
    fields = analysis.parsed.invoice.model_dump(mode="json") if analysis.parsed.invoice else analysis.parsed.raw_fields
    st.dataframe(pd.DataFrame([{"Field": k.replace("_", " "), "Value": "Missing" if v is None else str(v)} for k, v in fields.items()]),
                 hide_index=True, width="stretch", height=310)
    st.subheader("Matched purchase order")
    if result.purchase_order:
        st.dataframe(pd.DataFrame([{"Field": k.replace("_", " "), "Approved": str(v)} for k, v in result.purchase_order.model_dump(mode="json").items()]),
                     hide_index=True, width="stretch", height=260)
    else:
        st.info("No unique PO line was selected. Review the exception above.")
        with st.expander("Available synthetic purchase orders"):
            st.dataframe(pd.DataFrame([po.model_dump(mode="json") for po in load_purchase_orders(ROOT / "data/purchase_orders.csv")]), hide_index=True)
    if result.stated_total_difference is not None:
        st.caption(f"Stated total − calculated invoice cost: {usd(result.stated_total_difference)}")
    review_key = f"review_{digest}_{po_digest}_{thresholds.absolute}_{thresholds.percent}"
    if review_key not in st.session_state:
        st.session_state[review_key] = st.session_state.get(f"saved_{review_key}", "Needs Review")
    status = st.selectbox("Human review status", ["Needs Review", "Reviewed"], key=review_key)
    # Preserve the status even while the corresponding widget is not rendered.
    st.session_state[f"saved_{review_key}"] = status
    st.caption("Review status lasts only in this browser session. Reviewed does not approve or post an invoice.")
