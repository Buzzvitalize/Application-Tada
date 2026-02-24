import os
import sys
import pytest

sys.path.append(os.path.dirname(os.path.dirname(__file__)))
from app import app, db
from models import CompanyInfo, User, Product, Warehouse, ProductStock


@pytest.fixture
def inv_client(tmp_path):
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
        wh = Warehouse(name='W1', company_id=comp.id)
        db.session.add(wh)
        db.session.flush()
        categories = ['Alimentos y Bebidas', 'Productos Industriales / Materiales']
        for i in range(60):
            prod = Product(
                code=f'P{i:03d}',
                name=f'Prod{i:03d}',
                unit='u',
                price=1,
                category=categories[i % 2],
                company_id=comp.id,
            )
            db.session.add(prod)
            db.session.flush()
            stock = 5
            min_stock = 2
            if i == 0:
                stock = 1
            elif i == 1:
                stock = 0
            ps = ProductStock(
                product_id=prod.id,
                warehouse_id=wh.id,
                stock=stock,
                min_stock=min_stock,
                company_id=comp.id,
            )
            db.session.add(ps)
        special = Product(code='SPC', name='Special', unit='u', price=1, category=categories[0], company_id=comp.id)
        db.session.add(special)
        db.session.flush()
        db.session.add(ProductStock(product_id=special.id, warehouse_id=wh.id, stock=5, min_stock=2, company_id=comp.id))
        db.session.commit()
    with app.test_client() as c:
        c.post('/login', data={'username': 'user', 'password': 'pass'})
        yield c
    with app.app_context():
        db.drop_all()
    if db_path.exists():
        db_path.unlink()


def test_inventory_pagination(inv_client):
    resp = inv_client.get('/inventario?warehouse_id=1&per_page=25')
    data = resp.get_data(as_text=True)
    assert 'Prod000' in data and 'Prod024' in data
    assert 'Prod025' not in data
    resp2 = inv_client.get('/inventario?warehouse_id=1&page=2&per_page=25')
    data2 = resp2.get_data(as_text=True)
    assert 'Prod025' in data2


def test_inventory_search_and_category(inv_client):
    resp = inv_client.get('/inventario?warehouse_id=1&q=Special')
    data = resp.get_data(as_text=True)
    assert 'Special' in data
    assert 'Prod000' not in data
    resp2 = inv_client.get('/inventario?warehouse_id=1&category=Alimentos+y+Bebidas')
    data2 = resp2.get_data(as_text=True)
    assert 'Prod000' in data2
    assert 'Prod001' not in data2


def test_inventory_status_filters(inv_client):
    resp_low = inv_client.get('/inventario?warehouse_id=1&status=low')
    assert b'Prod000' in resp_low.data and b'Prod001' not in resp_low.data
    resp_zero = inv_client.get('/inventario?warehouse_id=1&status=zero')
    assert b'Prod001' in resp_zero.data and b'Prod000' not in resp_zero.data
    resp_norm = inv_client.get('/inventario?warehouse_id=1&status=normal')
    assert b'Prod002' in resp_norm.data and b'Prod000' not in resp_norm.data
