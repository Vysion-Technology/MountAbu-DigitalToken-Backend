"""Transport code utility for NAKA checkpoint operations.

Encodes (application_id, phase) into an HMAC-signed opaque string
that only the server can generate or verify. No external dependencies.
"""

import base64
import hmac
import hashlib

from pydantic import BaseModel

from backend.config import settings


class TransportCodeData(BaseModel):
    """Decoded transport code payload."""
    application_id: int
    phase: int


def encode_transport_code(application_id: int, phase: int) -> str:
    """Encode (application_id, phase) into a signed, opaque transport code."""
    payload = f"{application_id}:{phase}"
    signature = hmac.new(
        settings.SECRET_KEY.encode(), payload.encode(), hashlib.sha256
    ).digest()[:8]
    payload_b64 = base64.urlsafe_b64encode(payload.encode()).decode().rstrip("=")
    sig_b64 = base64.urlsafe_b64encode(signature).decode().rstrip("=")
    return f"{payload_b64}.{sig_b64}"


def decode_transport_code(code: str) -> TransportCodeData:
    """Verify and decode a transport code, returning a TransportCodeData object.

    Raises ValueError if the code is malformed or the signature is invalid.
    """
    try:
        payload_b64, sig_b64 = code.split(".", 1)
    except ValueError:
        raise ValueError("Invalid transport code format")

    # Restore base64 padding
    payload = base64.urlsafe_b64decode(payload_b64 + "==").decode()
    actual_sig = base64.urlsafe_b64decode(sig_b64 + "==")

    expected_sig = hmac.new(
        settings.SECRET_KEY.encode(), payload.encode(), hashlib.sha256
    ).digest()[:8]

    if not hmac.compare_digest(expected_sig, actual_sig):
        raise ValueError("Invalid transport code signature")

    try:
        app_id_str, phase_str = payload.split(":", 1)
        return TransportCodeData(application_id=int(app_id_str), phase=int(phase_str))
    except (ValueError, TypeError):
        raise ValueError("Invalid transport code payload")
