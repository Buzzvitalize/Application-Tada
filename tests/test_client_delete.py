import os
import sys
import re
import pytest

sys.path.append(os.path.dirname(os.path.dirname(__file__)))
from app import app, db
from models import CompanyInfo, User, Client


@pytest.fixture
def client(tmp_path):
    db_path = tmp_path / 'test.sqlite'
    app.config.from_object('config.TestingConfig')
    app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{db_path}'
    app.config['WTF_CSRF_ENABLED'] = True
    with app.app_context():
        db.create_all()
        comp = CompanyInfo(name='Comp', street='', sector='', province='', phone='', rnc='')
        db.session.add(comp)
        db.session.flush()
        u = User(username='u', first_name='U', last_name='L', role='company', company_id=comp.id)
        u.set_password('p')
        db.session.add(u)
        c = Client(name='Del', identifier='D1', email='d@ex.com', company_id=comp.id)
        db.session.add(c)
        db.session.commit()
    with app.test_client() as client:
        login_page = client.get('/login')
        token = _get_csrf(login_page)
        client.post('/login', data={'username': 'u', 'password': 'p', 'csrf_token': token})
        yield client
    with app.app_context():
        db.drop_all()
    if db_path.exists():
        db_path.unlink()


def _get_csrf(resp):
    match = re.search(b'name="csrf_token"[^>]*value="([^"]+)"', resp.data)
    assert match, 'csrf token not found'
    return match.group(1).decode()


def test_delete_requires_post(client):
    resp = client.get('/clientes/delete/1')
    assert resp.status_code == 405


def test_delete_requires_csrf(client):
    resp = client.post('/clientes/delete/1')
    assert resp.status_code == 400


def test_delete_success(client):
    page = client.get('/clientes')
    token = _get_csrf(page)
    resp = client.post('/clientes/delete/1', data={'csrf_token': token}, follow_redirects=True)
    assert resp.status_code == 200
    assert b'Cliente eliminado' in resp.data
    with app.app_context():
        assert Client.query.count() == 0
