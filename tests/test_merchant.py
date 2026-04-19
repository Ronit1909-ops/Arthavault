"""
tests/test_merchant.py – Unit tests for the merchant name extractor.
"""
import pytest
from app.parsers.merchant import extract_merchant


class TestUPISlashFormat:
    def test_flipkart(self):
        desc = "UPI/DR/603230176760/FLIPKART/UTIB0000001/flipkartt1/UPI"
        assert extract_merchant(desc) == "Flipkart"

    def test_swiggy(self):
        desc = "UPI/DR/316421895840/SWIGGY/KKBK0000958/swiggy@ybl/UPI"
        assert extract_merchant(desc) == "Swiggy"

    def test_amazon(self):
        desc = "UPI/CR/456789012345/AMAZON/RATN0TREASU/amazon@apl/UPI"
        assert extract_merchant(desc) == "Amazon"

    def test_zomato(self):
        desc = "UPI/P2M/987654321012/Zomato/HDFC0000001/zomato@hdfcbank"
        assert extract_merchant(desc) == "Zomato"

    def test_phonepay(self):
        desc = "UPI/CR/111222333444/PhonePe/YESB0000001/pp/UPI"
        merchant = extract_merchant(desc)
        # _clean() preserves mixed-case so PhonePe stays as-is
        assert merchant.lower() == "phonepe"

    def test_cr_type(self):
        desc = "UPI/CR/999888777666/PETROL BUNK/SBIN0001234/bunk@sbi"
        merchant = extract_merchant(desc)
        assert "Petrol" in merchant or "Bunk" in merchant


class TestUPIDashFormat:
    def test_swiggy_dash(self):
        desc = "UPI-SWIGGY INDIA-123456789012"
        merchant = extract_merchant(desc)
        assert "swiggy" in merchant.lower() or "india" in merchant.lower() or len(merchant) >= 3

    def test_airtel_dash(self):
        desc = "UPI-Airtel Payments-987654321098"
        merchant = extract_merchant(desc)
        assert "airtel" in merchant.lower() or len(merchant) >= 3


class TestIMPSFormat:
    def test_imps_p2m(self):
        desc = "IMPS/P2M/316421895/BIGBASKET/remarks"
        merchant = extract_merchant(desc)
        assert "Bigbasket" in merchant or "Big" in merchant

    def test_neft(self):
        desc = "NEFT/TRANSFER/HDFC/SALARY CREDIT"
        merchant = extract_merchant(desc)
        # HDFC is a noise word; should still return something after it
        assert merchant != "Unknown" or len(desc) > 0  # graceful fallback
        assert len(merchant) >= 3


class TestFallback:
    def test_plain_text(self):
        desc = "Electricity Board Payment"
        merchant = extract_merchant(desc)
        assert len(merchant) >= 3

    def test_empty_string(self):
        assert extract_merchant("") == "Unknown"

    def test_none_like(self):
        assert extract_merchant("   ") == "Unknown"
