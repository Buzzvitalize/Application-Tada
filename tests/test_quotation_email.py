import os
import sys
import pytest
from datetime import datetime, timedelta

sys.path.append(os.path.dirname(os.path.dirname(__file__)))
from app import app, db
from models import CompanyInfo, User, Client, Quotation, QuotationItem


@pytest.fixture
def client(tmp_path):
    db_path = tmp_path / "test.sqlite"
    app.config.from_object('config.TestingConfig')
    app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{db_path}'
    with app.app_context():
        db.drop_all()
        db.create_all()
        comp = CompanyInfo(name='Comp', street='', sector='', province='', phone='', rnc='')
        db.session.add(comp)
        db.session.flush()
        user = User(username='user', first_name='U', last_name='One', role='company', company_id=comp.id)
        user.set_password('pass')
        db.session.add(user)
        cli = Client(name='Client', email='client@example.com', company_id=comp.id)
        db.session.add(cli)
        db.session.flush()
        now = datetime.utcnow()
        q = Quotation(client_id=cli.id, subtotal=10, itbis=0, total=10,
                      date=now, valid_until=now + timedelta(days=30), company_id=comp.id)
        db.session.add(q)
        db.session.flush()
        qi = QuotationItem(quotation_id=q.id, code='P1', product_name='Prod', unit='Unidad', unit_price=10, quantity=1, company_id=comp.id)
        db.session.add(qi)
        db.session.commit()
        qid = q.id
        cli_email = cli.email
    with app.test_client() as test_client:
        yield test_client, qid, cli_email
    with app.app_context():
        db.drop_all()
    if db_path.exists():
        db_path.unlink()


def login(cli):
    cli.post('/login', data={'username': 'user', 'password': 'pass'})


def test_send_quotation_email(client, monkeypatch):
    cli, qid, email = client
    login(cli)
    sent = {}
    def fake_send(to, subject, html, attachments=None):
        sent['to'] = to
        sent['attachments'] = attachments
    monkeypatch.setattr('app.send_email', fake_send)
    resp = cli.post(f'/cotizaciones/{qid}/enviar', follow_redirects=True)
    assert resp.status_code == 200
    assert f'Cotización enviada con éxito a {email}'.encode() in resp.data
    assert sent['to'] == email
    assert sent['attachments']
    filename, data = sent['attachments'][0]
    assert filename == f'cotizacion_{qid}.pdf'
    assert data.startswith(b'%PDF')
