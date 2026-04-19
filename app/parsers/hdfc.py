"""
app/parsers/hdfc.py – HDFC Bank statement parser.

Column order (HDFC e-statement / PDF):
  0: Date          (DD/MM/YY)
  1: Narration
  2: Chq./Ref.No.
  3: Value Dt       (settlement date – we ignore)
  4: Withdrawal Amt (Debit)
  5: Deposit Amt    (Credit)
  6: Closing Balance
"""
from typing import Optional

from app.models.transaction import BankName, TransactionCreate, TransactionType
from app.parsers.base import BankParser, parse_amount, parse_date


class HDFCParser(BankParser):
    BANK_NAME = BankName.hdfc

    def _parse_row(self, row: list[str]) -> Optional[TransactionCreate]:
        if len(row) < 5:
            return None

        date_str  = self._safe_cell(row, 0)
        narration = self._safe_cell(row, 1)
        ref_no    = self._safe_cell(row, 2)
        # col 3 = Value Dt (skip)
        withdrawal_raw = self._safe_cell(row, 4)
        deposit_raw    = self._safe_cell(row, 5) if len(row) > 5 else ""
        balance_raw    = self._safe_cell(row, 6) if len(row) > 6 else ""

        date = parse_date(date_str)
        if date is None:
            return None

        withdrawal = parse_amount(withdrawal_raw)
        deposit    = parse_amount(deposit_raw)
        balance    = parse_amount(balance_raw)

        if withdrawal and withdrawal > 0:
            txn_type = TransactionType.debit
            amount   = withdrawal
        elif deposit and deposit > 0:
            txn_type = TransactionType.credit
            amount   = deposit
        else:
            return None

        return TransactionCreate(
            date=date,
            description=narration,
            amount=amount,
            type=txn_type,
            upi_ref=ref_no if ref_no else None,
            balance=balance,
            bank=self.BANK_NAME,
        )
