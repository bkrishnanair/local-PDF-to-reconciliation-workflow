"""Run the real extraction measurement and save an inspectable report."""
import json
import platform
from datetime import datetime, timezone
from importlib.metadata import version

import pytesseract

from reconciliation.evaluation import evaluate
from scripts.generate_demo import ROOT


def main():
    documents, fields, summary = evaluate(ROOT / "data")
    report = {
        "executed_at_utc": datetime.now(timezone.utc).isoformat(),
        "python": platform.python_version(),
        "tesseract": str(pytesseract.get_tesseract_version()).splitlines()[0],
        "pymupdf": version("PyMuPDF"),
        "summary": summary.to_dict(orient="records"),
        "documents": documents, "fields": fields.to_dict(orient="records"),
    }
    output = ROOT / "docs/evaluation.json"
    output.parent.mkdir(exist_ok=True)
    output.write_text(json.dumps(report, indent=2) + "\n")
    print(summary.to_string(index=False))
    print(f"Field errors: {len(fields[~fields.correct])}; report: {output}")


if __name__ == "__main__":
    main()
