from flask import Flask, render_template, request, redirect, url_for, send_file, flash
from models import db, Client, Product, Quotation, QuotationItem, Order, OrderItem, Invoice, InvoiceItem
from fpdf import FPDF
from io import BytesIO
from datetime import datetime
import os

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database.sqlite'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.secret_key = 'secret-key'

DB_PATH = os.path.join(os.path.dirname(__file__), 'database.sqlite')

# Initialize database
with app.app_context():
    db.init_app(app)
    db.create_all()
    # sample data
    if not Client.query.first():
        sample_client = Client(name='Juan Perez', identifier='001-0000000-1', phone='809-000-0000', email='juan@example.com')
        sample_product = Product(name='Producto Ejemplo', price=100.0)
        db.session.add_all([sample_client, sample_product])
        db.session.commit()

# Utility functions
ITBIS_RATE = 0.18

def _to_float(value):
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def _to_int(value):
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0


def calculate_totals(items):
    subtotal = sum((item['unit_price'] * item['quantity']) - item['discount'] for item in items)
    itbis = subtotal * ITBIS_RATE
    total = subtotal + itbis
    return subtotal, itbis, total


def generate_pdf(title, company, client, items, subtotal, itbis, total):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font('Helvetica', 'B', 16)
    pdf.cell(0, 10, company['name'], ln=1)
    pdf.set_font('Helvetica', '', 10)
    pdf.cell(0, 5, company['address'], ln=1)
    pdf.cell(0, 5, f"RNC: {company['rnc']} Tel: {company['phone']}", ln=1)
    pdf.ln(5)
    pdf.set_font('Helvetica', 'B', 14)
    pdf.cell(0, 10, title, ln=1, align='C')
    pdf.ln(5)
    pdf.set_font('Helvetica', '', 12)
    pdf.cell(0, 6, f"Cliente: {client.name}", ln=1)
    pdf.cell(0, 6, f"Cédula/RNC: {client.identifier}", ln=1)
    pdf.cell(0, 6, f"Teléfono: {client.phone}", ln=1)
    if client.email:
        pdf.cell(0, 6, f"Email: {client.email}", ln=1)
    pdf.ln(5)
    pdf.set_font('Helvetica', 'B', 12)
    pdf.cell(80, 8, 'Producto', border=1)
    pdf.cell(25, 8, 'Precio', border=1, align='R')
    pdf.cell(20, 8, 'Cant.', border=1, align='R')
    pdf.cell(25, 8, 'Desc.', border=1, align='R')
    pdf.cell(30, 8, 'Total', border=1, ln=1, align='R')
    pdf.set_font('Helvetica', '', 12)
    for i in items:
        total_line = (i.unit_price * i.quantity) - i.discount
        pdf.cell(80, 8, i.product_name, border=1)
        pdf.cell(25, 8, f"{i.unit_price:.2f}", border=1, align='R')
        pdf.cell(20, 8, str(i.quantity), border=1, align='R')
        pdf.cell(25, 8, f"{i.discount:.2f}", border=1, align='R')
        pdf.cell(30, 8, f"{total_line:.2f}", border=1, ln=1, align='R')
    pdf.ln(5)
    pdf.cell(0, 6, f"Subtotal: {subtotal:.2f}", ln=1, align='R')
    pdf.cell(0, 6, f"ITBIS ({ITBIS_RATE*100:.0f}%): {itbis:.2f}", ln=1, align='R')
    pdf.cell(0, 6, f"Total: {total:.2f}", ln=1, align='R')
    output = BytesIO()
    pdf.output(output)
    output.seek(0)
    return output

# Routes
@app.route('/')
def index():
    return redirect(url_for('list_quotations'))

# Clients CRUD
@app.route('/clientes', methods=['GET', 'POST'])
def clients():
    if request.method == 'POST':
        client = Client(
            name=request.form['name'],
            identifier=request.form['identifier'],
            phone=request.form['phone'],
            email=request.form.get('email')
        )
        db.session.add(client)
        db.session.commit()
        flash('Cliente agregado')
        return redirect(url_for('clients'))
    clients = Client.query.all()
    return render_template('clientes.html', clients=clients)

@app.route('/clientes/delete/<int:client_id>')
def delete_client(client_id):
    client = Client.query.get_or_404(client_id)
    db.session.delete(client)
    db.session.commit()
    flash('Cliente eliminado')
    return redirect(url_for('clients'))

# Products CRUD
@app.route('/productos', methods=['GET', 'POST'])
def products():
    if request.method == 'POST':
        product = Product(name=request.form['name'], price=_to_float(request.form['price']))
        db.session.add(product)
        db.session.commit()
        flash('Producto agregado')
        return redirect(url_for('products'))
    products = Product.query.all()
    return render_template('productos.html', products=products)

