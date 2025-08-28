import os, sys, pytest, importlib
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
create_app = importlib.import_module('app.__init__').create_app

@pytest.fixture
def client():
    app = create_app()
    app.config['TESTING'] = True
    from app.models import db
    with app.app_context():
        db.create_all()
    with app.test_client() as client:
        yield client

def test_index_pages(client):
    for url in ['/cotizaciones/', '/pedidos/', '/facturas/', '/clientes/', '/productos/', '/inventario/', '/reportes/', '/contabilidad/']:
        assert client.get(url).status_code == 200

def test_auth(client):
    assert client.get('/auth/').status_code == 200

def test_menu_has_links(client):
    with client.session_transaction() as sess:
        sess['role']='admin'
    res = client.get('/clientes/')
    page = res.get_data(as_text=True)
    for text in ['Cotizaciones','Pedidos','Facturas','Clientes','Productos','Inventario','Reportes','Contabilidad','CPanel','Ajustes']:
        assert text in page


def test_product_form_choices(client):
    res = client.get('/productos/nuevo')
    page = res.get_data(as_text=True)
    assert 'Servicios' in page and 'Consumo' in page
    for unit in ['Unidad','Metro','Onza','Libra']:
        assert unit in page
