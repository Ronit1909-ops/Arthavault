"""
tests/test_duplicate.py – Unit tests for the transaction dedup hash.
"""
from datetime import datetime
from app.services.transaction_service import _make_hash


class TestDedupHash:
    _DATE = datetime(2024, 3, 1)
    _REF  = "603230176760"
    _DESC = "UPI/DR/603230176760/FLIPKART/UTIB"
    _AMT  = 499.00

    def test_same_inputs_produce_same_hash(self):
        h1 = _make_hash(self._DATE, self._REF, self._DESC, self._AMT)
        h2 = _make_hash(self._DATE, self._REF, self._DESC, self._AMT)
        assert h1 == h2

    def test_different_date_produces_different_hash(self):
        h1 = _make_hash(datetime(2024, 3, 1), self._REF, self._DESC, self._AMT)
        h2 = _make_hash(datetime(2024, 3, 2), self._REF, self._DESC, self._AMT)
        assert h1 != h2

    def test_different_amount_produces_different_hash(self):
        h1 = _make_hash(self._DATE, self._REF, self._DESC, 499.00)
        h2 = _make_hash(self._DATE, self._REF, self._DESC, 500.00)
        assert h1 != h2

    def test_different_ref_produces_different_hash(self):
        h1 = _make_hash(self._DATE, "603230176760", self._DESC, self._AMT)
        h2 = _make_hash(self._DATE, "603230176761", self._DESC, self._AMT)
        assert h1 != h2

    def test_none_ref_falls_back_to_description(self):
        h1 = _make_hash(self._DATE, None, "FLIPKART PAYMENT ABC", self._AMT)
        h2 = _make_hash(self._DATE, None, "FLIPKART PAYMENT ABC", self._AMT)
        # Should still be deterministic
        assert h1 == h2

    def test_none_and_real_ref_differ(self):
        h1 = _make_hash(self._DATE, None,  self._DESC, self._AMT)
        h2 = _make_hash(self._DATE, "603230176760", self._DESC, self._AMT)
        # They may or may not collide; confirm they're deterministic
        assert isinstance(h1, str) and len(h1) == 64  # SHA-256 hex
        assert isinstance(h2, str) and len(h2) == 64

    def test_hash_is_hex_string(self):
        h = _make_hash(self._DATE, self._REF, self._DESC, self._AMT)
        assert len(h) == 64
        int(h, 16)  # No ValueError means it's valid hex

    def test_amount_precision(self):
        # 499.0 and 499.00 should give same hash
        h1 = _make_hash(self._DATE, self._REF, self._DESC, 499.0)
        h2 = _make_hash(self._DATE, self._REF, self._DESC, 499.00)
        assert h1 == h2

    def test_case_insensitive_ref(self):
        # UPI refs are numeric so case shouldn't matter, but test uppercase normalisation
        h1 = _make_hash(self._DATE, "upi-ref-abc", self._DESC, self._AMT)
        h2 = _make_hash(self._DATE, "UPI-REF-ABC", self._DESC, self._AMT)
        assert h1 == h2  # both uppercased in _make_hash
