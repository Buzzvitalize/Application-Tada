import time, os, sys
sys.path.append(os.getcwd())
from app import app, db, Invoice, InvoiceItem, Client, Product, ExportLog
from models import CompanyInfo

def setup_module(module):
    app.config.from_object('config.TestingConfig')
    with app.app_context():
        db.drop_all(); db.create_all()
        company = CompanyInfo(name='C', street='s', sector='s', province='p', phone='1', rnc='1')
        db.session.add(company); db.session.commit()
        prod = Product(code='P', name='Prod', unit='Unidad', price=10, category='Servicios', company_id=company.id)
        client = Client(name='A', company_id=company.id)
        db.session.add_all([prod, client]); db.session.commit()
        for i in range(10000):
            inv = Invoice(
                client_id=client.id,
                order_id=1,
                subtotal=10,
                itbis=1.8,
                total=11.8,
                invoice_type='Consumidor Final',
                status='Pagada',
                company_id=company.id,
            )
            db.session.add(inv)
            db.session.flush()
            db.session.add(InvoiceItem(invoice_id=inv.id, product_name='Prod', unit='Unidad', unit_price=10, quantity=1, company_id=company.id))
        db.session.commit()
        db.session.remove()


def test_export_limit_logs_failure():
        with app.test_client() as c:
            with c.session_transaction() as sess:
                sess['role']='admin'; sess['company_id']=1; sess['username']='u'; sess['user_id']=1
        resp = c.get('/reportes/export?formato=csv&tipo=detalle&async=0')
        assert resp.status_code==200
        # limit check
        app.config['MAX_EXPORT_ROWS']=1
        resp = c.get('/reportes/export?formato=csv&tipo=detalle')
        assert resp.status_code==400
        with app.app_context():
            assert ExportLog.query.filter_by(status='fail').first() is not None


def test_export_async_job():
        with app.test_client() as c:
            with c.session_transaction() as sess:
                sess['role']='admin'; sess['company_id']=1; sess['username']='u'; sess['user_id']=1
        app.config['MAX_EXPORT_ROWS']=1
        resp = c.get('/reportes/export?formato=csv&tipo=detalle&async=1')
        assert resp.status_code==200
        job_id = resp.get_json()['job']
        # wait for background thread
        time.sleep(1)
        with app.app_context():
            log = ExportLog.query.get(job_id)
            assert log.status in ('queued','success')


def test_report_performance():
        with app.test_client() as c:
            with c.session_transaction() as sess:
                sess['role']='admin'; sess['company_id']=1; sess['username']='admin'; sess['user_id']=1
        start=time.time()
        resp=c.get('/reportes?ajax=1')
        duration=time.time()-start
        assert resp.status_code==200
        assert duration < 3
