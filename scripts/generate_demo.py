"""Generate only fictional, labelled documents; no business records are used."""
import csv
import json
from pathlib import Path

import pymupdf
from PIL import Image
from reportlab.pdfgen import canvas

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
BANNER = "SYNTHETIC DEMO — NOT A REAL INVOICE."
LABELS = {
    "invoice_number": "Invoice number", "vendor": "Vendor", "po_number": "PO number",
    "equipment_id": "Equipment ID", "equipment_name": "Equipment name",
    "quantity": "Quantity", "rental_days": "Rental days", "rental_start": "Rental start",
    "rental_end": "Rental end", "rate_basis": "Rate basis", "daily_rate": "Daily rate",
    "stated_line_total": "Line total",
}


def records():
    a = dict(invoice_number="DEMO-A", vendor="Example Equipment Rentals", po_number="PO-1001",
             equipment_id="EX-01", equipment_name="Excavator", quantity=1, rental_days=3,
             rental_start="2026-11-02", rental_end="2026-11-04", rate_basis="daily",
             daily_rate="450.00", stated_line_total="1350.00")
    b = dict(invoice_number="DEMO-B", vendor="Sample Lift Services", po_number="PO-1002",
             equipment_id="SL-01", equipment_name="Scissor Lift", quantity=1, rental_days=2,
             rental_start="2026-11-05", rental_end="2026-11-06", rate_basis="daily",
             daily_rate="150.00", stated_line_total="300.00")
    return {
        "invoice_a_digital.pdf": a,
        "invoice_b_scanned.pdf": b,
        "invoice_c_unknown_po.pdf": {**a, "invoice_number": "DEMO-C", "po_number": "PO-9999"},
        "invoice_d_wrong_equipment.pdf": {**b, "invoice_number": "DEMO-D", "equipment_id": "SL-99"},
        "invoice_e_missing_po.pdf": {**b, "invoice_number": "DEMO-E", "po_number": None},
        "invoice_f_wrong_dates.pdf": {**b, "invoice_number": "DEMO-F", "rental_start": "2026-11-07", "rental_end": "2026-11-08"},
    }


def generate(destination=DATA):
    destination = Path(destination)
    (destination / "invoices").mkdir(parents=True, exist_ok=True)
    truth = records()
    for filename, record in truth.items():
        path = destination / "invoices" / filename
        if filename == "invoice_b_scanned.pdf":
            # Rasterize a temporary vector page, then embed ONLY pixels in the final PDF.
            vector = destination / "invoices" / "_raster_source.pdf"
            draw_pdf(vector, record)
            with pymupdf.open(vector) as pdf:
                pix = pdf[0].get_pixmap(dpi=220)
                with pymupdf.open() as scan:
                    page = scan.new_page(width=612, height=792)
                    page.insert_image(page.rect, stream=pix.tobytes("png"))
                    scan.save(path, deflate=True)
            vector.unlink()
        else:
            draw_pdf(path, record)
    # Use Pillow to inspect the generated raster without adding another PDF renderer.
    with pymupdf.open(destination / "invoices" / "invoice_b_scanned.pdf") as pdf:
        pix = pdf[0].get_pixmap(dpi=72)
        image = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
        assert image.getbbox() is not None
        assert not pdf[0].get_text().strip(), "Scanned fixture must have no text layer"
    with (destination / "ground_truth.json").open("w") as f:
        json.dump(truth, f, indent=2)
        f.write("\n")
    po_fields = ["po_number", "vendor", "equipment_id", "equipment_name", "quantity", "rental_days",
                 "rental_start", "rental_end", "rate_basis", "approved_daily_rate"]
    with (destination / "purchase_orders.csv").open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=po_fields, lineterminator="\n")
        writer.writeheader()
        for name, rate in [("invoice_a_digital.pdf", "400.00"), ("invoice_b_scanned.pdf", "150.00")]:
            record = truth[name]
            writer.writerow({**{k: record[k] for k in po_fields if k != "approved_daily_rate"},
                             "approved_daily_rate": rate})
    return truth


def draw_pdf(path, record):
    pdf = canvas.Canvas(str(path), pagesize=(612, 792), invariant=1)
    pdf.setTitle("Synthetic equipment rental invoice")
    pdf.setFont("Helvetica-Bold", 14)
    pdf.drawString(35, 750, BANNER)
    pdf.setFont("Helvetica", 13)
    pdf.drawString(35, 720, "Fictional equipment rental | One line item | USD")
    y = 680
    for key, label in LABELS.items():
        value = record[key]
        if value is not None:
            pdf.drawString(35, y, f"{label}: {value}")
            y -= 32
    pdf.setFont("Helvetica", 10)
    pdf.drawString(35, 100, "Rental dates are inclusive. No tax, fees, or customer billing in this demo.")
    pdf.drawString(35, 80, "SYNTHETIC DEMO — NOT A REAL INVOICE.")
    pdf.save()


if __name__ == "__main__":
    print(f"Generated {len(generate())} synthetic invoices and 2 purchase orders in {DATA}")
