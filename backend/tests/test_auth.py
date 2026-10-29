from datetime import datetime, timedelta

from extensions import db
from models import EmailVerificationToken, PasswordResetToken, User
from utils.security import hash_token


def _user(username):
    return User.query.filter_by(username=username).first()


def test_register_login_profile_and_preferences(client, app):
    response = client.post(
        "/api/v1/auth/register",
        json={
            "username": "newuser",
            "email": "NewUser@Example.com",
            "password": "NewPass123",
            "phone": "13800138000",
        },
    )
    assert response.status_code == 201
    user_data = response.get_json()["data"]["user"]
    assert user_data["email"] == "newuser@example.com"
    assert user_data["phone"] == "138****8000"
    assert user_data["roles"] == ["normal_user"]

    login_response = client.post(
        "/api/v1/auth/login",
        json={"identifier": "newuser@example.com", "password": "NewPass123"},
    )
    assert login_response.status_code == 200
    token = login_response.get_json()["data"]["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    me = client.get("/api/v1/users/me", headers=headers)
    assert me.status_code == 200
    assert me.get_json()["data"]["user"]["username"] == "newuser"
    assert "product:publish" in me.get_json()["data"]["user"]["permissions"]

    prefs = client.put(
        "/api/v1/users/me/preferences",
        headers=headers,
        json={"categories": ["手机", "耳机"]},
    )
    assert prefs.status_code == 200
    assert prefs.get_json()["data"]["preferred_categories"] == ["手机", "耳机"]

    updated = client.patch(
        "/api/v1/users/me",
        headers=headers,
        json={"phone": "13900139000"},
    )
    assert updated.status_code == 200
    assert updated.get_json()["data"]["user"]["phone"] == "139****9000"


def test_weak_password_and_duplicate_account(client):
    weak = client.post(
        "/api/v1/auth/register",
        json={"username": "weakuser", "email": "weak@example.com", "password": "12345678"},
    )
    assert weak.status_code == 422

    duplicate = client.post(
        "/api/v1/auth/register",
        json={"username": "testuser", "email": "other@example.com", "password": "Other12345"},
    )
    assert duplicate.status_code == 409


def test_refresh_rotation_and_logout(client):
    login_response = client.post(
        "/api/v1/auth/login",
        json={"identifier": "testuser", "password": "Test12345"},
    )
    assert login_response.status_code == 200
    assert client.get_cookie("cm_refresh", path="/api/v1/auth") is not None

    refreshed = client.post("/api/v1/auth/refresh")
    assert refreshed.status_code == 200
    assert refreshed.get_json()["data"]["access_token"]

    logged_out = client.post("/api/v1/auth/logout")
    assert logged_out.status_code == 200
    after_logout = client.post("/api/v1/auth/refresh")
    assert after_logout.status_code == 401


def test_refresh_replay_revokes_family(client):
    login_response = client.post(
        "/api/v1/auth/login",
        json={"identifier": "testuser", "password": "Test12345"},
    )
    assert login_response.status_code == 200
    old_cookie = client.get_cookie("cm_refresh", path="/api/v1/auth").value
    first_refresh = client.post("/api/v1/auth/refresh")
    assert first_refresh.status_code == 200
    new_cookie = client.get_cookie("cm_refresh", path="/api/v1/auth").value
    assert new_cookie != old_cookie

    client.set_cookie("cm_refresh", old_cookie, path="/api/v1/auth")
    replay = client.post("/api/v1/auth/refresh")
    assert replay.status_code == 401

    client.set_cookie("cm_refresh", new_cookie, path="/api/v1/auth")
    family_revoked = client.post("/api/v1/auth/refresh")
    assert family_revoked.status_code == 401


def test_email_verification_and_password_reset(client, app):
    with app.app_context():
        user = _user("testuser")
        user.email_verified_at = None
        raw_email = "email-token"
        db.session.add(
            EmailVerificationToken(
                user_id=user.id,
                token_hash=hash_token(raw_email),
                expires_at=datetime.utcnow() + timedelta(hours=1),
            )
        )
        raw_reset = "reset-token"
        db.session.add(
            PasswordResetToken(
                user_id=user.id,
                token_hash=hash_token(raw_reset),
                expires_at=datetime.utcnow() + timedelta(minutes=30),
            )
        )
        db.session.commit()

    verified = client.post("/api/v1/auth/verify-email", json={"token": "email-token"})
    assert verified.status_code == 200
    with app.app_context():
        assert _user("testuser").email_verified_at is not None

    reset = client.post(
        "/api/v1/auth/reset-password",
        json={"token": "reset-token", "new_password": "Reset12345"},
    )
    assert reset.status_code == 200
    old_login = client.post(
        "/api/v1/auth/login",
        json={"identifier": "testuser", "password": "Test12345"},
    )
    assert old_login.status_code == 401
    new_login = client.post(
        "/api/v1/auth/login",
        json={"identifier": "testuser", "password": "Reset12345"},
    )
    assert new_login.status_code == 200


def test_ban_revokes_access_and_login(client, app):
    admin_login = client.post(
        "/api/v1/auth/login",
        json={"identifier": "admin", "password": "Admin12345"},
    )
    assert admin_login.status_code == 200
    admin_token = admin_login.get_json()["data"]["access_token"]

    target = client.post(
        "/api/v1/auth/login",
        json={"identifier": "testuser", "password": "Test12345"},
    )
    target_token = target.get_json()["data"]["access_token"]

    with app.app_context():
        user_id = _user("testuser").id

    banned = client.post(
        f"/api/v1/admin/users/{user_id}/ban",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={"reason": "test"},
    )
    assert banned.status_code == 200
    blocked = client.get(
        "/api/v1/users/me", headers={"Authorization": f"Bearer {target_token}"}
    )
    assert blocked.status_code == 401
    login_blocked = client.post(
        "/api/v1/auth/login",
        json={"identifier": "testuser", "password": "Test12345"},
    )
    assert login_blocked.status_code == 403


def test_normal_user_cannot_access_admin(client):
    login_response = client.post(
        "/api/v1/auth/login",
        json={"identifier": "testuser", "password": "Test12345"},
    )
    token = login_response.get_json()["data"]["access_token"]
    response = client.get("/api/v1/admin/users", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 403
