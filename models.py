from werkzeug.security import generate_password_hash, check_password_hash
from flask_sqlalchemy import SQLAlchemy
try:
    from flask_migrate import Migrate
except ModuleNotFoundError:  # pragma: no cover
    class Migrate:
        def __init__(self, *a, **k):
            pass
        def init_app(self, *a, **k):
            pass
from datetime import datetime
from zoneinfo import ZoneInfo

# Initialize extensions without app; configured in app.py

db = SQLAlchemy()
migrate = Migrate()


def dom_now():
    """Return current datetime in Dominican Republic timezone (naive)."""
    return datetime.now(ZoneInfo("America/Santo_Domingo")).replace(tzinfo=None)

class Client(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    last_name = db.Column(db.String(120))
    identifier = db.Column(db.String(50))
    phone = db.Column(db.String(50))
    email = db.Column(db.String(120))
    street = db.Column(db.String(120))
    sector = db.Column(db.String(120))
    province = db.Column(db.String(120))
    is_final_consumer = db.Column(db.Boolean, default=True)
    company_id = db.Column(db.Integer, db.ForeignKey('company_info.id'), nullable=False)

class Product(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(50), unique=True, nullable=False)
    reference = db.Column(db.String(50))
    name = db.Column(db.String(120), nullable=False)
    unit = db.Column(db.String(20), nullable=False)
    price = db.Column(db.Float, nullable=False)
    category = db.Column(db.String(50))
    has_itbis = db.Column(db.Boolean, default=True)
    company_id = db.Column(db.Integer, db.ForeignKey('company_info.id'), nullable=False)

class Quotation(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    client_id = db.Column(db.Integer, db.ForeignKey('client.id'), nullable=False)
    date = db.Column(db.DateTime, default=dom_now)
    subtotal = db.Column(db.Float, nullable=False)
    itbis = db.Column(db.Float, nullable=False)
    total = db.Column(db.Float, nullable=False)
    seller = db.Column(db.String(120))
    payment_method = db.Column(db.String(20))
    bank = db.Column(db.String(50))
    note = db.Column(db.Text)
    company_id = db.Column(db.Integer, db.ForeignKey('company_info.id'), nullable=False)

    client = db.relationship('Client')
    items = db.relationship('QuotationItem', cascade='all, delete-orphan')

class QuotationItem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    quotation_id = db.Column(db.Integer, db.ForeignKey('quotation.id'), nullable=False)
    code = db.Column(db.String(50))
    reference = db.Column(db.String(50))
    product_name = db.Column(db.String(120), nullable=False)
    unit = db.Column(db.String(20), nullable=False)
    unit_price = db.Column(db.Float, nullable=False)
    quantity = db.Column(db.Integer, nullable=False)
    discount = db.Column(db.Float, default=0.0)
    category = db.Column(db.String(50))
    has_itbis = db.Column(db.Boolean, default=True)
    company_id = db.Column(db.Integer, db.ForeignKey('company_info.id'), nullable=False)

class Order(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    client_id = db.Column(db.Integer, db.ForeignKey('client.id'), nullable=False)
    quotation_id = db.Column(db.Integer, db.ForeignKey('quotation.id'))
    date = db.Column(db.DateTime, default=dom_now)
    status = db.Column(db.String(20), default='Pendiente')
    delivery_date = db.Column(db.DateTime)
    subtotal = db.Column(db.Float, nullable=False)
    itbis = db.Column(db.Float, nullable=False)
    total = db.Column(db.Float, nullable=False)
    seller = db.Column(db.String(120))
    payment_method = db.Column(db.String(20))
    bank = db.Column(db.String(50))
    note = db.Column(db.Text)
    company_id = db.Column(db.Integer, db.ForeignKey('company_info.id'), nullable=False)

    client = db.relationship('Client')
    items = db.relationship('OrderItem', cascade='all, delete-orphan')

class OrderItem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey('order.id'), nullable=False)
    code = db.Column(db.String(50))
    reference = db.Column(db.String(50))
    product_name = db.Column(db.String(120), nullable=False)
    unit = db.Column(db.String(20), nullable=False)
    unit_price = db.Column(db.Float, nullable=False)
    quantity = db.Column(db.Integer, nullable=False)
    discount = db.Column(db.Float, default=0.0)
    category = db.Column(db.String(50))
    has_itbis = db.Column(db.Boolean, default=True)
    company_id = db.Column(db.Integer, db.ForeignKey('company_info.id'), nullable=False)

class Invoice(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    client_id = db.Column(db.Integer, db.ForeignKey('client.id'), nullable=False)
    order_id = db.Column(db.Integer, db.ForeignKey('order.id'), nullable=False)
    date = db.Column(db.DateTime, default=dom_now)
    subtotal = db.Column(db.Float, nullable=False)
    itbis = db.Column(db.Float, nullable=False)
    total = db.Column(db.Float, nullable=False)
    ncf = db.Column(db.String(20), unique=True)
    seller = db.Column(db.String(120))
    payment_method = db.Column(db.String(20))
    bank = db.Column(db.String(50))
    invoice_type = db.Column(db.String(20))
    status = db.Column(db.String(20), default='Pendiente')
    note = db.Column(db.Text)
    company_id = db.Column(db.Integer, db.ForeignKey('company_info.id'), nullable=False)

    client = db.relationship('Client')
    items = db.relationship('InvoiceItem', cascade='all, delete-orphan')

class InvoiceItem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    invoice_id = db.Column(db.Integer, db.ForeignKey('invoice.id'), nullable=False)
    code = db.Column(db.String(50))
    reference = db.Column(db.String(50))
    product_name = db.Column(db.String(120), nullable=False)
    unit = db.Column(db.String(20), nullable=False)
    unit_price = db.Column(db.Float, nullable=False)
    quantity = db.Column(db.Integer, nullable=False)
    discount = db.Column(db.Float, default=0.0)
    category = db.Column(db.String(50))
    has_itbis = db.Column(db.Boolean, default=True)
    company_id = db.Column(db.Integer, db.ForeignKey('company_info.id'), nullable=False)


class CompanyInfo(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    street = db.Column(db.String(120), nullable=False)
    sector = db.Column(db.String(120), nullable=False)
    province = db.Column(db.String(120), nullable=False)
    phone = db.Column(db.String(50), nullable=False)
    rnc = db.Column(db.String(50), nullable=False)
    website = db.Column(db.String(120))
    logo = db.Column(db.String(120))
    ncf_final = db.Column(db.Integer, default=1)
    ncf_fiscal = db.Column(db.Integer, default=1)


class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password = db.Column(db.String(128), nullable=False)
    role = db.Column(db.String(20), default='company')  # 'admin', 'manager' or 'company'
    company_id = db.Column(db.Integer, db.ForeignKey('company_info.id'))

    def set_password(self, password: str) -> None:
        self.password = generate_password_hash(password)

    def check_password(self, password: str) -> bool:
        return check_password_hash(self.password, password)


class AccountRequest(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    account_type = db.Column(db.String(20), nullable=False)  # personal o empresarial
    first_name = db.Column(db.String(120), nullable=False)
    last_name = db.Column(db.String(120), nullable=False)
    company = db.Column(db.String(120), nullable=False)
    identifier = db.Column(db.String(50), nullable=False)  # RNC o Cédula
    phone = db.Column(db.String(50), nullable=False)
    email = db.Column(db.String(120), nullable=False)
    address = db.Column(db.String(200))
    website = db.Column(db.String(120))
    username = db.Column(db.String(80), unique=True, nullable=False)
    password = db.Column(db.String(120), nullable=False)
    created_at = db.Column(db.DateTime, default=dom_now)


class ExportLog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user = db.Column(db.String(80))
    company_id = db.Column(db.Integer)
    formato = db.Column(db.String(10))
    tipo = db.Column(db.String(20))
    filtros = db.Column(db.Text)
    status = db.Column(db.String(20))  # queued, success, fail
    message = db.Column(db.Text)
    file_path = db.Column(db.String(200))
    created_at = db.Column(db.DateTime, default=dom_now)


class NcfLog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    company_id = db.Column(db.Integer, db.ForeignKey('company_info.id'), nullable=False)
    old_final = db.Column(db.Integer)
    old_fiscal = db.Column(db.Integer)
    new_final = db.Column(db.Integer)
    new_fiscal = db.Column(db.Integer)
    changed_by = db.Column(db.Integer, db.ForeignKey('user.id'))
    changed_at = db.Column(db.DateTime, default=dom_now)
