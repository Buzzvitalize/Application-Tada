import os, sys, re
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from app import create_app
from app.models import db, CompanyInfo, Client
from app.forms import ClientForm

def setup_app():
    app = create_app()
    app.config.update(TESTING=True)
    app.add_url_rule('/q', 'list_quotations', lambda: '')
    with app.app_context():
        db.drop_all()
        db.create_all()
        db.session.add(CompanyInfo(name='Comp', street='s', sector='sec', province='prov', phone='1', rnc='1'))
        db.session.commit()
    return app

def test_client_form_validation():
    app = setup_app()
    with app.test_request_context('/', method='POST', data={'name': 'Juan', 'email': 'a@b.com'}):
        form = ClientForm()
        assert form.validate()
    with app.test_request_context('/', method='POST', data={'name': '', 'email': 'bad'}):
        form = ClientForm()
        assert not form.validate()

def test_csrf_protection():
    app = setup_app()
    client = app.test_client()
    with client.session_transaction() as sess:
        sess['csrf_token'] = 'stub-token'
    resp = client.post('/clientes/nuevo', data={'name': 'Ana', 'csrf_token': 'stub-token'})
    assert resp.status_code == 302
    resp = client.post('/clientes/nuevo', data={'name': 'Ana'})
    assert resp.status_code == 400
    with app.app_context():
        assert Client.query.count() == 1
