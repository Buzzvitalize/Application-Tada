import os
import sys
import pytest

sys.path.append(os.path.dirname(os.path.dirname(__file__)))
from app import app, db
from models import User


@pytest.fixture
def client(tmp_path):
    db_path = tmp_path / "test.sqlite"
    app.config.from_object('config.TestingConfig')
    app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{db_path}'
    with app.app_context():
        db.create_all()
        u = User(username='admin', first_name='Ad', last_name='Min', role='admin')
        u.set_password('363636')
        db.session.add(u)
        db.session.commit()
    with app.test_client() as client:
        yield client
    with app.app_context():
        db.drop_all()
    if db_path.exists():
        db_path.unlink()


def test_login(client):
    resp = client.post('/login', data={'username': 'admin', 'password': '363636'})
    assert resp.status_code == 302
