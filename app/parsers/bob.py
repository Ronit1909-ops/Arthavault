"""
app/parsers/bob.py – Bank of Baroda statement parser.

Column order (BOB e-statement):
  0: Tran Date     (DD-MM-YYYY)
  1: Description / Particulars
  2: Chq Ref Num
  3: Debit
  4: Credit
  5: Balance
"""
from typing import Optional

from app.models.transaction import BankName, TransactionCreate, TransactionType
from app.parsers.base import BankParser, parse_amount, parse_date


class BOBParser(BankParser):
    BANK_NAME = BankName.bob

    def _parse_row(self, row: list[str]) -> Optional[TransactionCreate]:
        if len(row) < 5:
            return None

        date_str    = self._safe_cell(row, 0)
        description = self._safe_cell(row, 1)
        ref_no      = self._safe_cell(row, 2)
        debit_raw   = self._safe_cell(row, 3)
        credit_raw  = self._safe_cell(row, 4)
        balance_raw = self._safe_cell(row, 5) if len(row) > 5 else ""

        date = parse_date(date_str)
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
