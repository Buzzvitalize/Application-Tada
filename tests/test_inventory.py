import os
import os
import sys
import csv
import pytest
from io import BytesIO

sys.path.append(os.path.dirname(os.path.dirname(__file__)))
from app import app, db
from models import CompanyInfo, User, Product, InventoryMovement, Warehouse, ProductStock


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
        user = User(username='user', role='company', company_id=comp.id)
        user.set_password('pass')
        db.session.add(user)
        prod = Product(code='P1', name='Prod', unit='u', price=10, stock=5, min_stock=3, company_id=comp.id)
        db.session.add(prod)
        w1 = Warehouse(name='W1', company_id=comp.id)
        w2 = Warehouse(name='W2', company_id=comp.id)
        db.session.add_all([w1, w2])
        db.session.flush()
        ps = ProductStock(product_id=prod.id, warehouse_id=w1.id, stock=5, min_stock=3, company_id=comp.id)
        db.session.add(ps)
        db.session.commit()
    with app.test_client() as c:
        # login session
        c.post('/login', data={'username': 'user', 'password': 'pass'})
        yield c
    with app.app_context():
        db.drop_all()
    if db_path.exists():
        db_path.unlink()


@pytest.fixture
def manager_client(tmp_path):
    db_path = tmp_path / "test.sqlite"
    app.config.from_object('config.TestingConfig')
    app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{db_path}'
    with app.app_context():
        db.create_all()
        comp = CompanyInfo(name='Comp', street='', sector='', province='', phone='', rnc='')
        db.session.add(comp)
        db.session.flush()
        user = User(username='mgr', role='manager', company_id=comp.id)
        user.set_password('pass')
        db.session.add(user)
        db.session.commit()
    with app.test_client() as c:
        c.post('/login', data={'username': 'mgr', 'password': 'pass'})
        yield c
    with app.app_context():
        db.drop_all()
    if db_path.exists():
        db_path.unlink()


def test_inventory_adjust_entry(client):
    resp = client.post('/inventario/ajustar', data={
        'product_id': '1',
        'warehouse_id': '1',
        'quantity': '5',
        'movement_type': 'entrada'
    }, follow_redirects=True)
    assert resp.status_code == 200
    with app.app_context():
        prod = Product.query.get(1)
        assert prod.stock == 10
        ps = ProductStock.query.filter_by(product_id=1, warehouse_id=1).first()
        assert ps.stock == 10
        assert InventoryMovement.query.count() == 1


def test_inventory_import_csv(client):
    data = 'code,stock,min_stock\nP1,20,8\n'
    resp = client.post('/inventario/importar', data={
        'file': (BytesIO(data.encode('utf-8')), 's.csv')
    }, follow_redirects=True)
    assert resp.status_code == 200
    with app.app_context():
        prod = Product.query.get(1)
        assert prod.stock == 20
        assert prod.min_stock == 8
        assert InventoryMovement.query.count() == 1


def test_low_stock_alert(client):
    with app.app_context():
        ps = ProductStock.query.filter_by(product_id=1, warehouse_id=1).first()
        ps.stock = 2
        db.session.commit()
    resp = client.get('/cotizaciones')
    assert b'stock bajo' in resp.data


def test_update_min_stock(client):
    resp = client.post('/inventario/1/minimo', data={'min_stock': '7'}, follow_redirects=True)
    assert resp.status_code == 200
    with app.app_context():
        ps = ProductStock.query.get(1)
        assert ps.min_stock == 7


def test_transfer_between_warehouses(client):
    resp = client.post('/inventario/transferir', data={
        'product_id': '1',
        'origin_id': '1',
        'dest_id': '2',
        'quantity': '3'
    }, follow_redirects=True)
    assert resp.status_code == 200
    with app.app_context():
        o = ProductStock.query.filter_by(product_id=1, warehouse_id=1).first()
        d = ProductStock.query.filter_by(product_id=1, warehouse_id=2).first()
        assert o.stock == 2
        assert d.stock == 3
        assert InventoryMovement.query.filter_by(reference_type='transfer').count() == 2


def test_product_import_csv(manager_client):
    data = 'code,name,unit,price,category,has_itbis\nP2,Prod2,Unidad,12.5,Servicios,1\n'
    resp = manager_client.post('/productos/importar', data={'file': (BytesIO(data.encode('utf-8')), 'p.csv')}, follow_redirects=True)
    assert resp.status_code == 200
    with app.app_context():
        p = Product.query.filter_by(code='P2').first()
        assert p is not None
        assert p.name == 'Prod2'
        assert p.unit == 'Unidad'
        assert p.category == 'Servicios'
        assert p.has_itbis is True


def test_company_cannot_create_warehouse(client):
    resp = client.post('/almacenes', data={'name': 'New'}, follow_redirects=True)
    assert b'Acceso restringido' in resp.data
    with app.app_context():
        assert Warehouse.query.filter_by(name='New').first() is None


def test_manager_create_delete_warehouse(manager_client):
    resp = manager_client.post('/almacenes', data={'name': 'Auth'}, follow_redirects=True)
    assert resp.status_code == 200
    with app.app_context():
        w = Warehouse.query.filter_by(name='Auth').first()
        assert w is not None
        wid = w.id
    manager_client.post(f'/almacenes/{wid}/delete', follow_redirects=True)
    with app.app_context():
        assert Warehouse.query.get(wid) is None
