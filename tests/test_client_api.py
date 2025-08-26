import os
import sys
import pytest

sys.path.append(os.path.dirname(os.path.dirname(__file__)))
from app import app, db
from models import CompanyInfo, User, Client

@pytest.fixture
def client():
    app.config.from_object('config.TestingConfig')
    with app.app_context():
        db.create_all()
        comp = CompanyInfo(name='Comp', street='', sector='', province='', phone='', rnc='')
        db.session.add(comp)
        db.session.flush()
        u = User(username='user', role='company', company_id=comp.id)
        u.set_password('pass')
        db.session.add(u)
        db.session.commit()
    with app.test_client() as client:
        yield client
    with app.app_context():
        db.drop_all()


def login(client):
    return client.post('/login', data={'username': 'user', 'password': 'pass'})


def test_api_create_client(client):
    login(client)
    resp = client.post('/api/clients', json={'type': 'final', 'name': 'Alice', 'identifier': '001-0000000-1'})
    assert resp.status_code == 200
    data = resp.get_json()
    assert 'id' in data
    with app.app_context():
        assert Client.query.filter_by(name='Alice').first() is not None
