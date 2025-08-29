import os
import sys
import pytest

sys.path.append(os.path.dirname(os.path.dirname(__file__)))
from app import app, db
from models import AccountRequest


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


def _base_data():
    return {
        'account_type': 'personal',
        'first_name': 'Ana',
        'last_name': 'Doe',
        'company': 'AnaCo',
        'identifier': '001',
        'phone': '123',
        'email': 'ana@example.com',
        'address': '',
        'website': '',
        'username': 'anita',
        'password': 'pw',
        'confirm_password': 'pw',
    }


def test_terms_required(client):
    resp = client.post('/solicitar-cuenta', data=_base_data(), follow_redirects=True)
    assert 'Debe aceptar los Términos y Condiciones' in resp.get_data(as_text=True)
    with app.app_context():
        assert AccountRequest.query.count() == 0


def test_terms_recorded(client):
    data = _base_data()
    data['accepted_terms'] = 'y'
    resp = client.post('/solicitar-cuenta', data=data)
    assert resp.status_code == 302
    with app.app_context():
        req = AccountRequest.query.filter_by(username='anita').first()
        assert req is not None
        assert req.accepted_terms is True
        assert req.accepted_terms_at is not None
        assert req.accepted_terms_ip == '127.0.0.1'
        assert 'werkzeug' in req.accepted_terms_user_agent.lower()


def test_terminos_page(client):
    resp = client.get('/terminos')
    assert resp.status_code == 200
    body = resp.get_data(as_text=True)
    assert 'Términos y Condiciones de Uso – Tiendix' in body
    assert 'actualmente gratuito' in body
