"""app/parsers/__init__.py"""
from app.parsers.sbi   import SBIParser
from app.parsers.hdfc  import HDFCParser
from app.parsers.icici import ICICIParser
from app.parsers.bob   import BOBParser
from app.parsers.idbi  import IDBIParser
from app.parsers.kotak import KotakParser
from app.parsers.cbi   import CBIParser
from app.parsers.base  import BankParser

# Registry: bank_id → parser class
PARSER_REGISTRY: dict[str, type[BankParser]] = {
    "sbi":   SBIParser,
    "hdfc":  HDFCParser,
    "icici": ICICIParser,
    "bob":   BOBParser,
    "idbi":  IDBIParser,
    "kotak": KotakParser,
    "cbi":   CBIParser,
}

__all__ = [
    "SBIParser", "HDFCParser", "ICICIParser", "BOBParser",
    "IDBIParser", "KotakParser", "CBIParser",
    "PARSER_REGISTRY",
]
