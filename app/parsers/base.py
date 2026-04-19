"""
app/parsers/base.py – Abstract base class for all bank PDF parsers.

Simple, reliable design:
  1. Open PDF with pdfplumber
  2. For each page: extract tables (default strategy first, text fallback)
  3. For each table row: call subclass _parse_row()
  4. Collect results, enrich with merchant + UPI ref
"""
from __future__ import annotations

import io
import logging
import re
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Optional

import pdfplumber

from app.models.transaction import BankName, TransactionCreate, TransactionType
from app.parsers.merchant import extract_merchant

logger = logging.getLogger(__name__)

_UPI_REF_RE = re.compile(r"\b(\d{10,25})\b")

# Every Indian date format including timestamp variants
_DATE_FORMATS = [
    "%d/%m/%Y %H:%M:%S", "%d-%m-%Y %H:%M:%S",
    "%d/%m/%Y %H:%M",    "%d-%m-%Y %H:%M",
    "%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S",
    "%d/%m/%Y", "%d-%m-%Y", "%d/%m/%y", "%d-%m-%y",
    "%d %b %Y", "%d %b %y",
    "%d-%b-%Y", "%d-%b-%y",
    "%Y-%m-%d",
]

# First-cell values that 100% indicate a header row
_HEADER_FIRST_CELLS = {
    "date", "txn date", "tran date", "value date", "transaction date",
    "posting date", "sl no", "sr no", "s no", "s.no", "sl.no", "sr.no",
    "#", "sno", "serial", "serial no", "transaction",
}

# Rows where every cell is a known header word → skip
_HEADER_WORDS = {
    "date", "description", "narration", "particulars", "debit",
    "credit", "balance", "withdrawal", "deposit", "ref no", "chq no",
    "cheque no", "amount", "dr", "cr", "remarks", "reference",
    "value date", "txn date", "tran date", "transaction date",
}

_SUMMARY_WORDS_RE = re.compile(
    r"^(opening|closing|brought\s+forward|carry\s+forward|grand\s+total|"
    r"sub\s*total|page\s+total|total\s+amount)",
    re.IGNORECASE,
)


def parse_date(raw: str) -> Optional[datetime]:
    if not raw:
        return None
    raw = raw.strip()
    for fmt in _DATE_FORMATS:
        try:
            return datetime.strptime(raw, fmt)
        except ValueError:
            pass
    # strip time component and retry
    parts = raw.split()
    if len(parts) > 1:
        for fmt in _DATE_FORMATS:
            try:
                return datetime.strptime(parts[0], fmt)
            except ValueError:
                pass
    return None


def parse_amount(raw: str) -> Optional[float]:
    if not raw or not raw.strip():
        return None
    cleaned = re.sub(r"[₹,\s]", "", raw.strip())
    if cleaned.startswith("(") and cleaned.endswith(")"):
        cleaned = "-" + cleaned[1:-1]
    try:
        v = float(cleaned)
        return v if abs(v) > 0 else None
    except ValueError:
        return None


def extract_upi_ref(description: str) -> Optional[str]:
    m = _UPI_REF_RE.search(description)
    return m.group(1) if m else None


# Shared helpers
_DATE_CELL_RE = re.compile(r"^\d{2}[/\-]\d{2}[/\-]\d{2,4}")


def pick_debit_credit(col_a: str, col_b: str):
    a = parse_amount(col_a)
    b = parse_amount(col_b)
    if a and not b:
        return col_a, ""
    if b and not a:
        return "", col_b
    return col_a, col_b


