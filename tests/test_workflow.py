import os
import sys
import pytest

sys.path.append(os.path.dirname(os.path.dirname(__file__)))
from app import app, db
from models import (
    CompanyInfo,
    User,
    Client,
    Product,
    Quotation,
    QuotationItem,
    Order,
    Invoice,
    InventoryMovement,
)


@pytest.fixture
def client(tmp_path):
    db_path = tmp_path / "test.sqlite"
    app.config.from_object('config.TestingConfig')
    app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{db_path}'
    with app.app_context():
        db.create_all()
        c1 = CompanyInfo(name='CompA', street='', sector='', province='', phone='', rnc='')
        c2 = CompanyInfo(name='CompB', street='', sector='', province='', phone='', rnc='')
        db.session.add_all([c1, c2])
        db.session.flush()
        u1 = User(username='user1', role='company', company_id=c1.id)
        u1.set_password('pass')
        u2 = User(username='user2', role='company', company_id=c2.id)
        u2.set_password('pass')
        admin = User(username='admin', role='admin')
        admin.set_password('363636')
        db.session.add_all([u1, u2, admin])
        cl1 = Client(name='Alice', company_id=c1.id)
        cl2 = Client(name='BobCorp', is_final_consumer=False, company_id=c2.id)
        db.session.add_all([cl1, cl2])
        db.session.flush()
        prod = Product(code='P1', name='Prod', unit='Unidad', price=100, stock=10, min_stock=2, company_id=c1.id)
        db.session.add(prod)
        q = Quotation(
            client_id=cl1.id,
            subtotal=100,
            itbis=18,
            total=118,
            seller='Vendedor',
            payment_method='Efectivo',
            company_id=c1.id,
        )
        db.session.add(q)
        db.session.flush()
        qi = QuotationItem(
            quotation_id=q.id,
            code='P1',
            product_name='Prod',
            unit='Unidad',
            unit_price=100,
            quantity=1,
            company_id=c1.id,
        )
        db.session.add(qi)
        db.session.commit()
    with app.test_client() as client:
        yield client
    with app.app_context():
        db.drop_all()
    if db_path.exists():
        db_path.unlink()


def login(client, username, password):
    return client.post('/login', data={'username': username, 'password': password})


def test_multi_tenant_isolation(client):
    login(client, 'user1', 'pass')
    resp = client.get('/clientes')
    assert b'Alice' in resp.data
    assert b'BobCorp' not in resp.data
    client.get('/logout')
    login(client, 'user2', 'pass')
    resp = client.get('/clientes')
    assert b'BobCorp' in resp.data
    assert b'Alice' not in resp.data


def test_conversion_and_pdf(client):
    login(client, 'user1', 'pass')
    client.get('/cotizaciones/1/convertir')
    with app.app_context():
        order = Order.query.first()
        order_id = order.id
    client.get(f'/pedidos/{order_id}/facturar')
    with app.app_context():
        invoice = Invoice.query.first()
        product = Product.query.filter_by(code='P1').first()
        movement = InventoryMovement.query.filter_by(product_id=product.id, reference_type='Order', reference_id=order_id).first()
    assert product.stock == 9
    assert movement is not None
    resp = client.get(f'/facturas/{invoice.id}/pdf')
    assert resp.status_code == 200
    assert resp.headers['Content-Type'] == 'application/pdf'


def test_unique_ncf_generation(client):
    login(client, 'user1', 'pass')
    # first conversion
    client.get('/cotizaciones/1/convertir')
    with app.app_context():
        order1 = Order.query.first()
    client.get(f'/pedidos/{order1.id}/facturar')
    # second conversion of same quotation creates new order
    client.get('/cotizaciones/1/convertir')
    with app.app_context():
        order2 = Order.query.order_by(Order.id.desc()).first()
    client.get(f'/pedidos/{order2.id}/facturar')
    with app.app_context():
        ncfs = [inv.ncf for inv in Invoice.query.order_by(Invoice.id).all()]
    assert len(ncfs) == 2
    assert ncfs[0] != ncfs[1]


def test_role_validation(client):
    login(client, 'user1', 'pass')
    resp = client.get('/admin/companies')
    assert resp.status_code == 302
    client.get('/logout')
    login(client, 'admin', '363636')
    resp = client.get('/admin/companies')
    assert resp.status_code == 200
