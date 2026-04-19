"""
tests/test_parsers.py – Unit tests for each bank-specific parser.

These tests use in-memory raw table rows (not real PDFs) to test
the _parse_row() logic directly — no file I/O needed.
"""
import pytest
from datetime import datetime
from app.models.transaction import TransactionType, BankName
from app.parsers.sbi   import SBIParser
from app.parsers.hdfc  import HDFCParser
from app.parsers.icici import ICICIParser
from app.parsers.bob   import BOBParser
from app.parsers.detector import detect_bank


# ── SBI ───────────────────────────────────────────────────────────────────────
class TestSBIParser:
    parser = SBIParser()

    def test_debit_row(self):
        row = ["01/03/2024", "UPI/DR/603230176760/FLIPKART/UTIB/fl/UPI",
               "603230176760", "", "499.00", "12501.00"]
        txn = self.parser._parse_row(row)
        assert txn is not None
        assert txn.type == TransactionType.debit
        assert txn.amount == 499.00
        assert txn.balance == 12501.00

    def test_credit_row(self):
        row = ["15/03/2024", "UPI/CR/111222333/SALARY/SBIN/sal@sbi/UPI",
               "111222333", "50000.00", "", "62501.00"]
        txn = self.parser._parse_row(row)
        assert txn is not None
        assert txn.type == TransactionType.credit
        assert txn.amount == 50000.00

    def test_invalid_date_skipped(self):
        row = ["Date", "Transaction Description", "Ref", "Credit", "Debit", "Balance"]
        txn = self.parser._parse_row(row)
        assert txn is None

    def test_empty_amounts_skipped(self):
        row = ["01/03/2024", "Some description", "REF123", "", "", "10000.00"]
        txn = self.parser._parse_row(row)
        assert txn is None  # no credit or debit value

    def test_five_column_layout(self):
        row = ["05/03/2024", "UPI/DR/123456789/ZOMATO/HDFC", "123456789",
               "350.00", "15000.00"]
        txn = self.parser._parse_row(row)
        assert txn is not None
        assert txn.amount in (350.00, 15000.00)  # credit parsed as amount

    def test_date_dd_mm_yy(self):
        row = ["01-03-24", "UPI/DR/999/AMAZON/RATN", "999", "", "1200.00", "8000.00"]
        txn = self.parser._parse_row(row)
        assert txn is not None
        assert txn.amount == 1200.00

    def test_bank_name_set(self):
        row = ["01/03/2024", "UPI/DR/603/SHOP/UTIB", "603", "", "200.00", "5000.00"]
        txn = self.parser._parse_row(row)
        assert txn is not None
        assert txn.bank == BankName.sbi


# ── HDFC ──────────────────────────────────────────────────────────────────────
class TestHDFCParser:
    parser = HDFCParser()

    def test_withdrawal(self):
        row = ["01/03/24", "UPI-SWIGGY-316421895840", "316421895840",
               "01/03/24", "350.00", "", "24650.00"]
        txn = self.parser._parse_row(row)
        assert txn is not None
        assert txn.type == TransactionType.debit
        assert txn.amount == 350.00

    def test_deposit(self):
        row = ["05/03/24", "NEFT-SALARY-CORP", "REF001",
               "05/03/24", "", "80000.00", "104650.00"]
        txn = self.parser._parse_row(row)
        assert txn is not None
        assert txn.type == TransactionType.credit
        assert txn.amount == 80000.00

    def test_balance_parsed(self):
        row = ["10/03/24", "UPI/DR/111/PAYTM/PYTM", "111",
               "10/03/24", "100.00", "", "104550.00"]
        txn = self.parser._parse_row(row)
        assert txn is not None
        assert txn.balance == 104550.00

    def test_too_few_columns(self):
        row = ["01/03/24", "somethhing"]
        txn = self.parser._parse_row(row)
        assert txn is None

    def test_bank_name_hdfc(self):
        row = ["01/03/24", "UPI/DR/111/SHOP/HDFC", "111",
               "01/03/24", "500.00", "", "10000.00"]
        txn = self.parser._parse_row(row)
        assert txn is not None
        assert txn.bank == BankName.hdfc


# ── ICICI ─────────────────────────────────────────────────────────────────────
class TestICICIParser:
    parser = ICICIParser()

    def test_debit_8col(self):
        row = ["1", "01-03-2024", "01-03-2024", "ICICI123REF",
               "UPI/DR/603/AMAZON/RATN/amzn@icici", "999.00", "", "25001.00"]
        txn = self.parser._parse_row(row)
        assert txn is not None
        assert txn.type == TransactionType.debit
        assert txn.amount == 999.00

    def test_credit_8col(self):
        row = ["2", "15-03-2024", "15-03-2024", "ICICIREF2",
               "UPI/CR/777/EMPLOYER/ICIC/emp@icici", "", "60000.00", "85001.00"]
        txn = self.parser._parse_row(row)
        assert txn is not None
        assert txn.type == TransactionType.credit
        assert txn.amount == 60000.00

    def test_fallback_to_txn_date(self):
        # value date empty, txn date used
        row = ["1", "", "01-03-2024", "REF",
               "UPI/DR/1/ZOMATO/ICIC", "200.00", "", "5000.00"]
        txn = self.parser._parse_row(row)
        assert txn is not None
        assert txn.date.day == 1

    def test_bank_name_icici(self):
        row = ["1", "01-03-2024", "01-03-2024", "REF",
               "UPI/DR/1/SHOP/ICIC", "100.00", "", "5000.00"]
        txn = self.parser._parse_row(row)
        assert txn is not None
        assert txn.bank == BankName.icici


# ── Bank of Baroda ────────────────────────────────────────────────────────────
class TestBOBParser:
    parser = BOBParser()

    def test_debit(self):
        row = ["01-03-2024", "UPI/DR/123456/FLIPKART/BARB", "123456",
               "799.00", "", "19201.00"]
        txn = self.parser._parse_row(row)
        assert txn is not None
        assert txn.type == TransactionType.debit
        assert txn.amount == 799.00

    def test_credit(self):
        row = ["10-03-2024", "NEFT SALARY", "NEFTREF",
               "", "45000.00", "64201.00"]
        txn = self.parser._parse_row(row)
        assert txn is not None
        assert txn.type == TransactionType.credit

    def test_bank_name_bob(self):
        row = ["01-03-2024", "UPI/DR/1/SHOP/BARB", "1",
               "100.00", "", "1000.00"]
        txn = self.parser._parse_row(row)
        assert txn is not None
        assert txn.bank == BankName.bob


# ── Bank Detector ─────────────────────────────────────────────────────────────
class TestBankDetector:
    def test_detect_sbi(self):
        assert detect_bank("Statement of Account\nState Bank of India\n") == "sbi"

    def test_detect_sbi_abbrev(self):
        assert detect_bank("SBI Bank Account Statement") == "sbi"

    def test_detect_hdfc(self):
        assert detect_bank("HDFC Bank Ltd\nAccount Statement") == "hdfc"

    def test_detect_icici(self):
        assert detect_bank("ICICI Bank - Account Statement") == "icici"

    def test_detect_bob(self):
        assert detect_bank("Bank of Baroda\nPassbook / Statement") == "bob"

    def test_unknown_bank(self):
        assert detect_bank("Some random text without bank name") == "unknown"

    def test_empty_text(self):
        assert detect_bank("") == "unknown"
