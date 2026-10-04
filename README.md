# bill-check

Checks an Indian GST bill after OCR and returns approve, review or reject, with reasons.

- GSTIN check digit. If one character was misread (1/I, 0/O, 5/S, 8/B), it tries the swap before rejecting.
- CGST equals SGST, and line items and totals reconcile, with tax added on top or inside the MRP. Discounts are allowed.
- A second upload with the same GSTIN, bill number, date and total is flagged as a reused bill.

Takes about 8 microseconds per bill. Standard library only.

```
python3 bill_check.py   # runs the built-in checks
```
