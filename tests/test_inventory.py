import os
import os
import sys
import csv
import pytest
from io import BytesIO

sys.path.append(os.path.dirname(os.path.dirname(__file__)))
from app import app, db, notify
from models import CompanyInfo, User, Product, ProductPriceLog, InventoryMovement, Warehouse, ProductStock, Notification


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
        user = User(username='mgr', first_name='M', last_name='Gr', role='manager', company_id=comp.id)
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
        'file': (BytesIO(data.encode('utf-8')), 's.csv'),
        'warehouse_id': '1'
    }, follow_redirects=True)
    assert resp.status_code == 200
    with app.app_context():
        prod = Product.query.get(1)
        ps = ProductStock.query.filter_by(product_id=1, warehouse_id=1).first()
        assert prod.stock == 20
        assert ps.stock == 20
        assert ps.min_stock == 8
        assert InventoryMovement.query.count() == 1


def test_inventory_import_invalid_header(client):
    data = 'code,stock\nP1,10\n'
    resp = client.post('/inventario/importar', data={
        'file': (BytesIO(data.encode('utf-8')), 's.csv'),
        'warehouse_id': '1'
    }, follow_redirects=True)
    assert 'Cabeceras inválidas' in resp.get_data(as_text=True)
    with app.app_context():
        prod = Product.query.get(1)
        assert prod.stock == 5
        assert InventoryMovement.query.count() == 0


def test_inventory_import_invalid_row(client):
    data = 'code,stock,min_stock\nP1,abc,8\n'
    resp = client.post('/inventario/importar', data={
        'file': (BytesIO(data.encode('utf-8')), 's.csv'),
        'warehouse_id': '1'
    }, follow_redirects=True)
    assert 'Importación cancelada' in resp.get_data(as_text=True)
    with app.app_context():
        prod = Product.query.get(1)
        assert prod.stock == 5
        assert InventoryMovement.query.count() == 0


def test_low_stock_alert(client):
    with app.app_context():
        ps = ProductStock.query.filter_by(product_id=1, warehouse_id=1).first()
        ps.stock = 2
        db.session.commit()
        notify(f'Stock bajo: {ps.product.name}')
    resp = client.get('/notificaciones')
    assert b'Stock bajo' in resp.data


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
    data = 'code,name,unit,price,category,has_itbis\nP2,Prod2,Unidad,12.5,Alimentos y Bebidas,1\n'
    resp = manager_client.post('/productos/importar', data={'file': (BytesIO(data.encode('utf-8')), 'p.csv')}, follow_redirects=True)
    assert resp.status_code == 200
    with app.app_context():
        p = Product.query.filter_by(code='P2').first()
        assert p is not None
        assert p.name == 'Prod2'
        assert p.unit == 'Unidad'
        assert p.category == 'Alimentos y Bebidas'
        assert p.reference == 'PRO001'
        assert p.has_itbis is True


def test_products_export_csv(client):
    resp = client.get('/productos/export')
    body = resp.get_data(as_text=True)
    assert resp.status_code == 200
    assert resp.headers['Content-Type'].startswith('text/csv')
    assert 'attachment; filename=productos.csv' in resp.headers.get('Content-Disposition', '')
    assert 'code,reference,name,unit,price,cost_price,category,has_itbis' in body
    assert 'P1' in body


def test_create_product_with_cost_and_margin_inputs(client):
    resp = client.post(
        '/productos',
        data={
            'name': 'Prod Costo',
            'unit': 'Unidad',
            'code': 'PC1',
            'reference': 'PRO999',
            'price': '400',
            'use_cost': 'on',
            'cost_price': '200',
            'category': 'Alimentos y Bebidas',
            'has_itbis': 'on',
        },
        follow_redirects=True,
    )
    assert resp.status_code == 200
    with app.app_context():
        prod = Product.query.filter_by(code='PC1').first()
        assert prod is not None
        assert prod.cost_price == 200


