import os
import sys
import pytest

sys.path.append(os.path.dirname(os.path.dirname(__file__)))
from app import app, db
from models import User, CompanyInfo, NcfLog


@pytest.fixture
def client(tmp_path):
    db_path = tmp_path / "test.sqlite"
    app.config.from_object('config.TestingConfig')
    app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{db_path}'
    with app.app_context():
        db.create_all()
        company = CompanyInfo(name='Comp', street='s', sector='s', province='p', phone='1', rnc='1')
        db.session.add(company)
        db.session.flush()
        u = User(username='mgr', first_name='Man', last_name='Ager', role='manager', company_id=company.id)
        u.set_password('pass')
        db.session.add(u)
        db.session.commit()
    with app.test_client() as client:
        client.post('/login', data={'username': 'mgr', 'password': 'pass'})
        yield client
    with app.app_context():
        db.drop_all()
    if db_path.exists():
        db_path.unlink()


def test_manager_can_update_ncf_and_log(client):
    with app.app_context():
        company = CompanyInfo.query.first()
        old_final = company.ncf_final
    resp = client.post('/ajustes', data={
        'name': 'Comp', 'rnc': '1', 'phone': '1', 'street': 's', 'sector': 's', 'province': 'p',
        'ncf_final': str(old_final + 5), 'ncf_fiscal': '1'
    })
    assert resp.status_code == 302
    with app.app_context():
        log = NcfLog.query.filter_by(company_id=company.id).first()
        assert log is not None
        assert log.new_final == old_final + 5


def test_ncf_cannot_decrease(client):
    with app.app_context():
        company = CompanyInfo.query.first()
        current = company.ncf_final
    resp = client.post('/ajustes', data={
        'name': 'Comp', 'rnc': '1', 'phone': '1', 'street': 's', 'sector': 's', 'province': 'p',
        'ncf_final': str(current - 1), 'ncf_fiscal': '1'
    }, follow_redirects=True)
    assert b'NCF Consumidor Final no puede ser menor' in resp.data


def test_manager_cannot_change_other_fields(client):
    with app.app_context():
        company = CompanyInfo.query.first()
        original_name = company.name
        original_phone = company.phone
    client.post('/ajustes', data={'name': 'Nuevo', 'phone': '999', 'ncf_final': '5', 'ncf_fiscal': '1'})
    with app.app_context():
        c = CompanyInfo.query.first()
        assert c.name == original_name
        assert c.phone == original_phone


def test_manager_user_limit(client):
    client.post('/ajustes', data={'action': "create_user", "first_name": "A", "last_name": "B", "username": "u1", "password": "p"})
    client.post('/ajustes', data={'action': "create_user", "first_name": "C", "last_name": "D", "username": "u2", "password": "p"})
    resp = client.post('/ajustes', data={'action': "create_user", "first_name": "E", "last_name": "F", "username": "u3", "password": "p"}, follow_redirects=True)
    assert b'Los managers solo pueden crear 2 usuarios' in resp.data

