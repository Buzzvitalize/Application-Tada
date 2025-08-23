from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

# Initialize SQLAlchemy without app; will be initialized in app.py

db = SQLAlchemy()

class Client(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    identifier = db.Column(db.String(50))
    phone = db.Column(db.String(50), nullable=False)
    email = db.Column(db.String(120))
    street = db.Column(db.String(120), nullable=False)
    sector = db.Column(db.String(120), nullable=False)
    province = db.Column(db.String(120), nullable=False)
    is_final_consumer = db.Column(db.Boolean, default=True)
    company_id = db.Column(db.Integer, db.ForeignKey('company_info.id'), nullable=False)

class Product(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    unit = db.Column(db.String(20), nullable=False)
    price = db.Column(db.Float, nullable=False)
    category = db.Column(db.String(50))
    has_itbis = db.Column(db.Boolean, default=True)
    company_id = db.Column(db.Integer, db.ForeignKey('company_info.id'), nullable=False)

class Quotation(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    client_id = db.Column(db.Integer, db.ForeignKey('client.id'), nullable=False)
    date = db.Column(db.DateTime, default=datetime.utcnow)
    subtotal = db.Column(db.Float, nullable=False)
    itbis = db.Column(db.Float, nullable=False)
    total = db.Column(db.Float, nullable=False)
    company_id = db.Column(db.Integer, db.ForeignKey('company_info.id'), nullable=False)

    client = db.relationship('Client')
    items = db.relationship('QuotationItem', cascade='all, delete-orphan')

class QuotationItem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    quotation_id = db.Column(db.Integer, db.ForeignKey('quotation.id'), nullable=False)
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
    date = db.Column(db.DateTime, default=datetime.utcnow)
    status = db.Column(db.String(20), default='Pendiente')
    delivery_date = db.Column(db.DateTime)
    subtotal = db.Column(db.Float, nullable=False)
    itbis = db.Column(db.Float, nullable=False)
    total = db.Column(db.Float, nullable=False)
    company_id = db.Column(db.Integer, db.ForeignKey('company_info.id'), nullable=False)

    client = db.relationship('Client')
    items = db.relationship('OrderItem', cascade='all, delete-orphan')

class OrderItem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey('order.id'), nullable=False)
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
    date = db.Column(db.DateTime, default=datetime.utcnow)
    subtotal = db.Column(db.Float, nullable=False)
    itbis = db.Column(db.Float, nullable=False)
    total = db.Column(db.Float, nullable=False)
    ncf = db.Column(db.String(20), unique=True)
    company_id = db.Column(db.Integer, db.ForeignKey('company_info.id'), nullable=False)

    client = db.relationship('Client')
    items = db.relationship('InvoiceItem', cascade='all, delete-orphan')

class InvoiceItem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    invoice_id = db.Column(db.Integer, db.ForeignKey('invoice.id'), nullable=False)
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
    password = db.Column(db.String(120), nullable=False)
    role = db.Column(db.String(20), default='company')  # 'admin' or 'company'
    company_id = db.Column(db.Integer, db.ForeignKey('company_info.id'))


class AccountRequest(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    first_name = db.Column(db.String(120), nullable=False)
    last_name = db.Column(db.String(120), nullable=False)
    company = db.Column(db.String(120), nullable=False)
    rnc = db.Column(db.String(50))
    phone = db.Column(db.String(50), nullable=False)
    email = db.Column(db.String(120), nullable=False)
    address = db.Column(db.String(200), nullable=False)
    website = db.Column(db.String(120))
    username = db.Column(db.String(80), unique=True, nullable=False)
    password = db.Column(db.String(120), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
