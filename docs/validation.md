# Validation record

Executed in the cloud Linux environment during the November 13, 2026 evening session (America/New_York). The measured report records UTC execution time and software versions. macOS execution has not been performed.

| Check | Actual outcome |
| --- | --- |
| Fresh Python 3.12.14 virtualenv, locked dependencies | Installed successfully; `uv pip check` confirmed all 119 installed packages compatible |
| `python -m scripts.generate_demo` | Six labelled synthetic PDFs and two approved PO rows generated |
| `python -m pytest -q`, host | **68 passed**, latest host run 7.89 seconds |
| `python -m scripts.evaluate` | Digital **60/60**, OCR **12/12**, zero field errors |
| `python -m scripts.execute_notebook` | Six code cells executed and saved, no error outputs |
| Chromium, host application | Overcharge rendered; no JavaScript errors or external requests observed |
| Docker image build, Python 3.12.14 slim | Succeeded with optional trusted build CA secret; all pip hashes checked |
| `docker run --rm --network none equipment-reconciliation-demo python -m pytest -q` | **68 passed**, 3.05 seconds |
| Container evaluation, `--network none` | Digital **60/60**, OCR **12/12**, zero field errors |
| Container notebook execution, `--network none` | Executed and saved successfully inside the disposable container |
| Chromium, running Docker application | See `browser-validation.json`; both digital overcharge and scanned match rendered |

The tests include the Streamlit review controls as well as actual Tesseract calls. The container's disabled network demonstrates that the tested application paths, tests, evaluation, and notebook do not need external connectivity after installation. The browser observation is bounded to the exercised flow; it is not a general network audit.

## Setup issues resolved

- The host's default package cache was read-only. A project-local ignored cache under `artifacts/uv-cache` resolved installation.
- The first Docker build failed HTTPS certificate verification at PyPI. The successful build mounted the cloud host's trusted combined public CA bundle through a temporary BuildKit secret. TLS verification and package hashes remained enabled; the bundle was not added to image layers.
- The host virtualenv was created by uv without pip. Dependency consistency was verified with `uv pip check`, rather than `python -m pip check`. The Docker and documented macOS virtualenvs use pip for installation.
- Notebook execution prints a kernel transport warning about local TCP without encryption. The kernel is used within the local development session, not exposed as an application service. The notebook still completed; this does not authorize exposing Jupyter publicly.

## Interpretation

There are 12 labelled fields per invoice. Five digital PDFs give 60 field slots, including the intentionally missing PO value; the single clean 220-DPI scan gives 12. The parser recovers every expected value in this controlled set. This says nothing about accuracy across unseen vendors, degraded scans, multi-line tables, real date conventions, or production approval suitability.

No tests were intentionally skipped or marked expected-failure. The optional language-model experiment was not run. No production service or business record was accessed or modified.

## Phase checkpoints

| Phase | Built and executed | What to understand before presenting |
| --- | --- | --- |
| 1: Fixtures | `python -m scripts.generate_demo`; six PDFs, PO CSV, ground truth generated; scanned PDF verified to have no text layer | The records are invented. A clean scan is much easier than many real invoices. |
| 2: PDF/OCR | `extract_pdf_text` called by pipeline tests and evaluation; actual OCR, mixed-page routing, missing executable, blank/corrupt PDF tests passed | PDF text extraction and OCR are different paths. OCR can fail or misread; warnings and provenance remain visible. |
| 3: Fields | `python -m pytest -q`; schema and parser checks passed, including duplicates and ambiguous dates | Labels and ISO dates are deliberately restricted. Missing values are not guessed. |
| 4: Rules | Same test suite; Decimal amounts, $150 overcharge, missing/unknown PO, identities, dates, and both tolerances passed | Money matching does not override identity/date exceptions. All outcomes remain drafts. |
| 5: Review | Streamlit AppTest plus real Chromium checks passed; screenshot captured | Reviewed is session state, not approval, persistence, or posting. |
| 6: Evaluation | `python -m scripts.evaluate` and `python -m scripts.execute_notebook`; real measurements and six executed notebook cells | 60/60 digital and 12/12 scanned describe only these controlled fixtures. |
| 7: Reproducibility | Tested installation refresh script, dependency consistency, fresh Docker installation, offline container tests/evaluation/notebook | Python and OCR dependencies install with a network connection; runtime needs none. macOS remains untested. |
| 8: Optional model | Not implemented or tested; no usable Ollama installation found | This demo makes no language-model performance claim and needs no GPU. |

No required application checks failed after setup corrections. The installation and Docker failures and their fixes are recorded above. The remaining handoff task is the author's workflow explanation and five practice answers in `docs/practice.md`; those have been requested, not assessed yet.
