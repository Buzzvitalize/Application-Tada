from flask import (
    Flask,
    render_template,
    request,
    redirect,
    url_for,
    send_file,
    send_from_directory,
    flash,
    session,
    jsonify,
    g,
    current_app,
)
try:
    from flask_migrate import Migrate
except ModuleNotFoundError:  # pragma: no cover
    class Migrate:
        def __init__(self, *a, **k):
            pass
        def init_app(self, *a, **k):
            pass
import logging
from logging.handlers import RotatingFileHandler
try:
    from flask_wtf import CSRFProtect
except ModuleNotFoundError:  # pragma: no cover
    class CSRFProtect:
        def __init__(self, app=None):
            if app:
                self.init_app(app)
        def init_app(self, app):
            pass
        def exempt(self, view):
            return view
from models import (
    db,
    migrate,
    Client,
    Product,
    Quotation,
    QuotationItem,
    Order,
    OrderItem,
    Invoice,
    InvoiceItem,
    CompanyInfo,
    User,
    AccountRequest,
    ExportLog,
    NcfLog,
    dom_now,
)
from io import BytesIO, StringIO
import csv
try:
    from openpyxl import Workbook
except ModuleNotFoundError:  # pragma: no cover
    Workbook = None
from datetime import datetime, timedelta
from sqlalchemy import func, inspect
from sqlalchemy.orm import load_only, joinedload
from werkzeug.utils import secure_filename
from werkzeug.security import generate_password_hash
import os
import re
import json
from ai import recommend_products
from weasy_pdf import generate_pdf
from functools import wraps
from auth import auth_bp
from config import DevelopmentConfig
try:
    from dotenv import load_dotenv
except ModuleNotFoundError:  # pragma: no cover
    def load_dotenv():
        pass
try:
    from rq import Queue
    from redis import Redis
except Exception:  # pragma: no cover
    Queue = None
    Redis = None
import threading

load_dotenv()
# Load RNC data for company name lookup
RNC_DATA = {}
DATA_PATH = os.path.join(os.path.dirname(__file__), 'data', 'DGII_RNC.TXT')
if os.path.exists(DATA_PATH):
    with open(DATA_PATH, encoding='utf-8') as f:
        for row in f:
            parts = row.strip().split('|')
            if len(parts) >= 2:
                rnc = re.sub(r'\D', '', parts[0])
                name = parts[1].strip()
                if rnc:
                    RNC_DATA[rnc] = name

app = Flask(__name__)
app.config.from_object(DevelopmentConfig)

if not os.path.exists('logs'):
    os.makedirs('logs')
file_handler = RotatingFileHandler('logs/app.log', maxBytes=10240, backupCount=10)
file_handler.setFormatter(logging.Formatter('%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'))
file_handler.setLevel(logging.INFO)
app.logger.addHandler(file_handler)
app.logger.setLevel(logging.INFO)
app.logger.info('Tiendix startup')


def _fmt_money(value):
    return f"RD${value:,.2f}"


app.jinja_env.filters['money'] = _fmt_money

db.init_app(app)
migrate.init_app(app, db)
csrf = CSRFProtect(app)
if 'csrf_token' not in app.jinja_env.globals:
    app.jinja_env.globals['csrf_token'] = lambda: ''
app.register_blueprint(auth_bp)

# Ensure tables exist when running without explicit migrations
with app.app_context():
    db.create_all()

if Queue and Redis:
    redis_conn = Redis.from_url(os.getenv('REDIS_URL', 'redis://localhost:6379'))
    export_queue = Queue('exports', connection=redis_conn)
else:  # pragma: no cover
    export_queue = None


def enqueue_export(fn, *args):
    if export_queue:
        return export_queue.enqueue(fn, *args)
    t = threading.Thread(target=fn, args=args, daemon=True)
    t.start()
    return t


def log_export(user, formato, tipo, filtros, status, message='', file_path=None):
    with app.app_context():
        entry = ExportLog(
            user=user,
            company_id=current_company_id(),
            formato=formato,
            tipo=tipo,
            filtros=json.dumps(filtros),
            status=status,
            message=message,
            file_path=file_path,
        )
        db.session.add(entry)
        db.session.commit()
        return entry.id


def _export_job(company_id, user, start, end, estado, categoria, formato, tipo, entry_id):  # pragma: no cover - background
    with app.app_context():
        session['company_id'] = company_id
        filtros = {
            'fecha_inicio': start.strftime('%Y-%m-%d') if start else '',
            'fecha_fin': end.strftime('%Y-%m-%d') if end else '',
            'estado': estado or '',
            'categoria': categoria or '',
        }
        try:
            q = _filtered_invoice_query(start, end, estado, categoria)
            invoices = q.options(
                joinedload(Invoice.client),
                load_only(Invoice.client_id, Invoice.total, Invoice.date, Invoice.status),
            ).all()
            path = os.path.join('maint', f'export_{entry_id}.{formato}')
            if formato == 'csv':
                with open(path, 'w', newline='', encoding='utf-8') as f:
                    writer = csv.writer(f)
                    writer.writerow(['Cliente', 'Fecha', 'Estado', 'Total'])
                    for inv in invoices:
                        writer.writerow([
                            inv.client.name if inv.client else '',
                            inv.date.strftime('%Y-%m-%d'),
                            inv.status or '',
                            f"{inv.total:.2f}",
                        ])
            entry = ExportLog.query.get(entry_id)
            entry.status = 'success'
            entry.file_path = path
            db.session.commit()
        except Exception as exc:
            entry = ExportLog.query.get(entry_id)
            entry.status = 'fail'
            entry.message = str(exc)
            db.session.commit()
def _migrate_legacy_schema():
    """Add missing columns to older SQLite databases.

    Early versions of the project lacked fields such as ``Product.category``.
    Users with an old ``database.sqlite`` would see errors like
    "no such column: product.category" when creating cotizaciones.  This helper
    checks for expected columns and adds them on the fly so the application can
    continue running without manual intervention.
    """
    inspector = inspect(db.engine)
    existing = {c['name'] for c in inspector.get_columns('product')}
    statements = []
    if 'category' not in existing:
        statements.append("ALTER TABLE product ADD COLUMN category VARCHAR(50)")
    if 'unit' not in existing:
        statements.append("ALTER TABLE product ADD COLUMN unit VARCHAR(20) DEFAULT 'Unidad'")
    if 'has_itbis' not in existing:
        statements.append("ALTER TABLE product ADD COLUMN has_itbis BOOLEAN DEFAULT 1")
    for stmt in statements:
        db.session.execute(db.text(stmt))
    if statements:
        db.session.commit()


def ensure_admin():  # pragma: no cover - optional helper for deployments
    with app.app_context():
        db.create_all()
        _migrate_legacy_schema()
        if not User.query.filter_by(username='admin').first():
            admin = User(username='admin', role='admin')
            admin.set_password(os.environ.get('ADMIN_PASSWORD', '363636'))
            db.session.add(admin)
            db.session.commit()
        db.session.remove()

