import os, sys, time
from io import BytesIO
from datetime import datetime, timedelta
import pytest

sys.path.append(os.getcwd())
from app import app, db, ExportLog, Invoice, InvoiceItem, Client, Product, User
from models import CompanyInfo


def _setup_db(db_path):
    app.config.from_object('config.TestingConfig')
    app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{db_path}'
    with app.app_context():
        db.session.remove(); db.engine.dispose(); db.create_all()
        c1 = CompanyInfo(name='C1', street='', sector='', province='', phone='', rnc='')
        c2 = CompanyInfo(name='C2', street='', sector='', province='', phone='', rnc='')
        db.session.add_all([c1, c2]); db.session.flush()
        admin = User(username='admin', role='admin'); admin.set_password('363636')
        u1 = User(username='u1', role='company', company_id=c1.id); u1.set_password('pass')
        acc = User(username='acc', role='contabilidad', company_id=c1.id); acc.set_password('pass')
        db.session.add_all([admin, u1, acc])
        prod = Product(code='A', name='ProdA', unit='Unidad', price=10, category='Servicios', stock=100, min_stock=0, company_id=c1.id)
        db.session.add(prod)
        cli1 = Client(name='Alice', company_id=c1.id)
        cli2 = Client(name='Bob', company_id=c2.id)
        db.session.add_all([cli1, cli2]); db.session.flush()
        # invoices for company1
        for i in range(3):
            inv = Invoice(
                client_id=cli1.id,
                order_id=1,
                subtotal=10,
                itbis=1.8,
                total=11.8,
                invoice_type='Consumidor Final',
                status='Pagada',
                company_id=c1.id,
                date=datetime.utcnow() - timedelta(days=i),
            )
            db.session.add(inv)
            db.session.flush()
            db.session.add(InvoiceItem(invoice_id=inv.id, code='A', product_name='ProdA', unit='Unidad',
                                       unit_price=10, quantity=1, category='Servicios', company_id=c1.id))
        # one invoice for company2
        inv2 = Invoice(
            client_id=cli2.id,
            order_id=1,
            subtotal=10,
            itbis=1.8,
            total=11.8,
            invoice_type='Consumidor Final',
            status='Pagada',
            company_id=c2.id,
            date=datetime.utcnow(),
        )
        db.session.add(inv2); db.session.flush()
        db.session.add(InvoiceItem(invoice_id=inv2.id, code='A', product_name='ProdA', unit='Unidad',
                                   unit_price=10, quantity=1, category='Servicios', company_id=c2.id))
        db.session.commit()


@pytest.fixture
def client(tmp_path):
    db_path = tmp_path / 'qa.sqlite'
    _setup_db(db_path)
    with app.test_client() as c:
        yield c
    with app.app_context():
        db.drop_all()
    if db_path.exists():
        db_path.unlink()


def login(c, user, pwd):
    return c.post('/login', data={'username': user, 'password': pwd})


def test_tampered_company_id(client):
    login(client, 'u1', 'pass')
    resp = client.get('/reportes?company_id=999&ajax=1')
    data = resp.get_json()
    assert resp.status_code == 200
    assert all(inv['total'] == 11.8 for inv in data['invoices'])
    client.get('/logout')


def test_export_headers_and_empty(client):
    login(client, 'admin', '363636')
    client.get('/admin/companies/select/1')
    app.config['MAX_EXPORT_ROWS'] = 100000
    resp = client.get('/reportes/export?formato=csv&estado=Pendiente')
    text = resp.data.decode()
    assert 'Empresa: C1' in text.splitlines()[0]
    assert 'Rango:' in text.splitlines()[1]
    # only headers, no data lines
    assert text.count('\n') <= 5
    with app.app_context():
        log = ExportLog.query.filter_by(formato='csv').order_by(ExportLog.id.desc()).first()
        assert log and log.status == 'success'
    client.get('/logout')


def test_export_summary_and_pdf(client):
    login(client, 'admin', '363636')
    client.get('/admin/companies/select/1')
    app.config['MAX_EXPORT_ROWS'] = 100000
    resp = client.get('/reportes/export?formato=csv&tipo=resumen')
    assert b'Servicios' in resp.data
    resp = client.get('/reportes/export?formato=pdf')
    assert resp.mimetype == 'application/pdf'
    client.get('/logout')


def test_unauthorized_export_logged(client):
    login(client, 'u1', 'pass')
    resp = client.get('/reportes/export?formato=csv')
    assert resp.status_code == 403
    with app.app_context():
        log = ExportLog.query.filter_by(status='fail').order_by(ExportLog.id.desc()).first()
        assert log and log.message == 'permiso'
    client.get('/logout')


def test_export_history_filter(client):
    login(client, 'admin', '363636')
    client.get('/admin/companies/select/1')
    app.config['MAX_EXPORT_ROWS'] = 100000
    client.get('/reportes/export?formato=csv')
    client.get('/reportes/export?formato=xlsx')
    resp = client.get('/reportes/exportes?formato=csv')
    assert resp.status_code == 200
    assert b'csv' in resp.data
    client.get('/logout')
