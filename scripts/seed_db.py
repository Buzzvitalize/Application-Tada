"""Database seeding script.

Creates application tables via Flask-Migrate and optionally populates
initial data such as the default admin user.  Uses the existing
``ensure_admin`` helper to insert an administrator account.
"""
from app import app, db, ensure_admin


def main() -> None:
    """Initialize database and seed default data."""
    with app.app_context():
        db.create_all()
        ensure_admin()
        db.session.remove()


if __name__ == "__main__":
    main()
