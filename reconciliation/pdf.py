"""Page-by-page text extraction, with real local OCR when the text layer is weak."""
from dataclasses import dataclass
from pathlib import Path
import shutil

import pymupdf
import pytesseract
from PIL import Image


class PDFExtractionError(RuntimeError):
    pass


class OCRUnavailableError(PDFExtractionError):
    pass


@dataclass
class PageText:
    source_filename: str
    page_number: int
    text: str
    method: str
    warnings: list[str]


@dataclass
class PDFText:
    source_filename: str
    text: str
    method: str
    pages: list[PageText]
    warnings: list[str]


def extract_pdf_text(file_path: str | Path) -> PDFText:
    """Extract each page. Heuristic: >=40 alphanumeric text-layer characters.

    This is not a general table extractor. A small or misleading text layer can
    fool this heuristic; extraction and business validation remain separate.
    """
    path = Path(file_path)
    pages = []
    try:
        with pymupdf.open(path) as document:
            if document.needs_pass:
                raise PDFExtractionError("Encrypted PDFs are not supported by this demo.")
            if not document.is_pdf or not len(document):
                raise PDFExtractionError("Expected a nonempty PDF.")
            if len(document) > 10:
                raise PDFExtractionError("Demo limit is 10 pages per document.")
            for number, page in enumerate(document, 1):
                warnings = []
                text = page.get_text("text", sort=True)
                if sum(char.isalnum() for char in text) >= 40:
                    method = "digital"
                else:
                    if not shutil.which(pytesseract.pytesseract.tesseract_cmd):
                        raise OCRUnavailableError("Tesseract executable is unavailable. Install Tesseract with English language data.")
                    # Bound rendering memory even for unusually large PDF page dimensions.
                    if page.rect.width * page.rect.height * (220 / 72) ** 2 > 40_000_000:
                        raise PDFExtractionError("Page exceeds the demo's OCR pixel limit.")
                    pix = page.get_pixmap(dpi=220, colorspace=pymupdf.csRGB, alpha=False)
                    image = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
                    try:
                        text = pytesseract.image_to_string(image, lang="eng", config="--psm 6", timeout=45)
                    except pytesseract.TesseractNotFoundError as exc:
                        raise OCRUnavailableError("Tesseract is unavailable.") from exc
                    except (pytesseract.TesseractError, RuntimeError) as exc:
                        raise PDFExtractionError(f"OCR failed on page {number}: {exc}") from exc
                    method = "ocr"
                    warnings.append(f"Page {number}: OCR text must be checked against the image; table layout is not guaranteed.")
                if not text.strip():
                    warnings.append(f"Page {number}: no readable text was recovered.")
                pages.append(PageText(path.name, number, text, method, warnings))
    except (pymupdf.FileDataError, pymupdf.EmptyFileError, FileNotFoundError) as exc:
        raise PDFExtractionError(f"Cannot read PDF {path.name}: {exc}") from exc
    methods = {page.method for page in pages}
    return PDFText(path.name, "\n".join(page.text for page in pages),
                   next(iter(methods)) if len(methods) == 1 else "mixed", pages,
                   [warning for page in pages for warning in page.warnings])
