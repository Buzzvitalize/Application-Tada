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
        existing = Client(name='Exist', identifier='ID1', email='ex@ex.com', company_id=comp.id)
        db.session.add(existing)
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


def test_create_duplicate_identifier(client):
    page = client.get('/clientes')
    token = _get_csrf(page)
    resp = client.post(
        '/clientes',
        data={
            'name': 'Other',
            'identifier': 'ID1',
            'email': 'other@ex.com',
            'type': 'company',
            'csrf_token': token,
        },
        follow_redirects=True,
    )
    text = resp.get_data(as_text=True)
    assert 'Ya existe un cliente con ese RNC/Cédula' in text
    with app.app_context():
        assert Client.query.count() == 1


def test_edit_duplicate_email(client):
    with app.app_context():
        comp = CompanyInfo.query.first()
        c2 = Client(name='Second', identifier='ID2', email='second@ex.com', company_id=comp.id)
        db.session.add(c2)
        db.session.commit()
        cid = c2.id
    page = client.get(f'/clientes/edit/{cid}')
    token = _get_csrf(page)
    resp = client.post(
        f'/clientes/edit/{cid}',
        data={
            'name': 'Second',
            'identifier': 'ID2',
            'email': 'ex@ex.com',
            'type': 'company',
            'csrf_token': token,
        },
        follow_redirects=True,
    )
    text = resp.get_data(as_text=True)
    assert 'Ya existe un cliente con ese correo electrónico' in text
    with app.app_context():
        c2 = Client.query.get(cid)
        assert c2.email == 'second@ex.com'