class BankParser(ABC):
    BANK_NAME: BankName = BankName.unknown

    def parse(self, file_bytes: bytes) -> list[TransactionCreate]:
        transactions: list[TransactionCreate] = []
        try:
            with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
                logger.info("Parsing %d-page PDF [%s]", len(pdf.pages), self.BANK_NAME)
                for page_num, page in enumerate(pdf.pages, 1):
                    page_txns = self._parse_page(page, page_num)
                    logger.debug("Page %d → %d transactions", page_num, len(page_txns))
                    transactions.extend(page_txns)
        except Exception as exc:
            raise ValueError(f"Failed to read PDF: {exc}") from exc

        logger.info("Total parsed: %d [%s]", len(transactions), self.BANK_NAME)
        return transactions

    def _parse_page(self, page, page_num: int) -> list[TransactionCreate]:
        # Step 1: try default line-based table extraction
        tables = page.extract_tables() or []

        # Step 2: if nothing found, try text-aligned strategy
        if not tables:
            try:
                tables = page.extract_tables({
                    "vertical_strategy": "text",
                    "horizontal_strategy": "text",
                }) or []
                logger.debug("Page %d: used text strategy, got %d tables", page_num, len(tables))
            except Exception as e:
                logger.debug("Page %d: text strategy failed: %s", page_num, e)
                tables = []

        transactions = []
        if tables:
            for table in tables:
                if not table:
                    continue
                rows = self._extract_data_rows(table)
                logger.debug(
                    "Page %d table: %d raw rows → %d data rows",
                    page_num, len(table), len(rows),
                )
                for row in rows:
                    txn = self._safe_parse(row, page_num)
                    if txn:
                        transactions.append(txn)
        else:
            # Step 3: text line fallback (last resort)
            text = page.extract_text() or ""
            if text:
                fake_rows = self._text_to_rows(text)
                logger.debug("Page %d: text fallback → %d lines", page_num, len(fake_rows))
                for row in fake_rows:
                    txn = self._safe_parse(row, page_num)
                    if txn:
                        transactions.append(txn)

        return transactions

    def _safe_parse(self, row: list[str], page_num: int) -> Optional[TransactionCreate]:
        try:
            txn = self._parse_row(row)
            if txn is not None:
                txn.bank = self.BANK_NAME
                if not txn.merchant or txn.merchant == "Unknown":
                    txn.merchant = extract_merchant(txn.description)
                if txn.upi_ref is None:
                    txn.upi_ref = extract_upi_ref(txn.description)
            return txn
        except Exception as exc:
            logger.debug("Row skip p%d: %s | %s", page_num, exc, row[:3])
            return None

    def _extract_data_rows(self, table: list[list]) -> list[list]:
        data_rows = []
        for row in table:
            # Skip empty rows
            if not row or all(c is None or str(c).strip() == "" for c in row):
                continue
            cells = [str(c or "").strip() for c in row]
            first = cells[0].strip().lower()

            # Skip definite header rows
            if first in _HEADER_FIRST_CELLS:
                continue
            if re.match(r"^s\.?\s*no\.?$", first, re.I):
                continue

            # Skip rows where ALL cells are header words (pure header rows)
            non_empty = [c.strip().lower() for c in cells if c.strip()]
            if non_empty and all(w in _HEADER_WORDS for w in non_empty):
                continue

            # Skip opening/closing balance rows
            if non_empty and _SUMMARY_WORDS_RE.match(non_empty[0]):
                continue

            data_rows.append(cells)
        return data_rows

    def _text_to_rows(self, text: str) -> list[list[str]]:
        """Convert raw text into pseudo-rows when no tables detected."""
        date_re = re.compile(
            r"^(\d{2}[/\-]\d{2}[/\-]\d{2,4}(?:\s+\d{2}:\d{2}(?::\d{2})?)?)"
            r"\s+(.*)"
        )
        rows = []
        current: list[str] = []
        for line in text.split("\n"):
            line = line.strip()
            if not line:
                continue
            m = date_re.match(line)
            if m:
                if current:
                    rows.append(current)
                current = [m.group(1), m.group(2)]
            elif current:
                current[1] += " " + line
        if current:
            rows.append(current)
        return rows

    def _safe_cell(self, row: list[str], index: int, default: str = "") -> str:
        try:
            return row[index].strip()
        except IndexError:
            return default

    @abstractmethod
    def _parse_row(self, row: list[str]) -> Optional[TransactionCreate]:
        ...