# Utility constants
ITBIS_RATE = 0.18
UNITS = ('Unidad', 'Metro', 'Onza', 'Libra', 'Kilogramo', 'Litro')
CATEGORIES = ('Servicios', 'Consumo', 'Liquido', 'Otros')
INVOICE_STATUSES = ('Pendiente', 'Pagada')
MAX_EXPORT_ROWS = 50000


def current_company_id():
    return session.get('company_id')


def company_query(model):
    cid = current_company_id()
    if session.get('role') == 'admin' and cid is None:
        return model.query
    return model.query.filter_by(company_id=cid)


def company_get(model, object_id):
    return company_query(model).filter_by(id=object_id).first_or_404()

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


def _parse_report_params(fecha_inicio, fecha_fin, estado, categoria):
    """Validate and normalize report filter parameters."""
    start = end = None
    if fecha_inicio:
        try:
            start = datetime.strptime(fecha_inicio, '%Y-%m-%d')
        except ValueError:
            start = None
    if fecha_fin:
        try:
            end = datetime.strptime(fecha_fin, '%Y-%m-%d')
        except ValueError:
            end = None
    if start and end and start > end:
        start = end = None
    if estado not in INVOICE_STATUSES:
        estado = None
    if categoria not in CATEGORIES:
        categoria = None
    return start, end, estado, categoria


@app.template_filter('phone')
def fmt_phone(value):
    digits = re.sub(r'\D', '', value or '')
    if len(digits) == 10:
        return f"{digits[:3]}-{digits[3:6]}-{digits[6:]}"
    return value or ''


@app.template_filter('id_doc')
def fmt_id(value):
    digits = re.sub(r'\D', '', value or '')
    if len(digits) == 9:
        return f"{digits[:3]}-{digits[3:8]}-{digits[8:]}"
    if len(digits) == 11:
        return f"{digits[:3]}-{digits[3:10]}-{digits[10:]}"
    return value or ''


def calculate_totals(items):
    subtotal = 0
    itbis = 0
    for item in items:
        line = (item['unit_price'] * item['quantity']) - item['discount']
        subtotal += line
        if item.get('has_itbis'):
            itbis += line * ITBIS_RATE
    return subtotal, itbis, subtotal + itbis


def build_items(product_ids, quantities, discounts):
    # Convert the list of product ids to integers, ignoring any non-numeric
    # values that may come from malformed form submissions. Previously a
    # stray string (e.g. the product name) would raise ``ValueError`` and the
    # quotation silently failed to save.  Now we skip those entries so the
    # view can provide proper feedback to the user.
    ids: list[int] = []
    for pid in product_ids:
        try:
            if pid:
                ids.append(int(pid))
        except (TypeError, ValueError):
            continue
    products = (
        company_query(Product)
        .options(load_only(
            Product.id,
            Product.code,
            Product.reference,
            Product.name,
            Product.unit,
            Product.price,
            Product.category,
            Product.has_itbis,
        ))
        .filter(Product.id.in_(ids))
        .all()
    )
    prod_map = {str(p.id): p for p in products}
    items = []
    for pid, q, d in zip(product_ids, quantities, discounts):
        product = prod_map.get(pid)
        if not product:
            continue
        qty = _to_int(q)
        percent = _to_float(d)
        discount_amount = product.price * qty * (percent / 100)
        items.append({
            'code': product.code,
            'reference': product.reference,
            'product_name': product.name,
            'unit': product.unit,
            'unit_price': product.price,
            'quantity': qty,
            'discount': discount_amount,
            'category': product.category,
            'has_itbis': product.has_itbis,
            'company_id': current_company_id(),
        })
    return items


@app.route('/api/rnc/<rnc>')
def rnc_lookup(rnc):
    clean = rnc.replace('-', '')
    name = RNC_DATA.get(clean)
    if not name:
        client = Client.query.filter(func.replace(Client.identifier, '-', '') == clean).first()
        name = client.name if client else ''
    return jsonify({'name': name})


@app.before_request
def load_company():
    cid = current_company_id()
    g.company = CompanyInfo.query.get(cid) if cid else None


@app.context_processor
def inject_company():
    return {'company': getattr(g, 'company', None)}


def get_company_info():
    c = CompanyInfo.query.get(current_company_id())
    if not c:
        return {}
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
# Routes
@app.before_request
def require_login():
    allowed = {'auth.login', 'static', 'request_account', 'auth.logout'}
    if request.endpoint not in allowed and 'user_id' not in session:
        return redirect(url_for('auth.login'))
    admin_extra = {'admin_companies', 'select_company', 'clear_company',
                   'admin_requests', 'approve_request', 'reject_request'}
    if session.get('role') == 'admin' and not session.get('company_id') \
            and request.endpoint not in allowed.union(admin_extra):
        return redirect(url_for('admin_companies'))


