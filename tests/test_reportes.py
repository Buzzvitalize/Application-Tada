import os, sys, pytest
from datetime import datetime, timedelta
sys.path.append(os.path.dirname(os.path.dirname(__file__)))
from app import app, db
from models import CompanyInfo, User, Client, Order, Invoice, InvoiceItem, Product, Warehouse, ProductStock

@pytest.fixture
def client(tmp_path):
    db_path = tmp_path / 'test.sqlite'
    app.config.from_object('config.TestingConfig')
    app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{db_path}'
    with app.app_context():
        db.session.remove(); db.engine.dispose(); db.create_all()
        comp = CompanyInfo(name='Comp', street='', sector='', province='', phone='', rnc='')
        db.session.add(comp); db.session.flush()
        user = User(username='user', first_name='U', last_name='One', role='company', company_id=comp.id)
        user.set_password('pass')
        mgr = User(username='mgr', first_name='M', last_name='Gr', role='manager', company_id=comp.id)
        mgr.set_password('pass')
        db.session.add_all([user, mgr])
        cli = Client(name='Alice', company_id=comp.id)
        db.session.add(cli); db.session.flush()
        order = Order(client_id=cli.id, subtotal=100, itbis=18, total=118, company_id=comp.id)
        db.session.add(order); db.session.flush()
        inv = Invoice(
            client_id=cli.id,
            order_id=order.id,
            subtotal=100,
            itbis=18,
            total=118,
            invoice_type='Consumidor Final',
            status='Pagada',
            payment_method='Efectivo',
            company_id=comp.id,
            date=datetime.utcnow(),
        )
        db.session.add(inv); db.session.flush()
        item = InvoiceItem(invoice_id=inv.id, code='P1', product_name='Prod', unit='Unidad', unit_price=100,
                           quantity=1, category='Alimentos y Bebidas', company_id=comp.id)
        db.session.add(item); db.session.commit()
    with app.test_client() as client:
        yield client
    with app.app_context():
        db.drop_all()
    if db_path.exists():
        db_path.unlink()


@pytest.fixture
def multi_client(tmp_path):
    db_path = tmp_path / 'test.sqlite'
    app.config.from_object('config.TestingConfig')
    app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{db_path}'
    with app.app_context():
        db.session.remove(); db.engine.dispose(); db.create_all()
        comp1 = CompanyInfo(name='Comp1', street='', sector='', province='', phone='', rnc='')
        comp2 = CompanyInfo(name='Comp2', street='', sector='', province='', phone='', rnc='')
        db.session.add_all([comp1, comp2]); db.session.flush()
        user1 = User(username='user1', first_name='U1', last_name='One', role='company', company_id=comp1.id); user1.set_password('pass')
        user2 = User(username='user2', first_name='U2', last_name='Two', role='company', company_id=comp2.id); user2.set_password('pass')
        admin = User(username='admin', first_name='Ad', last_name='Min', role='admin', company_id=None); admin.set_password('363636')
        db.session.add_all([user1, user2, admin])
        for i in range(50):
            cli = Client(name=f'C{i}', company_id=comp1.id)
            db.session.add(cli); db.session.flush()
            order = Order(client_id=cli.id, subtotal=100, itbis=18, total=118, company_id=comp1.id)
            db.session.add(order); db.session.flush()
            inv = Invoice(
                client_id=cli.id,
                order_id=order.id,
                subtotal=100,
                itbis=18,
                total=118,
                invoice_type='Consumidor Final',
                status='Pagada',
                payment_method='Efectivo',
                company_id=comp1.id,
                date=datetime.utcnow() - timedelta(days=i),
            )
            db.session.add(inv); db.session.flush()
            item = InvoiceItem(invoice_id=inv.id, code='P1', product_name='Prod', unit='Unidad', unit_price=100, quantity=1, category='Alimentos y Bebidas', company_id=comp1.id)
            db.session.add(item)
        cli2 = Client(name='Other', company_id=comp2.id)
        db.session.add(cli2); db.session.flush()
        order2 = Order(client_id=cli2.id, subtotal=50, itbis=9, total=59, company_id=comp2.id)
        db.session.add(order2); db.session.flush()
        inv2 = Invoice(
            client_id=cli2.id,
            order_id=order2.id,
            subtotal=50,
            itbis=9,
            total=59,
            invoice_type='Consumidor Final',
            status='Pendiente',
            payment_method='Transferencia',
            company_id=comp2.id,
            date=datetime.utcnow(),
        )
        db.session.add(inv2); db.session.flush()
        item2 = InvoiceItem(invoice_id=inv2.id, code='P1', product_name='Prod', unit='Unidad', unit_price=50, quantity=1, category='Alimentos y Bebidas', company_id=comp2.id)
        db.session.add(item2); db.session.commit()
    with app.test_client() as c:
        yield c
    with app.app_context():
        db.drop_all()
    if db_path.exists():
        db_path.unlink()

def login(c, username, password):
    return c.post('/login', data={'username': username, 'password': password})

def test_report_filters(client):
    login(client, 'user', 'pass')
    resp = client.get('/reportes?estado=Pagada&categoria=Alimentos%20y%20Bebidas&ajax=1')
    data = resp.get_json()
    assert len(data['invoices']) == 1
    assert data['invoices'][0]['estado'] == 'Pagada'
    client.get('/logout')

