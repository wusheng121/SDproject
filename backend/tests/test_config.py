import pytest

from config import get_config
from utils.security import mask_phone, normalize_phone
from utils.validators import password_errors


def test_production_requires_secrets(monkeypatch):
    for key in (
        "DATABASE_URL",
        "REDIS_URL",
        "SECRET_KEY",
        "PHONE_ENC_KEY",
        "PHONE_HASH_KEY",
    ):
        monkeypatch.delenv(key, raising=False)
    with pytest.raises(RuntimeError):
        get_config("production")


def test_phone_normalization_and_masking():
    assert normalize_phone("+86 138-0013-8000") == "+8613800138000"
    assert mask_phone("13800138000") == "138****8000"
    assert mask_phone("+8613800138000") == "138****8000"


def test_password_policy():
    assert password_errors("short")
    assert password_errors("12345678")
    assert password_errors("Password1") == []
