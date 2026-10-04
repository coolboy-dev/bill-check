"""Instant checks for an OCR'd Indian GST bill: approve, review, or reject, with reasons.

The idea: most genuine bills pass every check in under a millisecond, so they can be
approved on the spot. Only bills that fail something go to the human review queue.
"""
import re
from datetime import date, timedelta

CHARS = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ"
GSTIN_RE = re.compile(r"^\d{2}[A-Z]{5}\d{4}[A-Z][1-9A-Z]Z[0-9A-Z]$")
# characters OCR commonly swaps on thermal paper
OCR_SWAPS = {"0": "O", "O": "0", "1": "I", "I": "1", "5": "S", "S": "5",
             "8": "B", "B": "8", "2": "Z", "Z": "2", "6": "G", "G": "6"}
TOL = 1.0  # rupees, bills round to the nearest rupee or paisa
MAX_AGE = timedelta(days=30)


def gstin_ok(g):
    """Format plus the mod 36 check digit every real GSTIN carries."""
    if not GSTIN_RE.match(g):
        return False
    s = 0
    for i, c in enumerate(g[:14]):
        p = CHARS.index(c) * (2 if i % 2 else 1)
        s += p // 36 + p % 36
    return CHARS[(36 - s % 36) % 36] == g[14]


def repair_gstin(g):
    """Try one OCR swap at a time. One fix = probably a misread, not a fake bill."""
    fixes = [g[:i] + OCR_SWAPS[c] + g[i + 1:] for i, c in enumerate(g) if c in OCR_SWAPS]
    good = [f for f in fixes if gstin_ok(f)]
    return good[0] if len(good) == 1 else None


def check(bill, seen, today=None):
    """bill: dict from OCR. seen: set of keys of bills already accepted (shared across users)."""
    today = today or date.today()
    hard, soft = [], []

    g = bill.get("gstin", "").upper().replace(" ", "")
    if not gstin_ok(g):
        fixed = repair_gstin(g)
        if fixed:
            soft.append(f"GSTIN {g} looks misread, {fixed} passes the check digit")
            g = fixed
        else:
            hard.append(f"GSTIN {g or '(none)'} fails the check digit")

    for it in bill.get("items", []):
        if abs(it["qty"] * it["rate"] - it["amount"]) > TOL:
            soft.append(f"{it['name']}: {it['qty']} x {it['rate']} != {it['amount']}")
    items_sum = sum(it["amount"] for it in bill.get("items", []))
    if abs(items_sum - bill["subtotal"]) > TOL:
        hard.append(f"items add up to {items_sum:.2f}, bill says subtotal {bill['subtotal']}")

    cgst, sgst, igst = bill.get("cgst", 0), bill.get("sgst", 0), bill.get("igst", 0)
    if abs(cgst - sgst) > TOL:
        hard.append(f"CGST {cgst} != SGST {sgst}, they are always equal")
    if igst and (cgst or sgst):
        hard.append("IGST and CGST/SGST on the same bill")
    # tax added on top, or MRP bills where tax is already inside the prices
    net = bill["subtotal"] - bill.get("discount", 0)
    if min(abs(net + cgst + sgst + igst - bill["total"]), abs(net - bill["total"])) > TOL:
        hard.append(f"subtotal, discount and tax don't reconcile with total {bill['total']}, total may be edited")

    d = date.fromisoformat(bill["date"])
    if d > today:
        hard.append(f"dated in the future ({d})")
    elif today - d > MAX_AGE:
        soft.append(f"{(today - d).days} days old")

    key = (g, bill.get("bill_no", ""), bill["date"], round(bill["total"]))
    if key in seen:
        hard.append("same GSTIN, bill no, date and total already uploaded")

    verdict = "reject" if hard else "review" if soft else "approve"
    if verdict != "reject":
        seen.add(key)
    return verdict, hard + soft


def demo():
    today = date(2026, 10, 4)
    base = {
        "gstin": "27AAPFU0939F1ZV", "bill_no": "INV-1042", "date": "2026-10-02",
        "items": [{"name": "Amul Taaza 500ml", "qty": 2, "rate": 28.0, "amount": 56.0},
                  {"name": "Britannia Good Day 100g", "qty": 1, "rate": 30.0, "amount": 30.0}],
        "subtotal": 86.0, "cgst": 2.15, "sgst": 2.15, "total": 90.30,
    }
    seen = set()
    assert check(base, seen, today)[0] == "approve"
    assert check(base, seen, today) == ("reject", ["same GSTIN, bill no, date and total already uploaded"])

    misread = {**base, "bill_no": "INV-1043", "gstin": "27AAPFU0939FIZV"}  # 1 read as I
    v, why = check(misread, seen, today)
    assert v == "review" and "27AAPFU0939F1ZV" in why[0], why

    edited = {**base, "bill_no": "INV-1044", "total": 990.30}  # someone added a 9
    assert check(edited, seen, today)[0] == "reject"

    fake = {**base, "bill_no": "INV-1045", "gstin": "27AAPFU0939F1ZQ"}
    assert check(fake, seen, today)[0] == "reject"

    future = {**base, "bill_no": "INV-1046", "date": "2026-11-02"}
    assert check(future, seen, today)[0] == "reject"

    mrp = {**base, "bill_no": "INV-1047", "total": 86.0}  # GST printed inside MRP
    assert check(mrp, seen, today)[0] == "approve"

    discounted = {**base, "bill_no": "INV-1048", "discount": 6.0, "total": 84.30}
    assert check(discounted, seen, today)[0] == "approve"
    print("all checks pass")


if __name__ == "__main__":
    demo()
