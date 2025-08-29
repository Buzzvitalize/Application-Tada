import os
import sys
import pytest

try:  # Skip entire module if plugin unavailable
    import pytest_benchmark  # noqa: F401
except Exception:  # pragma: no cover
    pytest.skip("pytest-benchmark not installed", allow_module_level=True)

sys.path.append(os.path.dirname(os.path.dirname(__file__)))
from app import app, db
from models import Invoice
from scripts.seed_invoices import seed_invoices

@pytest.fixture(scope='module')
def perf_app(tmp_path_factory):
    db_path = tmp_path_factory.mktemp('perf') / 'perf.sqlite'
    app.config.from_object('config.TestingConfig')
    app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{db_path}'
    with app.app_context():
        db.create_all()
        seed_invoices(10000)
    yield app
    with app.app_context():
        db.drop_all()


@pytest.mark.parametrize('limit,threshold', [(10000, 3.0)])
def test_report_query(perf_app, benchmark, limit, threshold):
    with perf_app.app_context():
        def run_query():
            return list(Invoice.query.limit(limit).all())
        benchmark(run_query)
        assert benchmark.stats['mean'] < threshold