@app.route('/productos/delete/<int:product_id>')
def delete_product(product_id):
    product = Product.query.get_or_404(product_id)
    db.session.delete(product)
    db.session.commit()
    flash('Producto eliminado')
    return redirect(url_for('products'))

# Quotations
@app.route('/cotizaciones')
def list_quotations():
    quotations = Quotation.query.order_by(Quotation.date.desc()).all()
    return render_template('cotizaciones.html', quotations=quotations)

@app.route('/cotizaciones/nueva', methods=['GET', 'POST'])
def new_quotation():
    if request.method == 'POST':
        client = Client(
            name=request.form['client_name'],
            identifier=request.form['client_identifier'],
            phone=request.form['client_phone'],
            email=request.form.get('client_email')
        )
        db.session.add(client)
        db.session.flush()
        items = []
        names = request.form.getlist('product_name[]')
        prices = request.form.getlist('product_price[]')
        quantities = request.form.getlist('product_quantity[]')
        discounts = request.form.getlist('product_discount[]')
        for n, p, q, d in zip(names, prices, quantities, discounts):
            items.append({
                'product_name': n,
                'unit_price': _to_float(p),
                'quantity': _to_int(q),
                'discount': _to_float(d),
            })
        subtotal, itbis, total = calculate_totals(items)
        quotation = Quotation(client_id=client.id, subtotal=subtotal, itbis=itbis, total=total)
        db.session.add(quotation)
        db.session.flush()
        for it in items:
            q_item = QuotationItem(quotation_id=quotation.id, **it)
            db.session.add(q_item)
        db.session.commit()
        flash('Cotización guardada')
        return redirect(url_for('list_quotations'))
    products = Product.query.all()
    return render_template('cotizacion.html', products=products)

@app.route('/cotizaciones/<int:quotation_id>/pdf')
def quotation_pdf(quotation_id):
    quotation = Quotation.query.get_or_404(quotation_id)
    company = {'name': 'Mi Empresa', 'address': 'Dirección', 'rnc': '123456789', 'phone': '809-555-5555'}
    pdf_file = generate_pdf('Cotización', company, quotation.client, quotation.items, quotation.subtotal, quotation.itbis, quotation.total)
    return send_file(pdf_file, download_name=f'cotizacion_{quotation_id}.pdf', as_attachment=True)

@app.route('/cotizaciones/<int:quotation_id>/convertir')
def quotation_to_order(quotation_id):
    quotation = Quotation.query.get_or_404(quotation_id)
    order = Order(client_id=quotation.client_id, quotation_id=quotation.id, subtotal=quotation.subtotal, itbis=quotation.itbis, total=quotation.total)
    db.session.add(order)
    db.session.flush()
    for item in quotation.items:
        o_item = OrderItem(order_id=order.id, product_name=item.product_name, unit_price=item.unit_price, quantity=item.quantity, discount=item.discount)
        db.session.add(o_item)
    db.session.commit()
    flash('Pedido creado')
    return redirect(url_for('list_orders'))

# Orders
@app.route('/pedidos')
def list_orders():
    orders = Order.query.order_by(Order.id.desc()).all()
    return render_template('pedido.html', orders=orders)

@app.route('/pedidos/<int:order_id>/facturar')
def order_to_invoice(order_id):
    order = Order.query.get_or_404(order_id)
    invoice = Invoice(client_id=order.client_id, order_id=order.id, subtotal=order.subtotal, itbis=order.itbis, total=order.total)
    db.session.add(invoice)
    db.session.flush()
    for item in order.items:
        i_item = InvoiceItem(invoice_id=invoice.id, product_name=item.product_name, unit_price=item.unit_price, quantity=item.quantity, discount=item.discount)
        db.session.add(i_item)
    order.status = 'Entregado'
    db.session.commit()
    flash('Factura generada')
    return redirect(url_for('list_invoices'))

# Invoices
@app.route('/facturas')
def list_invoices():
    invoices = Invoice.query.order_by(Invoice.date.desc()).all()
    return render_template('factura.html', invoices=invoices)

@app.route('/facturas/<int:invoice_id>/pdf')
def invoice_pdf(invoice_id):
    invoice = Invoice.query.get_or_404(invoice_id)
    company = {'name': 'Mi Empresa', 'address': 'Dirección', 'rnc': '123456789', 'phone': '809-555-5555'}
    pdf_file = generate_pdf('Factura', company, invoice.client, invoice.items, invoice.subtotal, invoice.itbis, invoice.total)
    return send_file(pdf_file, download_name=f'factura_{invoice_id}.pdf', as_attachment=True)

if __name__ == '__main__':
    app.run(debug=True)
