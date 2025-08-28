import os
import sys
import pytest

sys.path.append(os.path.dirname(os.path.dirname(__file__)))
from app import app, db


@pytest.fixture
def client(tmp_path):
    db_path = tmp_path / 'test.sqlite'
    app.config.from_object('config.TestingConfig')
    app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{db_path}'
    with app.app_context():
        db.create_all()
    with app.test_client() as client:
        yield client
    with app.app_context():
        db.drop_all()
    if db_path.exists():
        db_path.unlink()


def test_blueprint_registration():
    assert 'auth' in app.blueprints


def test_migrate_extension_present():
    try:
        import flask_migrate  # noqa: F401
    except ModuleNotFoundError:  # pragma: no cover
        pytest.skip('Flask-Migrate not installed')
    assert 'migrate' in app.extensions
