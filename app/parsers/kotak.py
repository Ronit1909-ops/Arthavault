"""
app/parsers/kotak.py – Kotak Mahindra Bank statement parser.

Kotak layouts:
  7-col: TxnDate | ValueDate | Description | Ref | Debit | Credit | Balance
  6-col: Date | Description | Ref | Debit | Credit | Balance

Column map PERSISTS across pages.
"""
from typing import Optional
import re

from app.models.transaction import BankName, TransactionCreate, TransactionType
from app.parsers.base import (
    BankParser, parse_amount, parse_date, pick_debit_credit, _DATE_CELL_RE,
)

_SKIP_RE = re.compile(
    r"\b(opening\s+bal|closing\s+bal|balance\s+b/?f|total|brought\s+forward|carry\s+forward)\b",
    re.IGNORECASE,
)
_DR_RE = re.compile(r"UPI/DR|/DR/|\bDR\b|NEFT.{0,5}DR|IMPS.{0,5}DR", re.I)
_CR_RE = re.compile(r"UPI/CR|/CR/|\bCR\b|NEFT.{0,5}CR|IMPS.{0,5}CR", re.I)

_DEBIT_SUBS  = ("withdrawal", "debit", " dr", "(dr)", "dr)")
_CREDIT_SUBS = ("deposit", "credit", " cr", "(cr)", "cr)")
_BAL_SUBS    = ("balance",)
_DESC_SUBS   = ("description", "narration", "particulars", "remarks")
_DATE_SUBS   = ("txn date", "tran date", "transaction date", "posting date")
_REF_SUBS    = ("ref no", "chq no", "cheque", "reference")


def _matches(cell: str, subs: tuple) -> bool:
    return any(s in cell for s in subs)


def _desc_type(desc: str) -> Optional[str]:
    if _DR_RE.search(desc):
        return "debit"
    if _CR_RE.search(desc):
        return "credit"
    return None


class KotakParser(BankParser):
    BANK_NAME = BankName.kotak

    def __init__(self):
        self._debit_col:  Optional[int] = None
        self._credit_col: Optional[int] = None
        self._date_col:   Optional[int] = None
        self._desc_col:   Optional[int] = None
        self._ref_col:    Optional[int] = None
        self._bal_col:    Optional[int] = None

    def _extract_data_rows(self, table: list[list]) -> list[list]:
        for row in table:
            if not row or all(c is None for c in row):
                continue
            cells = [str(c or "").strip().lower() for c in row]
            has_debit  = any(_matches(c, _DEBIT_SUBS)  for c in cells)
            has_credit = any(_matches(c, _CREDIT_SUBS) for c in cells)
            if has_debit and has_credit:
                self._debit_col = self._credit_col = self._date_col = None
                self._desc_col  = self._ref_col    = self._bal_col  = None
                for i, cell in enumerate(cells):
                    if _matches(cell, _DEBIT_SUBS)  and self._debit_col  is None: self._debit_col = i
                    elif _matches(cell, _CREDIT_SUBS) and self._credit_col is None: self._credit_col = i
                    elif _matches(cell, _BAL_SUBS)   and self._bal_col    is None: self._bal_col = i
                    elif _matches(cell, _DESC_SUBS)  and self._desc_col   is None: self._desc_col = i
                    elif _matches(cell, _REF_SUBS)   and self._ref_col    is None: self._ref_col = i
                for i, cell in enumerate(cells):
                    if any(s in cell for s in _DATE_SUBS):
                        self._date_col = i; break
                if self._date_col is None:
                    for i, cell in enumerate(cells):
                        if "date" in cell: self._date_col = i; break
                break
        return super()._extract_data_rows(table)

    def _parse_row(self, row: list[str]) -> Optional[TransactionCreate]:
        n = len(row)
        if n < 4:
            return None

        if self._debit_col is not None and self._credit_col is not None:
            date_idx    = self._date_col   if self._date_col   is not None else 0
            desc_idx    = self._desc_col   if self._desc_col   is not None else (2 if n >= 7 else 1)
            ref_idx     = self._ref_col    if self._ref_col    is not None else (3 if n >= 7 else 2)
            bal_idx     = self._bal_col    if self._bal_col    is not None else (n - 1)
            date_str    = self._safe_cell(row, date_idx)
            desc        = self._safe_cell(row, desc_idx)
            ref_no      = self._safe_cell(row, ref_idx)
            debit_raw   = self._safe_cell(row, self._debit_col)
            credit_raw  = self._safe_cell(row, self._credit_col)
            balance_raw = self._safe_cell(row, bal_idx)
        elif n >= 7:
            date_str = self._safe_cell(row, 0)
            desc     = self._safe_cell(row, 2)
            ref_no   = self._safe_cell(row, 3)
            if _DATE_CELL_RE.match(desc): desc = self._safe_cell(row, 1)
            col4 = self._safe_cell(row, 4); col5 = self._safe_cell(row, 5)
            balance_raw = self._safe_cell(row, 6)
            debit_raw, credit_raw = _resolve(desc, col4, col5)
        elif n == 6:
            date_str = self._safe_cell(row, 0); desc = self._safe_cell(row, 1)
            ref_no = self._safe_cell(row, 2)
            col4 = self._safe_cell(row, 3); col5 = self._safe_cell(row, 4)
            balance_raw = self._safe_cell(row, 5)
            debit_raw, credit_raw = _resolve(desc, col4, col5)
        else:
            return None

        date = parse_date(date_str)
        if date is None:
            return None
        if not desc or _SKIP_RE.search(desc):
            return None

        balance = parse_amount(balance_raw)
        upi_ref = ref_no if ref_no and re.match(r"^\d{6,}$", ref_no.strip()) else None
        debit   = parse_amount(debit_raw)
        credit  = parse_amount(credit_raw)

        if not debit and not credit:
            return None
        if debit and debit > 0:
            return TransactionCreate(date=date, description=desc, amount=debit,
                                     type=TransactionType.debit, upi_ref=upi_ref,
                                     balance=balance, bank=self.BANK_NAME)
        elif credit and credit > 0:
            return TransactionCreate(date=date, description=desc, amount=credit,
                                     type=TransactionType.credit, upi_ref=upi_ref,
                                     balance=balance, bank=self.BANK_NAME)
        return None


def _resolve(desc, col_a, col_b):
    t = _desc_type(desc)
    a = parse_amount(col_a); b = parse_amount(col_b)
    if t == "debit":   return (col_a if a else col_b), ""
    if t == "credit":  return "", (col_b if b else col_a)
    return pick_debit_credit(col_a, col_b)
