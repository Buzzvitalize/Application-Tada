import os
import sys
import pytest

sys.path.append(os.path.dirname(os.path.dirname(__file__)))
from app import app, db
from models import User, CompanyInfo, AccountRequest
from werkzeug.security import generate_password_hash

@pytest.fixture
def client(tmp_path):
    db_path = tmp_path / "test.sqlite"
    app.config.from_object('config.TestingConfig')
    app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{db_path}'
    with app.app_context():
        db.create_all()
        company = CompanyInfo(name='Comp', street='', sector='', province='', phone='', rnc='')
        db.session.add(company)
        db.session.flush()
        admin = User(username='admin', first_name='Ad', last_name='Min', role='admin', company_id=company.id, email='admin@example.com')
        admin.set_password('363636')
        user = User(username='user', first_name='U', last_name='Ser', role='company', company_id=company.id, email='old@ex.com')
        user.set_password('123')
        db.session.add_all([admin, user])
        db.session.commit()
    with app.test_client() as c:
        yield c
    with app.app_context():
        db.drop_all()
    if db_path.exists():
        db_path.unlink()


def login(c, username, password):
    return c.post('/login', data={'username': username, 'password': password})


def test_admin_access_and_role_change(client):
    login(client, 'admin', '363636')
    r = client.get('/cpaneltx')
    assert r.status_code == 200
    # change role
    with app.app_context():
        user = User.query.filter_by(username='user').first()
    client.post(f'/cpaneltx/users/{user.id}/role', data={'role': 'manager'})
    with app.app_context():
        assert User.query.get(user.id).role == 'manager'


def test_admin_update_email_password(client):
    login(client, 'admin', '363636')
    with app.app_context():
        user = User.query.filter_by(username='user').first()
    client.post(f'/cpaneltx/users/{user.id}/update', data={'email': 'new@ex.com', 'password': 'newpass'})
    with app.app_context():
        u = User.query.get(user.id)
        assert u.email == 'new@ex.com'
        assert u.check_password('newpass')


def test_non_admin_denied(client):
    login(client, 'user', '123')
    r = client.get('/cpaneltx')
    assert r.status_code == 302


def test_account_approval_sends_email(client, monkeypatch):
    with app.app_context():
        req = AccountRequest(
            account_type='personal',
            first_name='Ana',
            last_name='Doe',
            company='AnaCo',
            identifier='001',
            phone='123',
            email='ana@example.com',
            username='anita',
            password=generate_password_hash('pw'),
        )
        db.session.add(req)
        db.session.commit()
        rid = req.id
    sent = {}
    def fake_send(to, subject, html):
        sent['to'] = to
        sent['subject'] = subject
        sent['html'] = html
    monkeypatch.setattr('app.send_email', fake_send)
    login(client, 'admin', '363636')
    client.post(f'/admin/solicitudes/{rid}/aprobar', data={'role': 'company'})
    assert sent['to'] == 'ana@example.com'
    assert 'aprobada' in sent['subject'].lower()
    with app.app_context():
        user = User.query.filter_by(username='anita').first()
        assert user is not None
        assert user.check_password('pw')
        # El hash nunca debe aparecer en el correo
        assert user.password not in sent['html']
        assert '/reset/' in sent['html']
