import base64
import hashlib
import hmac
import secrets

import bcrypt
from cryptography.fernet import Fernet, InvalidToken
from flask import current_app


def _bcrypt_rounds() -> int:
    return int(current_app.config.get("BCRYPT_COST", 12))


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt(rounds=_bcrypt_rounds())).decode(
        "utf-8"
    )


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("utf-8"))
    except (ValueError, TypeError):
        return False


def normalize_email(email: str) -> str:
    return (email or "").strip().lower()


def normalize_phone(phone: str | None) -> str | None:
    if not phone:
        return None
    cleaned = "".join(ch for ch in phone.strip() if ch.isdigit() or ch == "+")
    if cleaned.startswith("00"):
        cleaned = "+" + cleaned[2:]
    return cleaned or None


def mask_phone(phone: str | None) -> str | None:
    if not phone:
        return None
    digits = "".join(ch for ch in phone if ch.isdigit())
    if len(digits) == 13 and digits.startswith("86"):
        digits = digits[2:]
    if len(digits) >= 11:
        return f"{digits[:3]}****{digits[-4:]}"
    if len(digits) >= 7:
        return f"{digits[:2]}***{digits[-2:]}"
    return "***"


def _fernet() -> Fernet:
    configured = current_app.config.get("PHONE_ENC_KEY") or ""
    if configured:
        try:
            return Fernet(configured.encode("utf-8"))
        except (ValueError, TypeError):
            pass
    material = (configured or current_app.config["SECRET_KEY"]).encode("utf-8")
    key = base64.urlsafe_b64encode(hashlib.sha256(material).digest())
    return Fernet(key)


def encrypt_phone(phone: str | None) -> str | None:
    normalized = normalize_phone(phone)
    if not normalized:
        return None
    return _fernet().encrypt(normalized.encode("utf-8")).decode("utf-8")


def decrypt_phone(ciphertext: str | None) -> str | None:
    if not ciphertext:
        return None
    try:
        return _fernet().decrypt(ciphertext.encode("utf-8")).decode("utf-8")
    except (InvalidToken, ValueError, TypeError):
        return None


def hash_phone(phone: str | None) -> str | None:
    normalized = normalize_phone(phone)
    if not normalized:
        return None
    key = (current_app.config.get("PHONE_HASH_KEY") or current_app.config["SECRET_KEY"]).encode(
        "utf-8"
    )
    return hmac.new(key, normalized.encode("utf-8"), hashlib.sha256).hexdigest()


def opaque_token(nbytes: int = 32) -> str:
    return secrets.token_urlsafe(nbytes)


def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def generate_api_key() -> tuple[str, str, str]:
    prefix = "cmk_" + secrets.token_hex(4)
    secret = secrets.token_urlsafe(32)
    full = f"{prefix}.{secret}"
    return full, prefix, hash_token(full)


def parse_api_key(value: str) -> tuple[str, str] | None:
    if not value or "." not in value:
        return None
    prefix, secret = value.split(".", 1)
    if not prefix.startswith("cmk_") or not secret:
        return None
    return prefix, value
