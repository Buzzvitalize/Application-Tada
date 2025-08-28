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

def test_clientes(client):
    assert client.get('/clientes/').status_code == 200

def test_productos(client):
    assert client.get('/productos/').status_code == 200

def test_cotizaciones(client):
    assert client.get('/cotizaciones/').status_code == 200

def test_facturas(client):
    assert client.get('/facturas/').status_code == 200

def test_reportes(client):
    assert client.get('/reportes/').status_code == 200

def test_auth(client):
    assert client.get('/login').status_code == 200


def test_misc_pages(client):
    for url in ['/solicitar', '/cpanel', '/pedido', '/pedidos', '/ajustes', '/adjustes', '/notificaciones', '/inventario', '/contabilidad']:
        assert client.get(url).status_code == 200
