import os
import sys
import csv
import pytest
from io import BytesIO

sys.path.append(os.path.dirname(os.path.dirname(__file__)))
from app import app, db
from models import CompanyInfo, User, Product, InventoryMovement


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
        db.session.commit()
    with app.test_client() as c:
        # login session
        c.post('/login', data={'username': 'user', 'password': 'pass'})
        yield c
    with app.app_context():
        db.drop_all()
    if db_path.exists():
        db_path.unlink()


def test_inventory_adjust_entry(client):
    resp = client.post('/inventario/ajustar', data={
        'product_id': '1',
        'quantity': '5',
        'movement_type': 'entrada'
    }, follow_redirects=True)
    assert resp.status_code == 200
    with app.app_context():
        prod = Product.query.get(1)
        assert prod.stock == 10
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
        prod = Product.query.get(1)
        prod.stock = 2
        db.session.commit()
    resp = client.get('/cotizaciones')
    assert b'stock bajo' in resp.data
