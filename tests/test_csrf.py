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
    app.config['WTF_CSRF_ENABLED'] = True
    with app.app_context():
        db.create_all()
    with app.test_client() as client:
        yield client
    with app.app_context():
        db.drop_all()
    if db_path.exists():
        db_path.unlink()


def test_request_account_requires_csrf(client):
    resp = client.post('/solicitar-cuenta', data={'first_name': 'A'})
    assert resp.status_code == 400
