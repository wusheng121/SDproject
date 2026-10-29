"""Local development helper.

Production must use Alembic:
    cd backend
    flask --app app db upgrade
"""
import sys

sys.path.insert(0, "backend")

from app import app
from extensions import db
from seed.init_products import seed_all


def main():
    with app.app_context():
        db.create_all()
        seed_all()
        print("Database initialized with demo data (development only).")


if __name__ == "__main__":
    main()
