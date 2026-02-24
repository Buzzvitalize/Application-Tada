import os
import sys
import time
import uuid
import pytest

sys.path.append(os.path.dirname(os.path.dirname(__file__)))
from app import app, db
from models import User, CompanyInfo
from auth import generate_reset_token, verify_reset_token, reset_password


@pytest.fixture
def setup_db(tmp_path):
    db_path = tmp_path / "test.sqlite"
    app.config.from_object('config.TestingConfig')
    app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{db_path}'
    with app.app_context():
        db.create_all()
        company = CompanyInfo(name='Comp', street='', sector='', province='', phone='', rnc='')
        db.session.add(company)
        db.session.flush()
        username = f"tok_{uuid.uuid4().hex}"
        user = User(username=username, first_name='T', last_name='Ok', role='company', company_id=company.id)
        user.set_password('old')
        db.session.add(user)
        db.session.commit()
    yield username
    with app.app_context():
        db.drop_all()
    if db_path.exists():
        db_path.unlink()


def test_token_single_use_and_expiry(setup_db):
    username = setup_db
    with app.app_context():
        user = User.query.filter_by(username=username).first()
        token = generate_reset_token(user)
    # first use resets password
    with app.test_request_context(f'/reset/{token}', method='POST', data={'password': 'new'}):
        reset_password(token)
    with app.app_context():
        user = User.query.filter_by(username=username).first()
        assert user.check_password('new')
    # second use should be rejected and not change password
    with app.test_request_context(f'/reset/{token}', method='POST', data={'password': 'again'}):
        reset_password(token)
    with app.app_context():
        user = User.query.filter_by(username=username).first()
        assert user.check_password('new')
        token2 = generate_reset_token(user)
    time.sleep(2)
    with app.app_context():
        assert verify_reset_token(token2, max_age=1) is None
