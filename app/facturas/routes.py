from flask import Blueprint, render_template, request

facturas_bp = Blueprint('facturas', __name__, url_prefix='/facturas', template_folder='../../templates')

@facturas_bp.route('/')
def index():
    q = request.args.get('q')
    invoices = []
    return render_template('facturas.html', invoices=invoices, q=q)
