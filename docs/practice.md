# Explain it back

Without reading the README, describe the full path from a PDF to a human-review result. Mention where OCR, schema validation, PO matching, money arithmetic, and human judgment enter the workflow. Explain which inputs are fictional and which results were measured.

Then answer these five interview questions aloud:

1. Why does invoice B need OCR while invoice A does not? What happens if Tesseract is missing?
2. How do the approved rate, invoice rate, quantity, and rental days produce the $150 discrepancy?
3. What happens if a difference passes the absolute tolerance but fails the percentage tolerance? What if the baseline is zero?
4. Why do wrong equipment or dates require review even if the dollar difference is zero? What does Reviewed actually change?
5. What does perfect extraction on these fixtures tell us, what does it not tell us, and what must happen before testing actual invoices?

Try answering before reading the implementation. You should be able to explain each rule in plain language and point to its test.
