import os, sys, pytest
from datetime import datetime, timedelta
sys.path.append(os.path.dirname(os.path.dirname(__file__)))
from app import app, db
from models import CompanyInfo, User, Client, Order, Invoice, InvoiceItem

@pytest.fixture
def client(tmp_path):
    db_path = tmp_path / 'test.sqlite'
    app.config.from_object('config.TestingConfig')
    app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{db_path}'
    with app.app_context():
        db.session.remove(); db.engine.dispose(); db.create_all()
        comp = CompanyInfo(name='Comp', street='', sector='', province='', phone='', rnc='')
        db.session.add(comp); db.session.flush()
        user = User(username='user', role='company', company_id=comp.id)
        user.set_password('pass')
        db.session.add(user)
        cli = Client(name='Alice', company_id=comp.id)
        db.session.add(cli); db.session.flush()
        order = Order(client_id=cli.id, subtotal=100, itbis=18, total=118, company_id=comp.id)
        db.session.add(order); db.session.flush()
        inv = Invoice(client_id=cli.id, order_id=order.id, subtotal=100, itbis=18, total=118,
                      invoice_type='Pagada', company_id=comp.id, date=datetime.utcnow())
        db.session.add(inv); db.session.flush()
        item = InvoiceItem(invoice_id=inv.id, code='P1', product_name='Prod', unit='Unidad', unit_price=100,
                           quantity=1, category='Servicios', company_id=comp.id)
        db.session.add(item); db.session.commit()
    with app.test_client() as client:
        yield client
    with app.app_context():
        db.drop_all()
    if db_path.exists():
        db_path.unlink()

def login(c, username, password):
    return c.post('/login', data={'username': username, 'password': password})

def test_report_filters(client):
    login(client, 'user', 'pass')
    resp = client.get('/reportes?estado=Pagada&categoria=Servicios&ajax=1')
    data = resp.get_json()
    assert len(data['invoices']) == 1
    assert data['invoices'][0]['estado'] == 'Pagada'
    client.get('/logout')

def test_export_permissions(client):
    login(client, 'user', 'pass')
    resp = client.get('/reportes/export?formato=csv')
    assert resp.status_code == 403
    client.get('/logout')
    login(client, 'admin', '363636')
    client.get('/admin/companies/select/1')
    resp = client.get('/reportes/export?formato=csv', follow_redirects=True)
    assert resp.status_code == 200
    resp = client.get('/reportes/export?formato=pdf', follow_redirects=True)
    assert resp.status_code == 200
