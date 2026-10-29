import re

from email_validator import EmailNotValidError, validate_email

from utils.security import normalize_phone


def valid_email(value: str) -> str | None:
    try:
        result = validate_email(value, check_deliverability=False)
        return result.normalized.lower()
    except EmailNotValidError:
        return None


def password_errors(password: str) -> list[str]:
    errors = []
    if len(password or "") < 8:
        errors.append("密码至少 8 位")
    if len(password or "") > 128:
        errors.append("密码不能超过 128 位")
    if not re.search(r"[A-Za-z]", password or ""):
        errors.append("密码必须包含字母")
    if not re.search(r"\d", password or ""):
        errors.append("密码必须包含数字")
    return errors


def valid_phone(value: str | None) -> str | None:
    normalized = normalize_phone(value)
    if not normalized:
        return None
    digits = normalized.lstrip("+")
    if not digits.isdigit() or not 6 <= len(digits) <= 15:
        return None
    return normalized
