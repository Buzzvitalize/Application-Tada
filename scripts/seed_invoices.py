from __future__ import annotations
import random
from datetime import datetime
from faker import Faker
from app import app, db, Invoice, InvoiceItem, Client, Product
from models import CompanyInfo

fake = Faker()


def seed_invoices(n: int = 100_000) -> None:
    """Seed the database with ``n`` invoices for stress tests."""
    with app.app_context():
        db.create_all()
        company = CompanyInfo.query.first()
        if not company:
            company = CompanyInfo(name='DemoCo', street='-', sector='-', province='-', phone='-', rnc='-')
            db.session.add(company)
            db.session.commit()
        # ensure some products
        products = Product.query.filter_by(company_id=company.id).all()
        if not products:
            for i in range(10):
                p = Product(code=f'P{i}', name=fake.word(), unit='Unidad', price=random.uniform(5, 100),
                            category='Servicios', company_id=company.id)
                db.session.add(p)
            db.session.commit()
            products = Product.query.filter_by(company_id=company.id).all()
        # create clients
        clients = Client.query.filter_by(company_id=company.id).all()
        if not clients:
            clients = [Client(name=fake.name(), company_id=company.id) for _ in range(100)]
            db.session.add_all(clients)
            db.session.commit()
        for _ in range(n):
            client = random.choice(clients)
            inv = Invoice(client_id=client.id, order_id=1, subtotal=0, itbis=0, total=0,
                          invoice_type='Pagada', company_id=company.id,
                          date=fake.date_time_between(start_date='-2y', end_date='now'))
            db.session.add(inv)
            db.session.flush()
            total = 0
            for _ in range(random.randint(1, 4)):
                prod = random.choice(products)
                qty = random.randint(1, 5)
                line_total = prod.price * qty
                total += line_total
                db.session.add(InvoiceItem(invoice_id=inv.id, code=prod.code, product_name=prod.name,
                                            unit=prod.unit, unit_price=prod.price, quantity=qty,
                                            category=prod.category, company_id=company.id))
            inv.subtotal = total
            inv.itbis = round(total * 0.18, 2)
            inv.total = inv.subtotal + inv.itbis
        db.session.commit()
        print(f"Seeded {n} invoices")


if __name__ == '__main__':
    seed_invoices()
