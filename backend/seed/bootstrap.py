import os
from datetime import datetime

from extensions import db
from models import Role, User, UserRole
from seed.init_products import seed_rbac
from utils.security import hash_password
from utils.validators import password_errors, valid_email


def bootstrap_admin():
    username = (os.getenv("ADMIN_USERNAME") or "").strip()
    email = (os.getenv("ADMIN_EMAIL") or "").strip().lower()
    password = os.getenv("ADMIN_PASSWORD") or ""
    if not username or not email or not password:
        raise RuntimeError("ADMIN_USERNAME, ADMIN_EMAIL and ADMIN_PASSWORD are required")
    normalized_email = valid_email(email)
    if not normalized_email:
        raise RuntimeError("ADMIN_EMAIL is invalid")
    errors = password_errors(password)
    if errors:
        raise RuntimeError("ADMIN_PASSWORD is weak: " + "; ".join(errors))

    seed_rbac()
    user = User.query.filter_by(username=username).first()
    if not user:
        user = User(
            username=username,
            email=normalized_email,
            email_normalized=normalized_email,
            password_hash=hash_password(password),
            user_type="admin",
            email_verified_at=datetime.utcnow(),
        )
        db.session.add(user)
        db.session.flush()
    else:
        user.email = normalized_email
        user.email_normalized = normalized_email
        user.user_type = "admin"
        user.email_verified_at = datetime.utcnow()
        user.password_hash = hash_password(password)

    role = Role.query.filter_by(name="admin").first()
    if role and not UserRole.query.filter_by(user_id=user.id, role_id=role.id).first():
        db.session.add(UserRole(user_id=user.id, role_id=role.id))
    db.session.commit()
    print(f"Admin bootstrapped: {username}")
