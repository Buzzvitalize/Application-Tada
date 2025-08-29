import os
import sys
import pytest

sys.path.append(os.path.dirname(os.path.dirname(__file__)))
from app import app, db
from models import User, CompanyInfo


@pytest.fixture
def client(tmp_path):
    db_path = tmp_path / 'test.sqlite'
    app.config.from_object('config.TestingConfig')
    app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{db_path}'
    with app.app_context():
        db.drop_all()
        db.create_all()
        company = CompanyInfo(name='C', street='', sector='', province='', phone='', rnc='')
        db.session.add(company)
        db.session.flush()
        user = User(username='u', email='u@example.com', first_name='F', last_name='L', role='company', company_id=company.id)
        user.set_password('pw')
        db.session.add(user)
        db.session.commit()
    with app.test_client() as client:
        yield client
    with app.app_context():
        db.drop_all()
    if db_path.exists():
        db_path.unlink()


@pytest.fixture
def csrf_client(tmp_path):
    db_path = tmp_path / 'test.sqlite'
    app.config.from_object('config.TestingConfig')
    app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{db_path}'
    app.config['WTF_CSRF_ENABLED'] = True
    with app.app_context():
        db.drop_all()
        db.create_all()
    with app.test_client() as client:
        yield client
    with app.app_context():
        db.drop_all()
    app.config['WTF_CSRF_ENABLED'] = False
    if db_path.exists():
        db_path.unlink()


def test_reset_request_redirects(client):
    resp = client.post('/reset', data={'email': 'u@example.com'})
    assert resp.status_code == 302


def test_reset_request_requires_csrf(csrf_client):
    resp = csrf_client.post('/reset', data={'email': 'x@example.com'})
    assert resp.status_code == 400
