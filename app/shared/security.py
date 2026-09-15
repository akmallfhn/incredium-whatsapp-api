import hashlib
import hmac
from typing import Any

import bcrypt
import jwt

JWT_ALGORITHM = "HS256"


def verify_meta_signature(raw_body: bytes, signature_header: str, app_secret: str) -> bool:
    """Cocokkan header `X-Hub-Signature-256` dengan HMAC body pakai Meta app secret."""
    if not signature_header.startswith("sha256="):
        return False
    expected = hmac.new(app_secret.encode(), raw_body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, signature_header.removeprefix("sha256="))


def verify_meta_token(provided: str, expected: str) -> bool:
    """Cocokkan hub.verify_token dalam waktu konstan, bukan `==` yang bocor lewat timing."""
    if not provided or not expected:
        return False
    return hmac.compare_digest(provided, expected)


def hash_password(password: str) -> str:
    """bcrypt memotong di 72 byte, jadi input dipangkas eksplisit daripada diam-diam beda."""
    return bcrypt.hashpw(password.encode()[:72], bcrypt.gensalt()).decode()


def verify_password(password: str, password_hash: str) -> bool:
    if not password or not password_hash:
        return False
    try:
        return bcrypt.checkpw(password.encode()[:72], password_hash.encode())
    except ValueError:
        return False


def encode_jwt(payload: dict[str, Any], secret: str) -> str:
    return jwt.encode(payload, secret, algorithm=JWT_ALGORITHM)


def decode_jwt(token: str, secret: str) -> dict[str, Any] | None:
    """None untuk tanda tangan salah maupun kedaluwarsa; pemanggil tidak perlu bedakan."""
    try:
        return jwt.decode(token, secret, algorithms=[JWT_ALGORITHM])
    except jwt.PyJWTError:
        return None
