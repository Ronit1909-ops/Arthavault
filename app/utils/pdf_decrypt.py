"""
app/utils/pdf_decrypt.py – Decrypt a password-protected PDF in memory.

Indian bank PDFs use various password conventions:
  SBI   → date of birth in DDMMYYYY (e.g. 01011990)
  HDFC  → date of birth in DDMMYYYY
  ICICI → date of birth in DDMMYYYY
  BOB   → date of birth in DDMMYYYY
  Axis  → PAN number (uppercase) or DOB in DDMMYYYY

Usage:
    decrypted_bytes = decrypt_pdf(raw_bytes, password="01011990")
    # Then pass decrypted_bytes to pdfplumber as normal

If the PDF is not encrypted, the original bytes are returned unchanged.
If the password is wrong, raises ValueError with a clear message.
"""
import io
import logging

import pikepdf

logger = logging.getLogger(__name__)


def is_encrypted(pdf_bytes: bytes) -> bool:
    """Return True if the PDF requires a password to open."""
    try:
        with pikepdf.open(io.BytesIO(pdf_bytes)):
            return False
    except pikepdf.PasswordError:
        return True
    except Exception:
        return False


def decrypt_pdf(pdf_bytes: bytes, password: str) -> bytes:
    """
    Open the encrypted PDF with the given password and return
    a decrypted, unlocked copy as bytes.

    Args:
        pdf_bytes: Raw PDF file content.
        password:  User password (e.g. "01011990" for DOB DDMMYYYY).

    Returns:
        Unencrypted PDF as bytes — safe to pass to pdfplumber.

    Raises:
        ValueError: If the password is incorrect or PDF is corrupt.
    """
    try:
        with pikepdf.open(io.BytesIO(pdf_bytes), password=password) as pdf:
            output = io.BytesIO()
            # Save without encryption
            pdf.save(output)
            decrypted = output.getvalue()
            logger.info("PDF decrypted successfully (%d → %d bytes)",
                        len(pdf_bytes), len(decrypted))
            return decrypted
    except pikepdf.PasswordError:
        raise ValueError(
            "Incorrect PDF password. "
            "For most Indian banks, the password is your date of birth in DDMMYYYY format "
            "(e.g. '01011990' for 1 Jan 1990). "
            "Some banks use PAN number or last 4 digits of account number."
        )
    except Exception as exc:
        raise ValueError(f"Could not read PDF: {exc}") from exc


def decrypt_if_needed(pdf_bytes: bytes, password: str | None) -> bytes:
    """
    Convenience wrapper:
    - If PDF is not encrypted → return as-is.
    - If encrypted and password provided → decrypt.
    - If encrypted but no password → raise ValueError with helpful message.
    """
    if not is_encrypted(pdf_bytes):
        return pdf_bytes

    if not password:
        raise ValueError(
            "This PDF is password-protected. "
            "Please provide the password via the 'password' field. "
            "For most Indian banks: date of birth in DDMMYYYY format (e.g. '01011990')."
        )

    return decrypt_pdf(pdf_bytes, password)
