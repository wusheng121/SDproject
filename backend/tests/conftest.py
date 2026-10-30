import os
import sys
from pathlib import Path

import pytest

BACKEND_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_DIR))
os.environ["DEEPSEEK_API_KEY"] = ""
os.environ.setdefault("APP_ENV", "testing")
os.environ.setdefault("SECRET_KEY", "test-secret-0123456789abcdef0123456789")
os.environ.setdefault("TEST_DATABASE_URL", "sqlite:///:memory:")

from app import create_app  # noqa: E402
from extensions import db  # noqa: E402
from seed.init_products import (  # noqa: E402
    seed_categories,
    seed_products,
    seed_rbac,
    seed_users,
)


@pytest.fixture(scope="session")
def app():
    application = create_app("testing")
    with application.app_context():
        db.create_all()
    yield application
    with application.app_context():
        db.drop_all()


@pytest.fixture(autouse=True)
def reset_data(app):
    with app.app_context():
        db.drop_all()
        db.create_all()
        seed_rbac()
        seed_categories()
        seed_users()
        seed_products()
    yield
    with app.app_context():
        db.session.remove()


@pytest.fixture()
def client(app):
    return app.test_client()


def login(client, identifier="testuser", password="Test12345"):
    return client.post(
        "/api/v1/auth/login",
        json={"identifier": identifier, "password": password},
    )


def auth_headers(response):
    token = response.get_json()["data"]["access_token"]
    return {"Authorization": f"Bearer {token}"}
