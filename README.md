# bill-check

Instant checks for an OCR'd Indian GST bill: approve, review, or reject, with reasons.

- GSTIN check digit, with one-swap repair of common OCR misreads (1/I, 0/O, 5/S, 8/B)
- CGST equals SGST, line items and totals reconcile (tax added on top or inside MRP, discounts allowed)
- Same GSTIN, bill number, date and total from a second upload is flagged as a reused bill

About 8 microseconds per bill, standard library only.

```
python3 bill_check.py   # runs the built-in checks
```
