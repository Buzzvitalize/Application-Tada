"""Application entry point.

This small wrapper module creates the Flask application using the factory
defined in ``app/__init__.py`` and ensures a default administrator account
exists before the development server starts.  The admin credentials are
useful during local testing so the UI can be exercised without having to
seed the database manually.
"""

from app import create_app
from app.models import db, User


def ensure_admin() -> None:
    """Create a default admin user if one is not already present."""
    if not User.query.filter_by(username="admin").first():
        admin = User(username="admin", role="admin")
        admin.set_password("363636")
        db.session.add(admin)
        db.session.commit()


app = create_app()

if __name__ == "__main__":
    # Seed default admin credentials for local development/testing.  This is
    # wrapped in an application context because the create_app factory does
    # not automatically run database queries at import time.
    with app.app_context():
        ensure_admin()
    app.run(debug=True)
