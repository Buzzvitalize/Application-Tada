from flask import Flask, render_template, request, redirect, url_for, send_file, send_from_directory, flash, session, jsonify
from models import db, Client, Product, Quotation, QuotationItem, Order, OrderItem, Invoice, InvoiceItem, CompanyInfo
from fpdf import FPDF
from io import BytesIO
from datetime import datetime
from sqlalchemy import func
from werkzeug.utils import secure_filename
from uuid import uuid4
import qrcode
import os
from ai import recommend_products

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database.sqlite'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.secret_key = os.environ.get('SECRET_KEY', 'dev')

DB_PATH = os.path.join(os.path.dirname(__file__), 'database.sqlite')

# Initialize database
with app.app_context():
    db.init_app(app)
    db.create_all()
    # sample data and company info
    if not CompanyInfo.query.first():
        company = CompanyInfo(
            name='Empresa Demo',
            street='Calle 1',
            sector='Centro',
            province='Santo Domingo',
            phone='809-000-0000',
            rnc='101000000',
            website='',
            logo='',
        )
        db.session.add(company)
        db.session.commit()
    if not Client.query.first():
        sample_client = Client(
            name='Juan Perez',
            identifier='001-0000000-1',
            phone='809-000-0000',
            email='juan@example.com',
            street='Av. Siempre Viva',
            sector='Centro',
            province='Santo Domingo',
            is_final_consumer=False,
        )
        sample_product = Product(name='Producto Ejemplo', unit='Unidad', price=100.0, category='Servicios')
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
    itbis = sum(((item['unit_price'] * item['quantity']) - item['discount']) * ITBIS_RATE
                for item in items if item.get('has_itbis'))
    total = subtotal + itbis
    return subtotal, itbis, total


def get_company_info():
    c = CompanyInfo.query.first()
    return {
        'name': c.name,
        'address': f"{c.street}, {c.sector}, {c.province}",
        'rnc': c.rnc,
        'phone': c.phone,
        'website': c.website,
        'logo': os.path.join(app.static_folder, c.logo) if c.logo else None,
        'ncf_final': c.ncf_final,
        'ncf_fiscal': c.ncf_fiscal,
    }


def generate_pdf(title, company, client, items, subtotal, itbis, total, ncf=None, output_path=None, qr_url=None):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font('Helvetica', 'B', 16)
    text_x = 10
    if company.get('logo'):
        pdf.image(company['logo'], 10, 8, 33)
        text_x = 50
    pdf.set_xy(text_x, 10)
    pdf.cell(0, 10, company['name'], ln=1)
    pdf.set_font('Helvetica', '', 10)
    pdf.set_x(text_x)
    pdf.cell(0, 5, company['address'], ln=1)
    pdf.set_x(text_x)
    pdf.cell(0, 5, f"RNC: {company['rnc']} Tel: {company['phone']}", ln=1)
    if company.get('website'):
        pdf.set_x(text_x)
        pdf.cell(0, 5, company['website'], ln=1)
    pdf.ln(5)
    pdf.set_font('Helvetica', 'B', 14)
    pdf.cell(0, 10, title, ln=1, align='C')
    if ncf:
        pdf.set_font('Helvetica', '', 12)
        pdf.cell(0, 6, f"NCF: {ncf}", ln=1, align='C')
    pdf.ln(5)
    pdf.set_font('Helvetica', '', 12)
    pdf.cell(0, 6, f"Cliente: {client.name}", ln=1)
    if client.identifier:
        pdf.cell(0, 6, f"Cédula/RNC: {client.identifier}", ln=1)
    pdf.cell(0, 6, f"Teléfono: {client.phone}", ln=1)
    pdf.cell(0, 6, f"Dirección: {client.street}, {client.sector}, {client.province}", ln=1)
    if client.email:
        pdf.cell(0, 6, f"Email: {client.email}", ln=1)
    pdf.ln(5)
    pdf.set_font('Helvetica', 'B', 12)
    pdf.cell(60, 8, 'Producto', border=1)
    pdf.cell(20, 8, 'Unidad', border=1)
    pdf.cell(25, 8, 'Precio', border=1, align='R')
    pdf.cell(20, 8, 'Cant.', border=1, align='R')
    pdf.cell(25, 8, 'Desc.', border=1, align='R')
    pdf.cell(30, 8, 'Total', border=1, ln=1, align='R')
    pdf.set_font('Helvetica', '', 12)
    for i in items:
        total_line = (i.unit_price * i.quantity) - i.discount
        pdf.cell(60, 8, i.product_name, border=1)
        pdf.cell(20, 8, i.unit, border=1, align='C')
        pdf.cell(25, 8, f"{i.unit_price:.2f}", border=1, align='R')
        pdf.cell(20, 8, str(i.quantity), border=1, align='R')
        pdf.cell(25, 8, f"{i.discount:.2f}", border=1, align='R')
        pdf.cell(30, 8, f"{total_line:.2f}", border=1, ln=1, align='R')
    discount_total = sum(i.discount for i in items)
    pdf.ln(5)
    pdf.cell(0, 6, f"Subtotal: {subtotal:.2f}", ln=1, align='R')
    pdf.cell(0, 6, f"ITBIS ({ITBIS_RATE*100:.0f}%): {itbis:.2f}", ln=1, align='R')
    pdf.cell(0, 6, f"Descuento: {discount_total:.2f}", ln=1, align='R')
    pdf.cell(0, 6, f"Total: {total:.2f}", ln=1, align='R')
    if qr_url:
        os.makedirs(os.path.join(app.static_folder, 'qrcodes'), exist_ok=True)
        qr_path = os.path.join(app.static_folder, 'qrcodes', f"{uuid4().hex}.png")
        img = qrcode.make(qr_url)
        img.save(qr_path)
        pdf.image(qr_path, x=170, y=260, w=30)
    if output_path:
        pdf.output(output_path)
        return output_path
    output = BytesIO()
    pdf.output(output)
    output.seek(0)
    return output

