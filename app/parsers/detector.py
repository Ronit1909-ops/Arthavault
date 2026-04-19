"""
app/parsers/detector.py – Auto-detect Indian bank from PDF text.
"""
import re

# Each tuple: (compiled pattern, bank_id)
_BANK_SIGNATURES: list[tuple[re.Pattern, str]] = [
    (re.compile(r"State\s+Bank\s+of\s+India|SBI\s+(?:Bank|Statement|Passbook)", re.I), "sbi"),
    (re.compile(r"HDFC\s+Bank", re.I), "hdfc"),
    (re.compile(r"ICICI\s+Bank", re.I), "icici"),
    (re.compile(r"Bank\s+of\s+Baroda|BOB\s+(?:Bank|Statement)", re.I), "bob"),
    (re.compile(r"IDBI\s+Bank|Industrial\s+Development\s+Bank", re.I), "idbi"),
    (re.compile(r"Kotak\s+Mahindra\s+Bank|KOTAK\s+BANK", re.I), "kotak"),
    (re.compile(r"Central\s+Bank\s+of\s+India|CentBank", re.I), "cbi"),
    (re.compile(r"Axis\s+Bank|AXIS\s+BANK", re.I), "axis"),
    (re.compile(r"Punjab\s+National\s+Bank|PNB\s+Bank", re.I), "pnb"),
    (re.compile(r"Canara\s+Bank", re.I), "canara"),
    (re.compile(r"Union\s+Bank\s+of\s+India", re.I), "union"),
    (re.compile(r"IndusInd\s+Bank", re.I), "indusind"),
]


def detect_bank(pdf_text: str) -> str:
    """
    Scan the first ~3000 characters of a PDF text for bank-specific keywords.

    Returns one of: "sbi", "hdfc", "icici", "bob", "idbi", "kotak", "cbi",
                    "axis", "pnb", "canara", "union", "indusind", "unknown"
    """
    probe = pdf_text[:3000]
    for pattern, bank_id in _BANK_SIGNATURES:
        if pattern.search(probe):
            return bank_id
    return "unknown"
