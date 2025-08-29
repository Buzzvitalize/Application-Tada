import os
import sys
import pytest

sys.path.append(os.path.dirname(os.path.dirname(__file__)))
from app import app, db
from models import CompanyInfo, User, Client


@pytest.fixture
def client(tmp_path):
    db_path = tmp_path / "test.sqlite"
    app.config.from_object('config.TestingConfig')
    app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{db_path}'
    with app.app_context():
        db.create_all()
        comp = CompanyInfo(name='Comp', street='', sector='', province='', phone='', rnc='')
        db.session.add(comp)
        db.session.flush()
        u = User(username='user', first_name='U', last_name='One', role='company', company_id=comp.id)
        u.set_password('pass')
        db.session.add(u)
        for i in range(30):
            c = Client(
                name=f'Client {i}',
                identifier=f'ID{i}',
                email=f'c{i}@ex.com',
                company_id=comp.id,
            )
            db.session.add(c)
        db.session.commit()
    with app.test_client() as client:
        yield client
    with app.app_context():
        db.drop_all()
    if db_path.exists():
        db_path.unlink()


def login(client):
    client.post('/login', data={'username': 'user', 'password': 'pass'})


def test_pagination(client):
    login(client)
    resp = client.get('/clientes')
    assert b'Client 0' in resp.data
    assert b'Client 25' not in resp.data
    resp2 = client.get('/clientes?page=2')
    assert b'Client 25' in resp2.data
    assert b'Client 0' not in resp2.data


def test_search_filters(client):
    login(client)
    resp = client.get('/clientes?q=Client 5')
    assert b'Client 5' in resp.data
    assert b'Client 6' not in resp.data
    resp = client.get('/clientes?q=ID7')
    assert b'Client 7' in resp.data
    assert b'Client 8' not in resp.data
    resp = client.get('/clientes?q=c9@ex.com')
    assert b'Client 9' in resp.data
    assert b'Client 8' not in resp.data