# Routes
@app.before_request
def require_login():
    allowed = {'login', 'static'}
    if request.endpoint not in allowed and 'user' not in session:
        return redirect(url_for('login'))

@app.route('/', methods=['GET', 'POST'])
def login():
    company = CompanyInfo.query.first()
    if request.method == 'POST':
        if request.form.get('username') == 'admin' and request.form.get('pin') == '363636':
            session['user'] = 'admin'
            return redirect(url_for('list_quotations'))
        flash('Credenciales inválidas')
    return render_template('login.html', company=company)

@app.route('/logout')
def logout():
    session.pop('user', None)
    return redirect(url_for('login'))

# Clients CRUD
@app.route('/clientes', methods=['GET', 'POST'])
def clients():
    if request.method == 'POST':
        is_final = request.form.get('type') == 'final'
        identifier = request.form.get('identifier') if not is_final else request.form.get('identifier') or None
        if not is_final and not identifier:
            flash('El identificador es obligatorio para comprobante fiscal')
            return redirect(url_for('clients'))
        client = Client(
            name=request.form['name'],
            identifier=identifier,
            phone=request.form['phone'],
            email=request.form.get('email'),
            street=request.form['street'],
            sector=request.form['sector'],
            province=request.form['province'],
            is_final_consumer=is_final
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

@app.route('/clientes/edit/<int:client_id>', methods=['GET', 'POST'])
def edit_client(client_id):
    client = Client.query.get_or_404(client_id)
    if request.method == 'POST':
        is_final = request.form.get('type') == 'final'
        identifier = request.form.get('identifier') if not is_final else request.form.get('identifier') or None
        if not is_final and not identifier:
            flash('El identificador es obligatorio para comprobante fiscal')
            return redirect(url_for('edit_client', client_id=client.id))
        client.name = request.form['name']
        client.identifier = identifier
        client.phone = request.form['phone']
        client.email = request.form.get('email')
        client.street = request.form['street']
        client.sector = request.form['sector']
        client.province = request.form['province']
        client.is_final_consumer = is_final
        db.session.commit()
        flash('Cliente actualizado')
        return redirect(url_for('clients'))
    return render_template('cliente_form.html', client=client)

# Products CRUD
@app.route('/productos', methods=['GET', 'POST'])
def products():
    units = ['Unidad', 'Metro', 'Onza', 'Libra', 'Kilogramo', 'Litro']
    categories = ['Servicios', 'Consumo', 'Liquido', 'Otros']
    if request.method == 'POST':
        product = Product(
            name=request.form['name'],
            unit=request.form['unit'],
            price=_to_float(request.form['price']),
            category=request.form.get('category'),
            has_itbis=bool(request.form.get('has_itbis'))
        )
        db.session.add(product)
        db.session.commit()
        flash('Producto agregado')
        return redirect(url_for('products'))
    cat = request.args.get('cat')
    query = Product.query
    if cat:
        query = query.filter_by(category=cat)
    products = query.all()
    return render_template('productos.html', products=products, units=units, categories=categories, current_cat=cat)

@app.route('/productos/delete/<int:product_id>')
def delete_product(product_id):
    product = Product.query.get_or_404(product_id)
    db.session.delete(product)
    db.session.commit()
    flash('Producto eliminado')
    return redirect(url_for('products'))

@app.route('/productos/edit/<int:product_id>', methods=['GET', 'POST'])
def edit_product(product_id):
    product = Product.query.get_or_404(product_id)
    units = ['Unidad', 'Metro', 'Onza', 'Libra', 'Kilogramo', 'Litro']
    categories = ['Servicios', 'Consumo', 'Liquido', 'Otros']
    if request.method == 'POST':
        product.name = request.form['name']
        product.unit = request.form['unit']
        product.price = _to_float(request.form['price'])
        product.category = request.form.get('category')
        product.has_itbis = bool(request.form.get('has_itbis'))
        db.session.commit()
        flash('Producto actualizado')
        return redirect(url_for('products'))
    return render_template('producto_form.html', product=product, units=units, categories=categories)

# Quotations
@app.route('/cotizaciones')
def list_quotations():
    q = request.args.get('q')
    query = Quotation.query.join(Client)
    if q:
        query = query.filter((Client.name.contains(q)) | (Client.identifier.contains(q)))
    quotations = query.order_by(Quotation.date.desc()).all()
    return render_template('cotizaciones.html', quotations=quotations, q=q)

@app.route('/cotizaciones/nueva', methods=['GET', 'POST'])
def new_quotation():
    if request.method == 'POST':
        client_id = request.form.get('client_id')
        if client_id:
            client = Client.query.get_or_404(client_id)
        else:
            is_final = request.form.get('client_type') == 'final'
            identifier = request.form.get('client_identifier') if not is_final else request.form.get('client_identifier') or None
            if not is_final and not identifier:
                flash('El identificador es obligatorio para comprobante fiscal')
                return redirect(url_for('new_quotation'))
            client = Client(
                name=request.form['client_name'],
                identifier=identifier,
                phone=request.form['client_phone'],
                email=request.form.get('client_email'),
                street=request.form['client_street'],
                sector=request.form['client_sector'],
                province=request.form['client_province'],
                is_final_consumer=is_final,
            )
            db.session.add(client)
            db.session.flush()
        items = []
        product_ids = request.form.getlist('product_id[]')
        quantities = request.form.getlist('product_quantity[]')
        discounts = request.form.getlist('product_discount[]')
        for pid, q, d in zip(product_ids, quantities, discounts):
            product = Product.query.get(pid)
            if not product:
                continue
            qty = _to_int(q)
            percent = _to_float(d)
            discount_amount = product.price * qty * (percent / 100)
            items.append({
                'product_name': product.name,
                'unit': product.unit,
                'unit_price': product.price,
                'quantity': qty,
                'discount': discount_amount,
                'category': product.category,
                'has_itbis': product.has_itbis,
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
    clients = Client.query.all()
    products = Product.query.all()
    return render_template('cotizacion.html', clients=clients, products=products)

@app.route('/cotizaciones/editar/<int:quotation_id>', methods=['GET', 'POST'])
def edit_quotation(quotation_id):
    quotation = Quotation.query.get_or_404(quotation_id)
    if request.method == 'POST':
        client_id = request.form.get('client_id')
        if client_id:
            client = Client.query.get_or_404(client_id)
        else:
            client = quotation.client
            is_final = request.form.get('client_type') == 'final'
            identifier = request.form.get('client_identifier') if not is_final else request.form.get('client_identifier') or None
            if not is_final and not identifier:
                flash('El identificador es obligatorio para comprobante fiscal')
                return redirect(url_for('edit_quotation', quotation_id=quotation.id))
            client.name = request.form['client_name']
            client.identifier = identifier
            client.phone = request.form['client_phone']
            client.email = request.form.get('client_email')
            client.street = request.form['client_street']
            client.sector = request.form['client_sector']
            client.province = request.form['client_province']
            client.is_final_consumer = is_final
        quotation.items.clear()
        db.session.flush()
        items = []
        product_ids = request.form.getlist('product_id[]')
        quantities = request.form.getlist('product_quantity[]')
        discounts = request.form.getlist('product_discount[]')
        for pid, q, d in zip(product_ids, quantities, discounts):
            product = Product.query.get(pid)
            if not product:
                continue
            qty = _to_int(q)
            percent = _to_float(d)
            discount_amount = product.price * qty * (percent / 100)
            items.append({
                'product_name': product.name,
                'unit': product.unit,
                'unit_price': product.price,
                'quantity': qty,
                'discount': discount_amount,
                'category': product.category,
                'has_itbis': product.has_itbis,
            })
        subtotal, itbis, total = calculate_totals(items)
        quotation.client_id = client.id
        quotation.subtotal = subtotal
        quotation.itbis = itbis
        quotation.total = total
        for it in items:
            quotation.items.append(QuotationItem(**it))
        db.session.commit()
        flash('Cotización actualizada')
        return redirect(url_for('list_quotations'))
    clients = Client.query.all()
    products = Product.query.all()
    # prepare items for template (discount percentage)
    items = []
    for it in quotation.items:
        base = it.unit_price * it.quantity
        percent = (it.discount / base * 100) if base else 0
        product = Product.query.filter_by(name=it.product_name).first()
        items.append({'product_id': product.id if product else '', 'quantity': it.quantity,
                      'discount': percent, 'unit': it.unit,
                      'price': it.unit_price})
    return render_template('cotizacion_edit.html', quotation=quotation, clients=clients,
                           products=products, items=items)


@app.route('/ajustes', methods=['GET', 'POST'])
def settings():
    company = CompanyInfo.query.first()
    if request.method == 'POST':
        company.name = request.form['name']
        company.street = request.form['street']
        company.sector = request.form['sector']
        company.province = request.form['province']
        company.phone = request.form['phone']
        company.rnc = request.form['rnc']
        company.website = request.form.get('website')
        file = request.files.get('logo')
        if file and file.filename:
            filename = secure_filename(file.filename)
            upload_dir = os.path.join(app.static_folder, 'uploads')
            os.makedirs(upload_dir, exist_ok=True)
            path = os.path.join(upload_dir, filename)
            file.save(path)
            company.logo = f'uploads/{filename}'
        company.ncf_final = _to_int(request.form.get('ncf_final')) or company.ncf_final
        company.ncf_fiscal = _to_int(request.form.get('ncf_fiscal')) or company.ncf_fiscal
        db.session.commit()
        flash('Ajustes guardados')
        return redirect(url_for('settings'))
    return render_template('ajustes.html', company=company)

@app.route('/cotizaciones/<int:quotation_id>/pdf')
def quotation_pdf(quotation_id):
    quotation = Quotation.query.get_or_404(quotation_id)
    company = get_company_info()
    filename = f'cotizacion_{quotation_id}.pdf'
    pdf_path = os.path.join(app.static_folder, 'pdfs', filename)
    os.makedirs(os.path.dirname(pdf_path), exist_ok=True)
    qr_url = request.url_root.rstrip('/') + url_for('serve_pdf', filename=filename)
    generate_pdf('Cotización', company, quotation.client, quotation.items,
                 quotation.subtotal, quotation.itbis, quotation.total,
                 output_path=pdf_path, qr_url=qr_url)
    return send_file(pdf_path, download_name=filename, as_attachment=True)

@app.route('/cotizaciones/<int:quotation_id>/convertir')
def quotation_to_order(quotation_id):
    quotation = Quotation.query.get_or_404(quotation_id)
    order = Order(client_id=quotation.client_id, quotation_id=quotation.id, subtotal=quotation.subtotal, itbis=quotation.itbis, total=quotation.total)
    db.session.add(order)
    db.session.flush()
    for item in quotation.items:
        o_item = OrderItem(
            order_id=order.id,
            product_name=item.product_name,
            unit=item.unit,
            unit_price=item.unit_price,
            quantity=item.quantity,
            discount=item.discount,
            category=item.category,
            has_itbis=item.has_itbis,
        )
        db.session.add(o_item)
    db.session.commit()
    flash('Pedido creado')
    return redirect(url_for('list_orders'))

# Orders
@app.route('/pedidos')
def list_orders():
    q = request.args.get('q')
    query = Order.query.join(Client)
    if q:
        query = query.filter((Client.name.contains(q)) | (Client.identifier.contains(q)))
    orders = query.order_by(Order.id.desc()).all()
    return render_template('pedido.html', orders=orders, q=q)

@app.route('/pedidos/<int:order_id>/facturar')
def order_to_invoice(order_id):
    order = Order.query.get_or_404(order_id)
    company = CompanyInfo.query.first()
    if order.client.is_final_consumer:
        ncf = f"B02{company.ncf_final:08d}"
        company.ncf_final += 1
    else:
        ncf = f"B01{company.ncf_fiscal:08d}"
        company.ncf_fiscal += 1
    invoice = Invoice(client_id=order.client_id, order_id=order.id, subtotal=order.subtotal,
                      itbis=order.itbis, total=order.total, ncf=ncf)
    db.session.add(invoice)
    db.session.flush()
    for item in order.items:
        i_item = InvoiceItem(
            invoice_id=invoice.id,
            product_name=item.product_name,
            unit=item.unit,
            unit_price=item.unit_price,
            quantity=item.quantity,
            discount=item.discount,
            category=item.category,
            has_itbis=item.has_itbis,
        )
        db.session.add(i_item)
    order.status = 'Entregado'
    db.session.commit()
    flash('Factura generada')
    return redirect(url_for('list_invoices'))

# Invoices
@app.route('/facturas')
def list_invoices():
    q = request.args.get('q')
    query = Invoice.query.join(Client)
    if q:
        query = query.filter((Client.name.contains(q)) | (Client.identifier.contains(q)))
    invoices = query.order_by(Invoice.date.desc()).all()
    return render_template('factura.html', invoices=invoices, q=q)

@app.route('/facturas/<int:invoice_id>/pdf')
def invoice_pdf(invoice_id):
    invoice = Invoice.query.get_or_404(invoice_id)
    company = get_company_info()
    filename = f'factura_{invoice_id}.pdf'
    pdf_path = os.path.join(app.static_folder, 'pdfs', filename)
    os.makedirs(os.path.dirname(pdf_path), exist_ok=True)
    qr_url = request.url_root.rstrip('/') + url_for('serve_pdf', filename=filename)
    generate_pdf('Factura', company, invoice.client, invoice.items,
                 invoice.subtotal, invoice.itbis, invoice.total,
                 ncf=invoice.ncf, output_path=pdf_path, qr_url=qr_url)
    return send_file(pdf_path, download_name=filename, as_attachment=True)

@app.route('/pdfs/<path:filename>')
def serve_pdf(filename):
    return send_from_directory(os.path.join(app.static_folder, 'pdfs'), filename)

@app.route('/reportes')
def reportes():
    total_invoices = db.session.query(func.count(Invoice.id)).scalar() or 0
    total_sales = db.session.query(func.sum(Invoice.total)).scalar() or 0
    sales_by_category = db.session.query(
        InvoiceItem.category,
        func.sum((InvoiceItem.unit_price * InvoiceItem.quantity) - InvoiceItem.discount)
    ).group_by(InvoiceItem.category).all()
    stats = {
        'clients': Client.query.count(),
        'products': Product.query.count(),
        'quotations': Quotation.query.count(),
        'orders': Order.query.count(),
        'invoices': total_invoices,
    }
    return render_template('reportes.html', total_sales=total_sales, sales_by_category=sales_by_category, stats=stats)


@app.route('/contabilidad')
def contabilidad():
    return render_template('contabilidad.html')


@app.route('/api/recommendations')
def api_recommendations():
    """Return top product recommendations based on past orders."""
    return jsonify({'products': recommend_products()})

if __name__ == '__main__':
    app.run(debug=True)