def test_export_permissions(client):
    login(client, 'user', 'pass')
    resp = client.get('/reportes/export?formato=csv')
    assert resp.status_code == 403
    client.get('/logout')


def test_inventory_export(client):
    login(client, 'mgr', 'pass')
    with app.app_context():
        comp = CompanyInfo.query.first()
        prod = Product(code='P1', name='Prod', unit='Unidad', price=10, company_id=comp.id)
        wh = Warehouse(name='Principal', company_id=comp.id)
        db.session.add_all([prod, wh])
        db.session.flush()
        ps = ProductStock(product_id=prod.id, warehouse_id=wh.id, stock=5, min_stock=1, company_id=comp.id)
        db.session.add(ps)
        db.session.commit()
    resp = client.get('/reportes/inventario/export')
    assert resp.status_code == 200
    assert b'P1' in resp.data
    login(client, 'mgr', 'pass')
    resp = client.get('/reportes/export?formato=csv', follow_redirects=True)
    assert resp.status_code == 200
    resp = client.get('/reportes/export?formato=pdf', follow_redirects=True)
    assert resp.status_code == 200
    client.get('/logout')
    login(client, 'admin', '363636')
    client.get('/admin/companies/select/1')
    resp = client.get('/reportes/export?formato=csv', follow_redirects=True)
    assert resp.status_code == 200
    resp = client.get('/reportes/export?formato=pdf', follow_redirects=True)
    assert resp.status_code == 200


def test_invalid_filters(client):
    login(client, 'user', 'pass')
    resp = client.get('/reportes?fecha_inicio=2020-01-01&fecha_fin=2020-01-02&estado=Foo&categoria=Bar&ajax=1')
    data = resp.get_json()
    assert data['invoices'] == []
    client.get('/logout')


def test_payment_method_stats(client):
    with app.app_context():
        comp = CompanyInfo.query.first()
        cli = Client.query.first()
        order = Order(client_id=cli.id, subtotal=50, itbis=9, total=59, company_id=comp.id)
        db.session.add(order); db.session.flush()
        inv = Invoice(client_id=cli.id, order_id=order.id, subtotal=50, itbis=9, total=59,
                      invoice_type='Consumidor Final', status='Pagada',
                      payment_method='Transferencia', company_id=comp.id,
                      date=datetime.utcnow())
        db.session.add(inv); db.session.commit()
    login(client, 'user', 'pass')
    resp = client.get('/reportes?ajax=1')
    data = resp.get_json()
    assert data['stats']['cash'] > 0
    assert data['stats']['transfer'] > 0
    client.get('/logout')


def test_mark_invoice_paid(client):
    with app.app_context():
        comp = CompanyInfo.query.first()
        cli = Client.query.first()
        order = Order(client_id=cli.id, subtotal=40, itbis=7.2, total=47.2, company_id=comp.id)
        db.session.add(order); db.session.flush()
        inv = Invoice(client_id=cli.id, order_id=order.id, subtotal=40, itbis=7.2, total=47.2,
                      invoice_type='Consumidor Final', status='Pendiente',
                      payment_method='Efectivo', company_id=comp.id,
                      date=datetime.utcnow())
        db.session.add(inv); db.session.commit()
        invoice_id = inv.id
    login(client, 'user', 'pass')
    client.post(f'/facturas/{invoice_id}/pagar', follow_redirects=True)
    with app.app_context():
        assert Invoice.query.get(invoice_id).status == 'Pagada'
    client.get('/logout')


def test_pagination_with_filters(multi_client):
    login(multi_client, 'user1', 'pass')
    resp = multi_client.get('/reportes?page=5&ajax=1')
    data = resp.get_json()
    assert data['pagination']['pages'] >= 5 or data['invoices'] == []
    assert data['pagination']['page'] == 5
    multi_client.get('/logout')


def test_export_large_csv_xlsx(multi_client):
    login(multi_client, 'admin', '363636')
    multi_client.get('/admin/companies/select/1')
    resp = multi_client.get('/reportes/export?formato=csv')
    assert resp.status_code == 200
    lines = resp.data.decode().strip().splitlines()
    assert len(lines) > 50  # header + data
    resp = multi_client.get('/reportes/export?formato=xlsx')
    assert resp.status_code == 200
    multi_client.get('/logout')


def test_multi_tenant_isolation(multi_client):
    login(multi_client, 'user2', 'pass')
    resp = multi_client.get('/reportes?ajax=1')
    data = resp.get_json()
    assert len(data['invoices']) == 1
    resp = multi_client.get('/reportes/export?formato=csv')
    assert resp.status_code == 403
    multi_client.get('/logout')


def test_account_statement_pdf(client):
    login(client, 'user', 'pass')
    with app.app_context():
        comp = CompanyInfo.query.first()
        cli = Client.query.first()
        cid = cli.id
        order = Order(client_id=cid, subtotal=50, itbis=9, total=59, company_id=comp.id)
        db.session.add(order); db.session.flush()
        inv = Invoice(client_id=cid, order_id=order.id, subtotal=50, itbis=9, total=59,
                      invoice_type='Consumidor Final', status='Pendiente', payment_method='Efectivo', company_id=comp.id)
        db.session.add(inv); db.session.commit()
    resp = client.get('/reportes/estado-cuentas')
    assert resp.status_code == 200
    resp = client.get(f'/reportes/estado-cuentas/{cid}?pdf=1')
    assert resp.status_code == 200
    client.get('/logout')
