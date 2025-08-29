from werkzeug.security import generate_password_hash, check_password_hash
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

# Initialize extensions without app; configured in app.py

db = SQLAlchemy()
migrate = Migrate()


def dom_now():
    """Return current datetime in Dominican Republic timezone (naive)."""
    return datetime.now(ZoneInfo("America/Santo_Domingo")).replace(tzinfo=None)

class Client(db.Model):
    __table_args__ = (
        db.UniqueConstraint('identifier', 'company_id', name='uq_client_identifier_company'),
        db.UniqueConstraint('email', 'company_id', name='uq_client_email_company'),
    )
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
    stock = db.Column(db.Integer, default=0)
    min_stock = db.Column(db.Integer, default=0)
    company_id = db.Column(db.Integer, db.ForeignKey('company_info.id'), nullable=False)

    @property
    def needs_restock(self) -> bool:
        """Return True if product stock is at or below its minimum level."""
        return self.stock <= self.min_stock

class Quotation(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    client_id = db.Column(db.Integer, db.ForeignKey('client.id'), nullable=False)
    date = db.Column(db.DateTime, default=dom_now)
    valid_until = db.Column(db.DateTime, nullable=False)
    subtotal = db.Column(db.Float, nullable=False)
    itbis = db.Column(db.Float, nullable=False)
    total = db.Column(db.Float, nullable=False)
    seller = db.Column(db.String(120))
    payment_method = db.Column(db.String(20))
    bank = db.Column(db.String(50))
    note = db.Column(db.Text)
    status = db.Column(db.String(20), default='vigente')
    company_id = db.Column(db.Integer, db.ForeignKey('company_info.id'), nullable=False)
    warehouse_id = db.Column(db.Integer, db.ForeignKey('warehouse.id'))

    client = db.relationship('Client')
    items = db.relationship('QuotationItem', cascade='all, delete-orphan')
    warehouse = db.relationship('Warehouse')

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
    customer_po = db.Column(db.String(120))
    warehouse_id = db.Column(db.Integer, db.ForeignKey('warehouse.id'))
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
    warehouse_id = db.Column(db.Integer, db.ForeignKey('warehouse.id'))
    company_id = db.Column(db.Integer, db.ForeignKey('company_info.id'), nullable=False)

    client = db.relationship('Client')
    order = db.relationship('Order')
    items = db.relationship('InvoiceItem', cascade='all, delete-orphan')
    payments = db.relationship('Payment', cascade='all, delete-orphan', back_populates='invoice')

class Payment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    invoice_id = db.Column(db.Integer, db.ForeignKey('invoice.id'), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    date = db.Column(db.DateTime, default=dom_now)
    company_id = db.Column(db.Integer, db.ForeignKey('company_info.id'), nullable=False)
    invoice = db.relationship('Invoice', back_populates='payments')

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


class InventoryMovement(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    product_id = db.Column(db.Integer, db.ForeignKey('product.id'), nullable=False)
    quantity = db.Column(db.Integer, nullable=False)
    movement_type = db.Column(db.String(10), nullable=False)  # entrada o salida
    reference_type = db.Column(db.String(20))
    reference_id = db.Column(db.Integer)
    timestamp = db.Column(db.DateTime, default=dom_now)
    warehouse_id = db.Column(db.Integer, db.ForeignKey('warehouse.id'))
    company_id = db.Column(db.Integer, db.ForeignKey('company_info.id'), nullable=False)
    executed_by = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    product = db.relationship('Product')
    warehouse = db.relationship('Warehouse')
    user = db.relationship('User')


class Warehouse(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    address = db.Column(db.String(200))
    company_id = db.Column(db.Integer, db.ForeignKey('company_info.id'), nullable=False)
    stocks = db.relationship('ProductStock', cascade='all, delete-orphan')


class ProductStock(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    product_id = db.Column(db.Integer, db.ForeignKey('product.id'), nullable=False)
    warehouse_id = db.Column(db.Integer, db.ForeignKey('warehouse.id'), nullable=False)
    stock = db.Column(db.Integer, default=0)
    min_stock = db.Column(db.Integer, default=0)
    company_id = db.Column(db.Integer, db.ForeignKey('company_info.id'), nullable=False)
    __table_args__ = (db.UniqueConstraint('product_id', 'warehouse_id', name='uix_product_wh'),)
    product = db.relationship('Product')


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
    email = db.Column(db.String(120))
    first_name = db.Column(db.String(120), nullable=False, default='')
    last_name = db.Column(db.String(120), nullable=False, default='')
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
    accepted_terms = db.Column(db.Boolean, nullable=False, default=False)
    accepted_terms_at = db.Column(db.DateTime)
    accepted_terms_ip = db.Column(db.String(45))
    accepted_terms_user_agent = db.Column(db.String(255))


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


class Notification(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    company_id = db.Column(db.Integer, db.ForeignKey('company_info.id'), nullable=False)
    message = db.Column(db.String(200), nullable=False)
    is_read = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=dom_now)
