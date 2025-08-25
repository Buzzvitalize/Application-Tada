import os
import sys
import pytest

sys.path.append(os.path.dirname(os.path.dirname(__file__)))
from app import app, db
from models import User

@pytest.fixture
def client():
    app.config.from_object('config.TestingConfig')
    with app.app_context():
        db.create_all()
        u = User(username='admin', role='admin')
        u.set_password('363636')
        db.session.add(u)
        db.session.commit()
    with app.test_client() as client:
        yield client
    with app.app_context():
        db.drop_all()


def test_login(client):
    resp = client.post('/login', data={'username': 'admin', 'password': '363636'})
    assert resp.status_code == 302
