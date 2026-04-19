"""
app/parsers/merchant.py – Extract merchant name from UPI transaction descriptions.

Common formats observed across Indian banks:
  UPI/DR/603230176760/FLIPKART/UTIB0000001/fl…      → FLIPKART
  UPI/CR/456789/PhonePe/HDFC0000123/pp…             → PhonePe
  UPI-SWIGGY INDIA-12345678901                       → SWIGGY INDIA
  UPI/123456/ZOMATO/remarks                          → ZOMATO
  IMPS/P2M/123456/AMAZON                             → AMAZON
  NEFT/TRANSFER/HDFC/SALARY                          → SALARY (fallback)
  BIL/BPAY/12345/ELECTRICITY BOARD                   → ELECTRICITY BOARD
"""

import re
from functools import lru_cache

# ── UPI slash format ──────────────────────────────────────────────────────────
# Pattern: UPI/(DR|CR)/<ref>/<MERCHANT>/<bank_code>/<vpa>/...
_UPI_SLASH_RE = re.compile(
    r"UPI[/\-](DR|CR|P2M|P2P)[/\-](\d+)[/\-]([^/\-]+)",
    re.IGNORECASE,
)

# Alternate shorter form: UPI/<ref>/<MERCHANT>
_UPI_SHORT_RE = re.compile(
    r"UPI[/\-](\d{6,})[/\-]([^/\-]{2,40})",
    re.IGNORECASE,
)

# UPI dash separated: UPI-MERCHANT NAME-digits  OR  UPI-MERCHANT NAME-digits
# Also handles: UPI-SWIGGY INDIA-1234567890
_UPI_DASH_RE = re.compile(
    r"UPI[-\s]+([A-Za-z][A-Za-z0-9 &'.]{1,40})[-\s]+\d{6,}",
    re.IGNORECASE,
)

# UPI/NAME/digits or UPI/NAME/ref  (no DR/CR prefix)
# Handles:  UPI/PRIYANSHU NAYA/6421   UPI/DILIP ADHIKARY/60592
_UPI_NAMED_RE = re.compile(
    r"UPI[/\-]([A-Za-z][A-Za-z0-9 &'.]{1,40})[/\-](\d{4,}|\w{4,})",
    re.IGNORECASE,
)

# IMPS/NEFT P2M: skip optional bank code token, capture merchant after it
# e.g. NEFT/TRANSFER/HDFC/SALARY CREDIT  → SALARY CREDIT
_IMPS_RE = re.compile(
    r"(?:IMPS|NEFT|RTGS)[/\-](?:P2M|P2P|FT|TRANSFER)?[/\-]?\d*[/\-](?:[A-Z]{2,6}[0-9]*[/\-])?([A-Za-z][^/\n]{2,40})",
    re.IGNORECASE,
)

# Bill pay: BIL/BPAY/<ref>/<MERCHANT>
_BILL_RE = re.compile(
    r"(?:BIL|BILL|BPAY)[/\-][A-Z0-9]*[/\-]\d*[/\-]([A-Za-z][^/\n]{2,40})",
    re.IGNORECASE,
)

# Noise tokens to strip from extracted merchant
_NOISE = re.compile(
    r"\b(?:UPI|DR|CR|IMPS|NEFT|RTGS|P2M|P2P|FT|REF|NO|UTR|AC|A/C|HDFC|ICICI|SBI|AXIS|UTIB|KKBK|SBIN|PYTM|PAYTM|YESB|PUNB|BARB)\b",
    re.IGNORECASE,
)


def extract_merchant(description: str) -> str:
    """
    Return a clean merchant/payee name from a raw bank transaction description.

    Falls back to the first meaningful token of the description string if no
    known pattern matches.
    """
    if not description:
        return "Unknown"

    desc = description.strip()

    # 1. UPI slash format with DR/CR/P2M/P2P prefix (most common bank format)
    m = _UPI_SLASH_RE.search(desc)
    if m:
        return _clean(m.group(3))

    # 2. UPI dash format: UPI-MERCHANT NAME-123456
    m = _UPI_DASH_RE.search(desc)
    if m:
        return _clean(m.group(1))

    # 3. UPI/NAME/ref  (Kotak and similar: UPI/PRIYANSHU NAYA/6421)
    m = _UPI_NAMED_RE.search(desc)
    if m:
        candidate = _clean(m.group(1))
        # Reject if the "name" segment looks like a pure reference/bank-code
        if candidate and not re.match(r'^\d+$', candidate) and len(candidate) >= 3:
            return candidate

    # 4. UPI short numeric ref: UPI/123456/MERCHANT
    m = _UPI_SHORT_RE.search(desc)
    if m:
        return _clean(m.group(2))

    # 5. IMPS / NEFT P2M
    m = _IMPS_RE.search(desc)
    if m:
        return _clean(m.group(1))

    # 6. Bill payment
    m = _BILL_RE.search(desc)
    if m:
        return _clean(m.group(1))

    # 7. Fallback: first non-noise token with >= 3 chars
    tokens = re.split(r'[/\-_\s]+', desc)
    for tok in tokens:
        cleaned = _clean(tok)
        if len(cleaned) >= 3 and not re.match(r'^\d+$', cleaned):
            return cleaned

    return desc[:40].strip() or 'Unknown'


def _clean(text: str) -> str:
    """Strip noise keywords and extra whitespace."""
    text = _NOISE.sub("", text).strip(" /-.@_")
    text = re.sub(r"\s{2,}", " ", text)
    return text.title() if text.isupper() else text or "Unknown"
