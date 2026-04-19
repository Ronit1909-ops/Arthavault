"""
app/parsers/icici.py – ICICI Bank statement parser.

Column order (ICICI e-statement):
  0: S No.
  1: Value Date      (DD-MM-YYYY)
  2: Transaction Date
  3: Ref Number
  4: Transaction Remarks / Description
  5: Debit
  6: Credit
  7: Balance
"""
from typing import Optional

from app.models.transaction import BankName, TransactionCreate, TransactionType
from app.parsers.base import BankParser, parse_amount, parse_date


class ICICIParser(BankParser):
    BANK_NAME = BankName.icici

    def _parse_row(self, row: list[str]) -> Optional[TransactionCreate]:
        if len(row) < 6:
            return None

        # Skip the serial number column
        value_date_str = self._safe_cell(row, 1)
        txn_date_str   = self._safe_cell(row, 2)
        ref_no         = self._safe_cell(row, 3)
        description    = self._safe_cell(row, 4)
        debit_raw      = self._safe_cell(row, 5)
        credit_raw     = self._safe_cell(row, 6) if len(row) > 6 else ""
        balance_raw    = self._safe_cell(row, 7) if len(row) > 7 else ""

        # Prefer value date; fall back to transaction date
        date = parse_date(value_date_str) or parse_date(txn_date_str)
        if date is None:
            return None

        debit   = parse_amount(debit_raw)
        credit  = parse_amount(credit_raw)
        balance = parse_amount(balance_raw)

        if debit and debit > 0:
            txn_type = TransactionType.debit
            amount   = debit
        elif credit and credit > 0:
            txn_type = TransactionType.credit
            amount   = credit
        else:
            return None

        return TransactionCreate(
            date=date,
            description=description,
            amount=amount,
            type=txn_type,
            upi_ref=ref_no if ref_no else None,
            balance=balance,
            bank=self.BANK_NAME,
        )
