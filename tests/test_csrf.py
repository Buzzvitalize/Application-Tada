import os
import sys
import pytest

sys.path.append(os.path.dirname(os.path.dirname(__file__)))
from app import app, db
from models import User
from auth import generate_reset_token


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


def test_reset_password_requires_csrf(client):
    with app.app_context():
        user = User(username='csrfuser', first_name='A', last_name='B')
        user.set_password('old')
        db.session.add(user)
        db.session.commit()
        token = generate_reset_token(user)
    resp = client.post(f'/reset/{token}', data={'password': 'new'})
    assert resp.status_code == 400
