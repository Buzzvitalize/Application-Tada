import os
import sys
from datetime import datetime, timedelta
import pytest

sys.path.append(os.path.dirname(os.path.dirname(__file__)))
from app import app, db
from models import CompanyInfo, User, Client, Quotation


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
        user = User(username='user', first_name='U', last_name='One', role='company', company_id=comp.id)
        user.set_password('pass')
        db.session.add(user)
        c1 = Client(name='Client A', identifier='A', email='a@x.com', company_id=comp.id)
        c2 = Client(name='Client B', identifier='B', email='b@x.com', company_id=comp.id)
        db.session.add_all([c1, c2])
        db.session.flush()
        now = datetime.utcnow()
        for i in range(25):
            d = now - timedelta(days=i)
            q = Quotation(client_id=c1.id, subtotal=0, itbis=0, total=i,
                          date=d, valid_until=d + timedelta(days=30), company_id=comp.id)
            db.session.add(q)
        conv_date = now - timedelta(days=25)
        conv = Quotation(client_id=c2.id, subtotal=0, itbis=0, total=100,
                          date=conv_date, valid_until=conv_date + timedelta(days=30), status='convertida', company_id=comp.id)
        old_date = now - timedelta(days=40)
        old = Quotation(client_id=c2.id, subtotal=0, itbis=0, total=200,
                         date=old_date, valid_until=old_date + timedelta(days=30), company_id=comp.id)
        db.session.add_all([conv, old])
        db.session.commit()
        conv_id, old_id = conv.id, old.id
    with app.test_client() as test_client:
        yield test_client, conv_id, old_id
    with app.app_context():
        db.drop_all()
    if db_path.exists():
        db_path.unlink()


def login(cli):
    cli.post('/login', data={'username': 'user', 'password': 'pass'})


def test_pagination(client):
    cli, conv_id, _ = client
    login(cli)
    resp = cli.get('/cotizaciones')
    assert f'>{conv_id}<'.encode() not in resp.data
    resp2 = cli.get('/cotizaciones?page=2')
    assert f'>{conv_id}<'.encode() in resp2.data


def test_client_filter(client):
    cli, _, _ = client
    login(cli)
    resp = cli.get('/cotizaciones?client=Client B')
    assert b'Client B' in resp.data
    assert b'Client A' not in resp.data


def test_date_filter(client):
    cli, _, _ = client
    login(cli)
    date_from = (datetime.utcnow() - timedelta(days=5)).strftime('%Y-%m-%d')
    resp = cli.get(f'/cotizaciones?date_from={date_from}')
    assert resp.data.count(b'<tr class="border-t">') == 6


def test_status_filter(client):
    cli, conv_id, old_id = client
    login(cli)
    resp = cli.get('/cotizaciones?status=convertida')
    assert f'>{conv_id}<'.encode() in resp.data
    assert f'>{old_id}<'.encode() not in resp.data
    resp = cli.get('/cotizaciones?status=vencida')
    assert f'>{old_id}<'.encode() in resp.data
    assert f'>{conv_id}<'.encode() not in resp.data
