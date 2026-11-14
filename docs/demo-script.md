# 60-second walkthrough

**0–10 seconds:** “I built a small feasibility demo using fictional equipment invoices. It does not connect to any business system or approve payments.”

**10–25 seconds:** Open invoice A. “This invoice has readable PDF text. The approved excavator rate is $400 per day, but the invoice says $450 for three days. The difference is $150, so it is held for review.” Point to the original, the PO, and the calculated difference.

**25–40 seconds:** Open invoice B. “This file is a picture inside a PDF, so local OCR reads it first. Its $150 daily rate for two days matches the purchase order. Matching produces a draft, not an approval.”

**40–50 seconds:** Open invoice F. “The money matches here, but the rental dates do not. That still needs review. Small dollar differences are checked against both an absolute and a percentage limit.”

**50–60 seconds:** Change Human review status to Reviewed. “This only records a choice in this session. The controlled examples work, including the clean scan. The next step would be permission to evaluate a representative labelled sample and agree on the business rules.”

If asked about AI: “The baseline uses local OCR and deterministic Python rules. I have not evaluated a local language model yet. Keeping that optional makes extraction failures and comparison decisions easier to inspect.”