def test_create_product_rejects_non_positive_cost(client):
    resp = client.post(
        '/productos',
        data={
            'name': 'Prod Invalido',
            'unit': 'Unidad',
            'code': 'PC_BAD',
            'reference': 'PRO998',
            'price': '400',
            'use_cost': 'on',
            'cost_price': '0',
            'category': 'Alimentos y Bebidas',
            'has_itbis': 'on',
        },
        follow_redirects=True,
    )
    body = resp.get_data(as_text=True)
    assert resp.status_code == 200
    assert 'No se pudo guardar el producto: costo inválido' in body
    with app.app_context():
        assert Product.query.filter_by(code='PC_BAD').first() is None


def test_create_product_warns_when_price_below_cost(client):
    resp = client.post(
        '/productos',
        data={
            'name': 'Prod Margen Neg',
            'unit': 'Unidad',
            'code': 'PC_NEG',
            'reference': 'PRO997',
            'price': '100',
            'use_cost': 'on',
            'cost_price': '200',
            'category': 'Alimentos y Bebidas',
            'has_itbis': 'on',
        },
        follow_redirects=True,
    )
    body = resp.get_data(as_text=True)
    assert resp.status_code == 200
    assert 'Advertencia: el precio de venta está por debajo del costo' in body
    with app.app_context():
        prod = Product.query.filter_by(code='PC_NEG').first()
        assert prod is not None
        assert prod.cost_price == 200


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


def test_inventory_movement_tracks_user(client):
    client.post(
        '/inventario/ajustar',
        data={
            'product_id': '1',
            'warehouse_id': '1',
            'quantity': '2',
            'movement_type': 'entrada',
        },
        follow_redirects=True,
    )
    with app.app_context():
        mov = InventoryMovement.query.first()
        assert mov.executed_by == 1
        assert mov.user.username == 'user'


def test_product_price_log_created_on_create(client):
    client.post(
        '/productos',
        data={
            'name': 'Prod Log',
            'unit': 'Unidad',
            'code': 'PLOG1',
            'reference': 'PRO321',
            'price': '350',
            'use_cost': 'on',
            'cost_price': '175',
            'category': 'Alimentos y Bebidas',
            'has_itbis': 'on',
        },
        follow_redirects=True,
    )
    with app.app_context():
        product = Product.query.filter_by(code='PLOG1').first()
        log = ProductPriceLog.query.filter_by(product_id=product.id).order_by(ProductPriceLog.id.desc()).first()
        assert log is not None
        assert log.old_price is None
        assert log.new_price == 350
        assert log.new_cost_price == 175


def test_product_price_log_created_on_edit_when_price_or_cost_changes(client):
    with app.app_context():
        product = Product.query.filter_by(code='P1').first()
        pid = product.id

    client.post(
        f'/productos/edit/{pid}',
        data={
            'name': 'Prod',
            'unit': 'u',
            'code': 'P1',
            'reference': 'PRO001',
            'price': '20',
            'use_cost': 'on',
            'cost_price': '10',
            'category': 'Alimentos y Bebidas',
            'has_itbis': 'on',
        },
        follow_redirects=True,
    )

    with app.app_context():
        log = ProductPriceLog.query.filter_by(product_id=pid).order_by(ProductPriceLog.id.desc()).first()
        assert log is not None
        assert log.old_price == 10
        assert log.new_price == 20
        assert log.old_cost_price is None
        assert log.new_cost_price == 10


def test_price_history_view_lists_logs(client):
    client.post(
        '/productos',
        data={
            'name': 'Prod Log View',
            'unit': 'Unidad',
            'code': 'PLOGV',
            'reference': 'PRO322',
            'price': '250',
            'use_cost': 'on',
            'cost_price': '125',
            'category': 'Alimentos y Bebidas',
            'has_itbis': 'on',
        },
        follow_redirects=True,
    )
    resp = client.get('/productos/historial-precios')
    body = resp.get_data(as_text=True)
    assert resp.status_code == 200
    assert 'Historial de precios' in body
    assert 'Prod Log View' in body