def admin_only(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        if session.get('role') != 'admin':
            flash('Acceso restringido')
            return redirect(url_for('list_quotations'))
        return f(*args, **kwargs)
    return wrapper


def manager_only(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        if session.get('role') not in ('admin', 'manager'):
            flash('Acceso restringido')
            return redirect(url_for('list_quotations'))
        return f(*args, **kwargs)
    return wrapper

@app.route('/')
def index():
    if 'user_id' not in session:
        return redirect(url_for('auth.login'))
    return redirect(url_for('list_quotations'))


@app.route('/solicitar-cuenta', methods=['GET', 'POST'])
@csrf.exempt
def request_account():
    if request.method == 'POST':
        if request.form.get('password') != request.form.get('confirm_password'):
            flash('Las contraseñas no coinciden', 'request')
            return redirect(url_for('request_account'))
        account_type = request.form['account_type']
        identifier = request.form.get('identifier')
        if not identifier:
            flash('Debe ingresar RNC o Cédula', 'request')
            return redirect(url_for('request_account'))
        req = AccountRequest(
            account_type=account_type,
            first_name=request.form['first_name'],
            last_name=request.form['last_name'],
            company=request.form['company'],
            identifier=identifier,
            phone=request.form['phone'],
            email=request.form['email'],
            address=request.form.get('address'),
            website=request.form.get('website'),
            username=request.form['username'],
            password=generate_password_hash(request.form['password']),
        )
        db.session.add(req)
        db.session.commit()
        flash('Solicitud enviada, espere aprobación', 'login')
        return redirect(url_for('auth.login'))
    return render_template('solicitar_cuenta.html')


@app.route('/admin/solicitudes')
@admin_only
def admin_requests():
    requests = AccountRequest.query.all()
    return render_template('admin_solicitudes.html', requests=requests)


@app.route('/admin/companies')
@admin_only
def admin_companies():
    companies = CompanyInfo.query.all()
    return render_template('admin_companies.html', companies=companies)


@app.route('/admin/companies/select/<int:company_id>')
@admin_only
def select_company(company_id):
    session['company_id'] = company_id
    return redirect(url_for('list_quotations'))


@app.route('/admin/companies/clear')
@admin_only
def clear_company():
    session.pop('company_id', None)
    return redirect(url_for('admin_companies'))


@app.route('/admin/solicitudes/<int:req_id>/aprobar', methods=['POST'])
@admin_only
def approve_request(req_id):
    req = AccountRequest.query.get_or_404(req_id)
    role = request.form.get('role', 'company')
    company = CompanyInfo(
        name=req.company,
        street=req.address or '',
        sector='',
        province='',
        phone=req.phone,
        rnc=req.identifier or '',
        website=req.website,
        logo='',
    )
    db.session.add(company)
    db.session.flush()
    user = User(username=req.username, password=req.password, role=role, company_id=company.id)
    db.session.add(user)
    db.session.delete(req)
    db.session.commit()
    flash('Cuenta aprobada')
    return redirect(url_for('admin_requests'))


@app.route('/admin/solicitudes/<int:req_id>/rechazar', methods=['POST'])
@admin_only
def reject_request(req_id):
    req = AccountRequest.query.get_or_404(req_id)
    db.session.delete(req)
    db.session.commit()
    flash('Solicitud rechazada')
    return redirect(url_for('admin_requests'))


# --- CPanel ---


@app.route('/cpaneltx')
@admin_only
def cpanel_home():
    return render_template('cpaneltx.html')


@app.route('/cpaneltx/users')
@admin_only
def cpanel_users():
    users = User.query.all()
    return render_template('cpanel_users.html', users=users)


@app.post('/cpaneltx/users/<int:user_id>/role')
@admin_only
def cpanel_user_role(user_id):
    user = User.query.get_or_404(user_id)
    role = request.form.get('role')
    if role in ('admin', 'manager', 'company'):
        user.role = role
        db.session.commit()
        flash('Rol actualizado')
    return redirect(url_for('cpanel_users'))


@app.post('/cpaneltx/users/<int:user_id>/delete')
@admin_only
def cpanel_user_delete(user_id):
    user = User.query.get_or_404(user_id)
    db.session.delete(user)
    db.session.commit()
    flash('Usuario eliminado')
    return redirect(url_for('cpanel_users'))


@app.route('/cpaneltx/companies')
@admin_only
def cpanel_companies():
    companies = CompanyInfo.query.all()
    return render_template('cpanel_companies.html', companies=companies)


@app.post('/cpaneltx/companies/<int:cid>/delete')
@admin_only
def cpanel_company_delete(cid):
    company = CompanyInfo.query.get_or_404(cid)
    db.session.delete(company)
    db.session.commit()
    flash('Empresa eliminada')
    return redirect(url_for('cpanel_companies'))


@app.route('/cpaneltx/orders')
@admin_only
def cpanel_orders():
    orders = Order.query.options(joinedload(Order.client)).all()
    return render_template('cpanel_orders.html', orders=orders)


@app.post('/cpaneltx/orders/<int:oid>/delete')
@admin_only
def cpanel_order_delete(oid):
    order = Order.query.get_or_404(oid)
    db.session.delete(order)
    db.session.commit()
    flash('Pedido eliminado')
    return redirect(url_for('cpanel_orders'))


@app.route('/cpaneltx/invoices')
@admin_only
def cpanel_invoices():
    invoices = Invoice.query.options(joinedload(Invoice.client)).all()
    return render_template('cpanel_invoices.html', invoices=invoices)


@app.post('/cpaneltx/invoices/<int:iid>/delete')
@admin_only
def cpanel_invoice_delete(iid):
    inv = Invoice.query.get_or_404(iid)
    db.session.delete(inv)
    db.session.commit()
    flash('Factura eliminada')
    return redirect(url_for('cpanel_invoices'))

# Clients CRUD
@app.route('/clientes', methods=['GET', 'POST'])
def clients():
    if request.method == 'POST':
        is_final = request.form.get('type') == 'final'
        identifier = request.form.get('identifier') if not is_final else request.form.get('identifier') or None
        last_name = request.form.get('last_name') if is_final else None
        if not is_final and not identifier:
            flash('El RNC es obligatorio para empresas')
            return redirect(url_for('clients'))
        client = Client(
            name=request.form['name'],
            last_name=last_name,
            identifier=identifier,
            phone=request.form.get('phone'),
            email=request.form.get('email'),
            street=request.form.get('street'),
            sector=request.form.get('sector'),
            province=request.form.get('province'),
            is_final_consumer=is_final,
            company_id=current_company_id()
        )
        db.session.add(client)
        db.session.commit()
        flash('Cliente agregado')
        return redirect(url_for('clients'))
    clients = company_query(Client).all()
    return render_template('clientes.html', clients=clients)

@app.route('/clientes/delete/<int:client_id>')
def delete_client(client_id):
    client = company_get(Client, client_id)
    db.session.delete(client)
    db.session.commit()
    flash('Cliente eliminado')
    return redirect(url_for('clients'))

@app.route('/clientes/edit/<int:client_id>', methods=['GET', 'POST'])
def edit_client(client_id):
    client = company_get(Client, client_id)
    if request.method == 'POST':
        is_final = request.form.get('type') == 'final'
        identifier = request.form.get('identifier') if not is_final else request.form.get('identifier') or None
        last_name = request.form.get('last_name') if is_final else None
        if not is_final and not identifier:
            flash('El RNC es obligatorio para empresas')
            return redirect(url_for('edit_client', client_id=client.id))
        client.name = request.form['name']
        client.last_name = last_name
        client.identifier = identifier
        client.phone = request.form.get('phone')
        client.email = request.form.get('email')
        client.street = request.form.get('street')
        client.sector = request.form.get('sector')
        client.province = request.form.get('province')
        client.is_final_consumer = is_final
        db.session.commit()
        flash('Cliente actualizado')
        return redirect(url_for('clients'))
    return render_template('cliente_form.html', client=client)

@csrf.exempt
@app.post('/api/clients')
def api_create_client():
    data = request.get_json() or {}
    if not data.get('name'):
        return {'error': 'El nombre es obligatorio'}, 400
    is_final = data.get('type') == 'final'
    identifier = data.get('identifier') if not is_final else data.get('identifier') or None
    last_name = data.get('last_name') if is_final else None
    if not is_final and not identifier:
        return {'error': 'El RNC es obligatorio para empresas'}, 400
    client = Client(
        name=data.get('name'),
        last_name=last_name,
        identifier=identifier,
        phone=data.get('phone'),
        email=data.get('email'),
        street=data.get('street'),
        sector=data.get('sector'),
        province=data.get('province'),
        is_final_consumer=is_final,
        company_id=current_company_id()
    )
    db.session.add(client)
    db.session.commit()
    return {'id': client.id, 'name': client.name, 'identifier': client.identifier}

# Products CRUD
@app.route('/productos', methods=['GET', 'POST'])
def products():
    if request.method == 'POST':
        product = Product(
            code=request.form['code'],
            reference=request.form.get('reference'),
            name=request.form['name'],
            unit=request.form['unit'],
            price=_to_float(request.form['price']),
            category=request.form.get('category'),
            has_itbis=bool(request.form.get('has_itbis')),
            company_id=current_company_id()
        )
        db.session.add(product)
        db.session.commit()
        flash('Producto agregado')
        return redirect(url_for('products'))
    cat = request.args.get('cat')
    query = company_query(Product)
    if cat:
        query = query.filter_by(category=cat)
    products = query.all()
    return render_template('productos.html', products=products, units=UNITS, categories=CATEGORIES, current_cat=cat)

@app.route('/productos/delete/<int:product_id>')
def delete_product(product_id):
    product = company_get(Product, product_id)
    db.session.delete(product)
    db.session.commit()
    flash('Producto eliminado')
    return redirect(url_for('products'))

@app.route('/productos/edit/<int:product_id>', methods=['GET', 'POST'])
def edit_product(product_id):
    product = company_get(Product, product_id)
    if request.method == 'POST':
        product.code = request.form['code']
        product.reference = request.form.get('reference')
        product.name = request.form['name']
        product.unit = request.form['unit']
        product.price = _to_float(request.form['price'])
        product.category = request.form.get('category')
        product.has_itbis = bool(request.form.get('has_itbis'))
        db.session.commit()
        flash('Producto actualizado')
        return redirect(url_for('products'))
    return render_template('producto_form.html', product=product, units=UNITS, categories=CATEGORIES)

# Quotations
@app.route('/cotizaciones')
def list_quotations():
    q = request.args.get('q')
    query = company_query(Quotation).join(Client)
    if q:
        query = query.filter((Client.name.contains(q)) | (Client.identifier.contains(q)))
    quotations = query.order_by(Quotation.date.desc()).all()
    return render_template('cotizaciones.html', quotations=quotations, q=q,
                           timedelta=timedelta, now=dom_now())

@csrf.exempt
@app.route('/cotizaciones/nueva', methods=['GET', 'POST'])
def new_quotation():
    if request.method == 'POST':
        print('Form data:', dict(request.form))
        client_id = request.form.get('client_id')
        if not client_id:
            flash('Debe seleccionar un cliente registrado')
            return redirect(url_for('new_quotation'))
        client = company_get(Client, client_id)
        product_ids = request.form.getlist('product_id[]')
        quantities = request.form.getlist('product_quantity[]')
        discounts = request.form.getlist('product_discount[]')
        items = build_items(product_ids, quantities, discounts)
        if not items:
            flash('Debe agregar al menos un producto')
            return redirect(url_for('new_quotation'))
        subtotal, itbis, total = calculate_totals(items)
        payment_method = request.form.get('payment_method')
        bank = request.form.get('bank') if payment_method == 'Transferencia' else None
        quotation = Quotation(client_id=client.id, subtotal=subtotal, itbis=itbis, total=total,
                               seller=request.form.get('seller'), payment_method=payment_method,
                               bank=bank, note=request.form.get('note'),
                               company_id=current_company_id())
        db.session.add(quotation)
        db.session.flush()
        for it in items:
            q_item = QuotationItem(quotation_id=quotation.id, **it)
            db.session.add(q_item)
        db.session.commit()
        flash('Cotización guardada')
        return redirect(url_for('list_quotations'))
    clients = company_query(Client).options(
        load_only(Client.id, Client.name, Client.identifier)
    ).all()
    products = company_query(Product).options(
        load_only(Product.id, Product.code, Product.name, Product.unit, Product.price)
    ).all()
    return render_template('cotizacion.html', clients=clients, products=products)

@app.route('/cotizaciones/editar/<int:quotation_id>', methods=['GET', 'POST'])
def edit_quotation(quotation_id):
    quotation = company_get(Quotation, quotation_id)
    if request.method == 'POST':
        client = quotation.client
        is_final = request.form.get('client_type') == 'final'
        identifier = request.form.get('client_identifier') if not is_final else request.form.get('client_identifier') or None
        if not is_final and not identifier:
            flash('El identificador es obligatorio para comprobante fiscal')
            return redirect(url_for('edit_quotation', quotation_id=quotation.id))
        client.name = request.form['client_name']
        client.last_name = request.form.get('client_last_name') if is_final else None
        client.identifier = identifier
        client.phone = request.form.get('client_phone')
        client.email = request.form.get('client_email')
        client.street = request.form.get('client_street')
        client.sector = request.form.get('client_sector')
        client.province = request.form.get('client_province')
        client.is_final_consumer = is_final
        quotation.items.clear()
        db.session.flush()
        product_ids = request.form.getlist('product_id[]')
        quantities = request.form.getlist('product_quantity[]')
        discounts = request.form.getlist('product_discount[]')
        items = build_items(product_ids, quantities, discounts)
        subtotal, itbis, total = calculate_totals(items)
        payment_method = request.form.get('payment_method')
        bank = request.form.get('bank') if payment_method == 'Transferencia' else None
        quotation.client_id = client.id
        quotation.subtotal = subtotal
        quotation.itbis = itbis
        quotation.total = total
        quotation.seller = request.form.get('seller')
        quotation.payment_method = payment_method
        quotation.bank = bank
        quotation.note = request.form.get('note')
        for it in items:
            quotation.items.append(QuotationItem(**it))
        db.session.commit()
        flash('Cotización actualizada')
        return redirect(url_for('list_quotations'))
    products = company_query(Product).options(
        load_only(Product.id, Product.code, Product.name, Product.unit, Product.price)
    ).all()
    product_map = {p.name: p.id for p in products}
    items = []
    for it in quotation.items:
        base = it.unit_price * it.quantity
        percent = (it.discount / base * 100) if base else 0
        items.append({
            'product_id': product_map.get(it.product_name, ''),
            'quantity': it.quantity,
            'discount': percent,
            'unit': it.unit,
            'price': it.unit_price,
        })
    return render_template(
        'cotizacion_edit.html',
        quotation=quotation,
        products=products,
        items=items,
    )


@app.route('/ajustes', methods=['GET', 'POST'])
@manager_only
def settings():
    company = CompanyInfo.query.get(current_company_id())
    if not company:
        flash('Seleccione una empresa')
        return redirect(url_for('admin_companies'))
    if request.method == 'POST':
        company.name = request.form['name']
        company.street = request.form['street']
        company.sector = request.form['sector']
        company.province = request.form['province']
        company.phone = request.form['phone']
        company.rnc = request.form['rnc']
        company.website = request.form.get('website')

        if request.form.get('remove_logo'):
            if company.logo:
                try:
                    os.remove(os.path.join(app.static_folder, company.logo))
                except FileNotFoundError:
                    pass
            company.logo = None
        else:
            file = request.files.get('logo')
            if file and file.filename:
                filename = secure_filename(file.filename)
                ext = os.path.splitext(filename)[1].lower()
                if ext not in {'.png', '.jpg', '.jpeg'}:
                    flash('Formato de logo inválido')
                    return redirect(url_for('settings'))
                file.seek(0, os.SEEK_END)
                size = file.tell()
                file.seek(0)
                if size > 1 * 1024 * 1024:
                    flash('Logo demasiado grande (máximo 1MB)')
                    return redirect(url_for('settings'))
                upload_dir = os.path.join(app.static_folder, 'uploads')
                os.makedirs(upload_dir, exist_ok=True)
                path = os.path.join(upload_dir, filename)
                file.save(path)
                company.logo = f'uploads/{filename}'

        old_final = company.ncf_final
        old_fiscal = company.ncf_fiscal
        new_final = _to_int(request.form.get('ncf_final'))
        new_fiscal = _to_int(request.form.get('ncf_fiscal'))
        if new_final is not None and new_final < old_final:
            flash('NCF Consumidor Final no puede ser menor que el actual')
            return redirect(url_for('settings'))
        if new_fiscal is not None and new_fiscal < old_fiscal:
            flash('NCF Comprobante Fiscal no puede ser menor que el actual')
            return redirect(url_for('settings'))
        if new_final is not None:
            company.ncf_final = new_final
        if new_fiscal is not None:
            company.ncf_fiscal = new_fiscal

        if old_final != company.ncf_final or old_fiscal != company.ncf_fiscal:
            log = NcfLog(
                company_id=company.id,
                old_final=old_final,
                old_fiscal=old_fiscal,
                new_final=company.ncf_final,
                new_fiscal=company.ncf_fiscal,
                changed_by=session.get('user_id'),
            )
            db.session.add(log)

        db.session.commit()
        flash('Ajustes guardados')
        return redirect(url_for('settings'))
    return render_template('ajustes.html', company=company)

@app.route('/cotizaciones/<int:quotation_id>/pdf')
def quotation_pdf(quotation_id):
    quotation = company_get(Quotation, quotation_id)
    company = get_company_info()
    filename = f'cotizacion_{quotation_id}.pdf'
    pdf_path = os.path.join(app.static_folder, 'pdfs', filename)
    os.makedirs(os.path.dirname(pdf_path), exist_ok=True)
    qr_url = request.url_root.rstrip('/') + url_for('serve_pdf', filename=filename)
    valid_until = quotation.date + timedelta(days=30)
    app.logger.info("Generating quotation PDF %s", quotation_id)
    generate_pdf('Cotización', company, quotation.client, quotation.items,
                 quotation.subtotal, quotation.itbis, quotation.total,
                 seller=quotation.seller, payment_method=quotation.payment_method,
                 bank=quotation.bank, doc_number=quotation.id, note=quotation.note,
                 output_path=pdf_path, qr_url=qr_url,
                 date=quotation.date, valid_until=valid_until,
                 footer=("Condiciones: Esta cotización es válida por 30 días a partir de la fecha de emisión. "
                         "Los precios están sujetos a cambios sin previo aviso. "
                         "El ITBIS ha sido calculado conforme a la ley vigente."))
    return send_file(pdf_path, download_name=filename, as_attachment=True)

@app.route('/cotizaciones/<int:quotation_id>/convertir')
def quotation_to_order(quotation_id):
    quotation = company_get(Quotation, quotation_id)
    if dom_now() > quotation.date + timedelta(days=30):
        flash('La cotización ha expirado')
        return redirect(url_for('list_quotations'))
    order = Order(
        client_id=quotation.client_id,
        quotation_id=quotation.id,
        subtotal=quotation.subtotal,
        itbis=quotation.itbis,
        total=quotation.total,
        seller=quotation.seller,
        payment_method=quotation.payment_method,
        bank=quotation.bank,
        note=quotation.note,
        company_id=current_company_id(),
    )
    db.session.add(order)
    db.session.flush()
    for item in quotation.items:
        o_item = OrderItem(
            order_id=order.id,
            code=item.code,
            reference=item.reference,
            product_name=item.product_name,
            unit=item.unit,
            unit_price=item.unit_price,
            quantity=item.quantity,
            discount=item.discount,
            category=item.category,
            has_itbis=item.has_itbis,
            company_id=current_company_id(),
        )
        db.session.add(o_item)
    db.session.commit()
    flash('Pedido creado')
    return redirect(url_for('list_orders'))

# Orders
@app.route('/pedidos')
def list_orders():
    q = request.args.get('q')
    query = company_query(Order).join(Client)
    if q:
        query = query.filter((Client.name.contains(q)) | (Client.identifier.contains(q)))
    orders = query.order_by(Order.date.desc()).all()
    return render_template('pedido.html', orders=orders, q=q)

@app.route('/pedidos/<int:order_id>/facturar')
def order_to_invoice(order_id):
    order = company_get(Order, order_id)
    company = CompanyInfo.query.get(current_company_id())
    if order.client.is_final_consumer:
        prefix, counter = "B02", "ncf_final"
    else:
        prefix, counter = "B01", "ncf_fiscal"

    # ensure NCF is unique; advance company counter until unused
    while True:
        seq = getattr(company, counter)
        ncf = f"{prefix}{seq:08d}"
        if not Invoice.query.filter_by(ncf=ncf).first():
            setattr(company, counter, seq + 1)
            break
        setattr(company, counter, seq + 1)
    invoice = Invoice(
        client_id=order.client_id,
        order_id=order.id,
        subtotal=order.subtotal,
        itbis=order.itbis,
        total=order.total,
        ncf=ncf,
        seller=order.seller,
        payment_method=order.payment_method,
        bank=order.bank,
        note=order.note,
        invoice_type=(
            'Consumidor Final' if order.client.is_final_consumer else 'Crédito Fiscal'
        ),
        status='Pendiente',
        company_id=current_company_id(),
    )
    db.session.add(invoice)
    db.session.flush()
    for item in order.items:
        i_item = InvoiceItem(
            invoice_id=invoice.id,
            code=item.code,
            reference=item.reference,
            product_name=item.product_name,
            unit=item.unit,
            unit_price=item.unit_price,
            quantity=item.quantity,
            discount=item.discount,
            category=item.category,
            has_itbis=item.has_itbis,
            company_id=current_company_id(),
        )
        db.session.add(i_item)
    order.status = 'Entregado'
    db.session.commit()
    flash('Factura generada')
    return redirect(url_for('list_invoices'))

@app.route('/pedidos/<int:order_id>/pdf')
def order_pdf(order_id):
    order = company_get(Order, order_id)
    company = get_company_info()
    filename = f'pedido_{order_id}.pdf'
    pdf_path = os.path.join(app.static_folder, 'pdfs', filename)
    os.makedirs(os.path.dirname(pdf_path), exist_ok=True)
    qr_url = request.url_root.rstrip('/') + url_for('serve_pdf', filename=filename)
    app.logger.info("Generating order PDF %s", order_id)
    generate_pdf('Pedido', company, order.client, order.items,
                 order.subtotal, order.itbis, order.total,
                 seller=order.seller, payment_method=order.payment_method,
                 bank=order.bank, doc_number=order.id, note=order.note,
                 output_path=pdf_path, qr_url=qr_url,
                date=order.date,
                footer=("Este pedido será procesado tras la confirmación de pago. "
                        "Tiempo estimado de entrega: 3 a 5 días hábiles."))
    return send_file(pdf_path, download_name=filename, as_attachment=True)

# Invoices
@app.route('/facturas')
def list_invoices():
    q = request.args.get('q')
    query = company_query(Invoice).join(Client)
    if q:
        query = query.filter((Client.name.contains(q)) | (Client.identifier.contains(q)))
    invoices = query.order_by(Invoice.date.desc()).all()
    return render_template('factura.html', invoices=invoices, q=q)


@app.route('/facturas/<int:invoice_id>/pagar', methods=['POST'])
def pay_invoice(invoice_id):
    invoice = company_get(Invoice, invoice_id)
    invoice.status = 'Pagada'
    db.session.commit()
    flash('Factura marcada como pagada')
    return redirect(url_for('list_invoices'))

@app.route('/facturas/<int:invoice_id>/pdf')
def invoice_pdf(invoice_id):
    invoice = company_get(Invoice, invoice_id)
    company = get_company_info()
    filename = f'factura_{invoice_id}.pdf'
    pdf_path = os.path.join(app.static_folder, 'pdfs', filename)
    os.makedirs(os.path.dirname(pdf_path), exist_ok=True)
    qr_url = request.url_root.rstrip('/') + url_for('serve_pdf', filename=filename)
    app.logger.info("Generating invoice PDF %s", invoice_id)
    generate_pdf('Factura', company, invoice.client, invoice.items,
                 invoice.subtotal, invoice.itbis, invoice.total,
                 ncf=invoice.ncf, seller=invoice.seller,
                 payment_method=invoice.payment_method, bank=invoice.bank,
                 order_number=invoice.order_id, doc_number=invoice.id,
                 invoice_type=invoice.invoice_type, note=invoice.note,
                 output_path=pdf_path, qr_url=qr_url, date=invoice.date,
                 footer=("Factura generada electrónicamente, válida sin firma ni sello. "
                         "Para reclamaciones favor comunicarse dentro de las 48 horas siguientes a la emisión. "
                         "Gracias por su preferencia."))
    return send_file(pdf_path, download_name=filename, as_attachment=True)

@app.route('/pdfs/<path:filename>')
def serve_pdf(filename):
    return send_from_directory(os.path.join(app.static_folder, 'pdfs'), filename)

def _filtered_invoice_query(fecha_inicio, fecha_fin, estado, categoria):
    """Return an invoice query filtered by the provided parameters."""
    q = company_query(Invoice)
    if fecha_inicio:
        q = q.filter(Invoice.date >= fecha_inicio)
    if fecha_fin:
        q = q.filter(Invoice.date <= fecha_fin)
    if estado:
        q = q.filter(Invoice.status == estado)
    if categoria:
        q = q.join(Invoice.items).filter(InvoiceItem.category == categoria)
    return q


@app.route('/reportes')
def reportes():
    fecha_inicio = request.args.get('fecha_inicio')
    fecha_fin = request.args.get('fecha_fin')
    estado = request.args.get('estado')
    categoria = request.args.get('categoria')
    page = request.args.get('page', 1, type=int)

    start, end, estado, categoria = _parse_report_params(fecha_inicio, fecha_fin, estado, categoria)
    q = _filtered_invoice_query(start, end, estado, categoria)

    pagination = (
        q.options(
            joinedload(Invoice.client),
            load_only(Invoice.client_id, Invoice.total, Invoice.date, Invoice.status),
        )
        .order_by(Invoice.date.desc())
        .paginate(page=page, per_page=10, error_out=False)
    )
    invoices = pagination.items

    all_invoices = q.options(
        load_only(Invoice.client_id, Invoice.total, Invoice.date, Invoice.status)
    ).all()
    total_sales = sum(i.total for i in all_invoices)
    unique_clients = len({i.client_id for i in all_invoices})

    item_query = company_query(InvoiceItem).join(Invoice)
    if start:
        item_query = item_query.filter(Invoice.date >= start)
    if end:
        item_query = item_query.filter(Invoice.date <= end)
    if estado:
        item_query = item_query.filter(Invoice.status == estado)
    if categoria:
        item_query = item_query.filter(InvoiceItem.category == categoria)

    sales_by_category = (
        item_query.with_entities(
            InvoiceItem.category,
            func.count(InvoiceItem.id),
            func.avg((InvoiceItem.unit_price * InvoiceItem.quantity) - InvoiceItem.discount),
            func.sum((InvoiceItem.unit_price * InvoiceItem.quantity) - InvoiceItem.discount),
        ).group_by(InvoiceItem.category).all()
    )

    sales_over_time = (
        q.with_entities(func.date(Invoice.date), func.sum(Invoice.total), func.count(Invoice.id))
        .group_by(func.date(Invoice.date))
        .order_by(func.date(Invoice.date))
        .all()
    )

    # retention
    client_counts = (
        q.with_entities(Invoice.client_id, func.count(Invoice.id))
        .group_by(Invoice.client_id)
        .all()
    )
    retained = len([1 for _cid, cnt in client_counts if cnt > 1])
    retention = (retained / len(client_counts)) * 100 if client_counts else 0

    # top categories last year
    last_year_start = datetime.utcnow().replace(year=datetime.utcnow().year - 1, month=1, day=1)
    top_cats = (
        company_query(InvoiceItem)
        .join(Invoice)
        .with_entities(InvoiceItem.category, func.sum((InvoiceItem.unit_price * InvoiceItem.quantity) - InvoiceItem.discount))
        .filter(Invoice.date >= last_year_start)
        .group_by(InvoiceItem.category)
        .order_by(func.sum((InvoiceItem.unit_price * InvoiceItem.quantity) - InvoiceItem.discount).desc())
        .limit(5)
        .all()
    )

    # monthly and yearly avg ticket
    today = datetime.utcnow()
    month_invoices = [i for i in all_invoices if i.date.month == today.month and i.date.year == today.year]
    month_total = sum(i.total for i in month_invoices)
    month_clients = len({i.client_id for i in month_invoices})
    avg_ticket_month = month_total / month_clients if month_clients else 0
    year_invoices = [i for i in all_invoices if i.date.year == today.year]
    year_total = sum(i.total for i in year_invoices)
    year_clients = len({i.client_id for i in year_invoices})
    avg_ticket_year = year_total / year_clients if year_clients else 0

    # trend last 24 months
    trend_query = (
        q.with_entities(func.strftime('%Y-%m', Invoice.date), func.sum(Invoice.total))
        .filter(Invoice.date >= datetime(today.year - 2, today.month, 1))
        .group_by(func.strftime('%Y-%m', Invoice.date))
        .order_by(func.strftime('%Y-%m', Invoice.date))
    )
    # ensure a list of dicts is always provided even if the query returns no rows
    trend_rows = trend_query.all() if trend_query is not None else []
    trend_24 = [{'month': m, 'total': tot or 0} for m, tot in trend_rows]

    status_totals = {s: 0 for s in INVOICE_STATUSES}
    status_counts = {s: 0 for s in INVOICE_STATUSES}
    for st, amount, cnt in (
        q.with_entities(Invoice.status, func.sum(Invoice.total), func.count(Invoice.id))
        .group_by(Invoice.status)
    ):
        if st in status_totals:
            status_totals[st] = amount or 0
            status_counts[st] = cnt or 0

    payment_totals = {'Efectivo': 0, 'Transferencia': 0}
    payment_counts = {'Efectivo': 0, 'Transferencia': 0}
    for pm, amount, cnt in (
        q.with_entities(Invoice.payment_method, func.sum(Invoice.total), func.count(Invoice.id))
        .group_by(Invoice.payment_method)
    ):
        if pm in payment_totals:
            payment_totals[pm] = amount or 0
            payment_counts[pm] = cnt or 0

    current_year = datetime.utcnow().year
    monthly_totals = (
        q.with_entities(
            func.strftime('%Y', Invoice.date).label('y'),
            func.strftime('%m', Invoice.date).label('m'),
            func.sum(Invoice.total),
        )
        .filter(Invoice.date >= datetime(current_year - 1, 1, 1))
        .group_by('y', 'm')
        .all()
    )
    year_current = [0] * 12
    year_prev = [0] * 12
    for y, m, total in monthly_totals:
        if int(y) == current_year:
            year_current[int(m) - 1] = total or 0
        else:
            year_prev[int(m) - 1] = total or 0

    avg_ticket = total_sales / unique_clients if unique_clients else 0

    top_clients = (
        q.join(Client)
        .with_entities(Client.name, func.sum(Invoice.total))
        .group_by(Client.id)
        .order_by(func.sum(Invoice.total).desc())
        .limit(5)
        .all()
    )

    stats = {
        'total_sales': total_sales,
        'unique_clients': unique_clients,
        'invoices': len(all_invoices),
        'pending': status_totals.get('Pendiente', 0),
        'paid': status_totals.get('Pagada', 0),
        'cash': payment_totals.get('Efectivo', 0),
        'transfer': payment_totals.get('Transferencia', 0),
        'avg_ticket': avg_ticket,
        'avg_ticket_month': avg_ticket_month,
        'avg_ticket_year': avg_ticket_year,
        'retention': retention,
    }

    cat_labels = [c or 'Sin categoría' for c, *_ in sales_by_category]
    cat_totals = [s or 0 for *_1, _2, s in sales_by_category]
    cat_counts = [qtd for _cat, qtd, *_ in sales_by_category]
    date_labels = [d if isinstance(d, str) else d.strftime('%Y-%m-%d') for d, *_ in sales_over_time]
    date_totals = [t or 0 for _, t, _ in sales_over_time]
    date_counts = [cnt for *_1, cnt in sales_over_time]
    status_labels = list(status_counts.keys())
    status_values = list(status_counts.values())
    method_labels = list(payment_counts.keys())
    method_values = list(payment_counts.values())
    months = [
        'Ene', 'Feb', 'Mar', 'Abr', 'May', 'Jun',
        'Jul', 'Ago', 'Sep', 'Oct', 'Nov', 'Dic'
    ]

    filters = {
        'fecha_inicio': fecha_inicio or '',
        'fecha_fin': fecha_fin or '',
        'estado': estado or '',
        'categoria': categoria or '',
    }

    if request.args.get('ajax') == '1':
        return jsonify(
            {
                'stats': stats,
                'top_clients': [{'name': n, 'total': t} for n, t in top_clients],
                'cat_labels': cat_labels,
                'cat_totals': cat_totals,
                'cat_counts': cat_counts,
                'date_labels': date_labels,
                'date_totals': date_totals,
                'date_counts': date_counts,
                'status_labels': status_labels,
                'status_values': status_values,
                'method_labels': method_labels,
                'method_values': method_values,
                'months': months,
                'year_current': year_current,
                'year_prev': year_prev,
                'top_categories_year': [{'category': c or 'Sin categoría', 'total': t or 0} for c, t in top_cats],
                'trend_24': trend_24,
                'invoices': [
                    {
                        'client': i.client.name if i.client else '',
                        'date': i.date.strftime('%Y-%m-%d'),
                        'estado': i.status or '',
                        'total': i.total,
                    }
                    for i in invoices
                ],
                'pagination': {'page': pagination.page, 'pages': pagination.pages},
            }
        )

    return render_template(
        'reportes.html',
        invoices=invoices,
        pagination=pagination,
        sales_by_category=sales_by_category,
        stats=stats,
        top_clients=top_clients,
        top_categories_year=top_cats,
        trend_24=trend_24,
        cat_labels=cat_labels,
        cat_totals=cat_totals,
        cat_counts=cat_counts,
        date_labels=date_labels,
        date_totals=date_totals,
        date_counts=date_counts,
        status_labels=status_labels,
        status_values=status_values,
        method_labels=method_labels,
        method_values=method_values,
        months=months,
        year_current=year_current,
        year_prev=year_prev,
        filters=filters,
        categories=CATEGORIES,
        statuses=INVOICE_STATUSES,
    )


@app.route('/reportes/export')
def export_reportes():
    role = session.get('role')
    formato = request.args.get('formato', 'csv')
    tipo = request.args.get('tipo', 'detalle')
    if role == 'contabilidad':
        if formato not in {'csv', 'xlsx'} or tipo != 'resumen':
            log_export(session.get('username'), formato, tipo, {}, 'fail', 'permiso')
            return '', 403
    elif role != 'admin':
        log_export(session.get('username'), formato, tipo, {}, 'fail', 'permiso')
        return '', 403

    fecha_inicio = request.args.get('fecha_inicio')
    fecha_fin = request.args.get('fecha_fin')
    estado = request.args.get('estado')
    categoria = request.args.get('categoria')

    start, end, estado, categoria = _parse_report_params(fecha_inicio, fecha_fin, estado, categoria)
    q = _filtered_invoice_query(start, end, estado, categoria)
    count = q.count()
    filtros = {'fecha_inicio': fecha_inicio, 'fecha_fin': fecha_fin, 'estado': estado, 'categoria': categoria}
    user = session.get('username')

    max_rows = current_app.config.get('MAX_EXPORT_ROWS', MAX_EXPORT_ROWS)
    if count > max_rows and request.args.get('async') != '1':
        log_export(user, formato, tipo, filtros, 'fail', 'too_many_rows')
        return jsonify({'error': 'too many rows', 'suggest': 'async'}), 400

    if count > max_rows and request.args.get('async') == '1':
        entry_id = log_export(user, formato, tipo, filtros, 'queued')
        enqueue_export(
            _export_job,
            current_company_id(),
            user,
            start,
            end,
            estado,
            categoria,
            formato,
            tipo,
            entry_id,
        )
        return jsonify({'job': entry_id})

    invoices = q.options(
        joinedload(Invoice.client),
        load_only(Invoice.client_id, Invoice.total, Invoice.date, Invoice.status),
    ).all()

    company = get_company_info()
    header = [
        f"Empresa: {company.get('name', '')}",
        f"Rango: {(fecha_inicio or 'Todas')} - {(fecha_fin or 'Todas')}",
        f"Generado: {datetime.utcnow().strftime('%Y-%m-%d %H:%M')} por {user}",
    ]
    current_app.logger.info(
        "export user=%s company=%s formato=%s tipo=%s filtros=%s",
        user,
        current_company_id(),
        formato,
        tipo,
        filtros,
    )

    if formato == 'csv':
        output = StringIO()
        writer = csv.writer(output)
        for h in header:
            writer.writerow([h])
        if tipo == 'resumen':
            writer.writerow(['Categoría', 'Cantidad', 'Total'])
            summary = (
                company_query(InvoiceItem)
                .join(Invoice)
                .with_entities(InvoiceItem.category, func.count(InvoiceItem.id), func.sum(InvoiceItem.unit_price * InvoiceItem.quantity - InvoiceItem.discount))
                .group_by(InvoiceItem.category)
            )
            if start:
                summary = summary.filter(Invoice.date >= start)
            if end:
                summary = summary.filter(Invoice.date <= end)
            if estado:
                summary = summary.filter(Invoice.status == estado)
            for cat, cnt, tot in summary:
                writer.writerow([cat or 'Sin categoría', cnt, f"{tot or 0:.2f}"])
        else:
            writer.writerow(['Cliente', 'Fecha', 'Estado', 'Total'])
            for inv in invoices:
                writer.writerow([
                    inv.client.name if inv.client else '',
                    inv.date.strftime('%Y-%m-%d'),
                    inv.status or '',
                    f"{inv.total:.2f}",
                ])
        mem = BytesIO()
        mem.write(output.getvalue().encode('utf-8'))
        mem.seek(0)
        log_export(user, formato, tipo, filtros, 'success')
        return send_file(mem, mimetype='text/csv', as_attachment=True, download_name='reportes.csv')

    if formato == 'xlsx':
        if Workbook is None:
            mem = BytesIO()
            mem.write(b'')
            mem.seek(0)
            return send_file(mem, mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet', as_attachment=True, download_name='reportes.xlsx')
        wb = Workbook()
        ws = wb.active
        row = 1
        for h in header:
            ws.cell(row=row, column=1, value=h)
            row += 1
        if tipo == 'resumen':
            ws.append(['Categoría', 'Cantidad', 'Total'])
            summary = (
                company_query(InvoiceItem)
                .join(Invoice)
                .with_entities(InvoiceItem.category, func.count(InvoiceItem.id), func.sum(InvoiceItem.unit_price * InvoiceItem.quantity - InvoiceItem.discount))
                .group_by(InvoiceItem.category)
            )
            if start:
                summary = summary.filter(Invoice.date >= start)
            if end:
                summary = summary.filter(Invoice.date <= end)
            if estado:
                summary = summary.filter(Invoice.status == estado)
            for cat, cnt, tot in summary:
                ws.append([cat or 'Sin categoría', cnt, float(tot or 0)])
        else:
            ws.append(['Cliente', 'Fecha', 'Estado', 'Total'])
            for inv in invoices:
                ws.append([
                    inv.client.name if inv.client else '',
                    inv.date.strftime('%Y-%m-%d'),
                    inv.status or '',
                    float(inv.total),
                ])
        mem = BytesIO()
        wb.save(mem)
        mem.seek(0)
        log_export(user, formato, tipo, filtros, 'success')
        return send_file(
            mem,
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            as_attachment=True,
            download_name='reportes.xlsx',
        )

    if formato == 'pdf':
        items = [
            {
                'code': inv.id,
                'reference': inv.client.name if inv.client else '',
                'product_name': '',
                'unit': '',
                'unit_price': inv.total,
                'quantity': 1,
                'discount': 0,
            }
            for inv in invoices
        ]
        subtotal = sum(inv.total for inv in invoices)
        note = f"Rango: {(fecha_inicio or 'Todas')} - {(fecha_fin or 'Todas')} | Usuario: {user}"
        pdf_path = generate_pdf(
            'Reporte de Facturas',
            company,
            {'name': '', 'address': '', 'phone': ''},
            items,
            subtotal,
            0,
            subtotal,
            note=note,
            output_path='reportes.pdf'
        )
        log_export(user, formato, tipo, filtros, 'success', file_path=pdf_path)
    return send_file(pdf_path, as_attachment=True, download_name='reportes.pdf')

    return redirect(url_for('reportes'))


@app.route('/reportes/exportes')
def export_history():
    q = company_query(ExportLog).order_by(ExportLog.created_at.desc())
    usuario = request.args.get('usuario')
    formato = request.args.get('formato')
    if usuario:
        q = q.filter(ExportLog.user == usuario)
    if formato:
        q = q.filter(ExportLog.formato == formato)
    logs = q.limit(100).all()
    return render_template('export_history.html', logs=logs)


@app.route('/docs')
def docs():
    return render_template('docs.html')


@app.route('/contabilidad')
def contabilidad():
    return render_template('contabilidad.html')


@app.route('/contabilidad/catalogo')
def contab_catalogo():
    return render_template('contabilidad_catalogo.html')


@app.route('/contabilidad/entradas')
def contab_entradas():
    return render_template('contabilidad_entradas.html')


@app.route('/contabilidad/estados')
def contab_estados():
    return render_template('contabilidad_estados.html')


@app.route('/contabilidad/libro-mayor')
def contab_libro_mayor():
    return render_template('contabilidad_libro_mayor.html')


@app.route('/contabilidad/impuestos')
def contab_impuestos():
    return render_template('contabilidad_impuestos.html')


@app.route('/contabilidad/balanza')
def contab_balanza():
    return render_template('contabilidad_balanza.html')


@app.route('/contabilidad/asignacion')
def contab_asignacion():
    return render_template('contabilidad_asignacion.html')


@app.route('/contabilidad/centro-costo')
def contab_centro_costo():
    return render_template('contabilidad_centro_costo.html')


@app.route('/contabilidad/reportes')
def contab_reportes():
    return render_template('contabilidad_reportes.html')


@app.route('/contabilidad/dgii')
def contab_dgii():
    return render_template('contabilidad_dgii.html')


@app.route('/api/recommendations')
def api_recommendations():
    """Return top product recommendations based on past orders."""
    return jsonify({'products': recommend_products()})

if __name__ == '__main__':
    with app.app_context():
        ensure_admin()
    app.run(debug=True)
