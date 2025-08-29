from flask import Blueprint, render_template

pedidos_bp = Blueprint('pedidos', __name__, url_prefix='/pedidos',
                       template_folder='../../templates')


@pedidos_bp.route('/')
def index():
    return render_template('pedido.html', orders=[], q=None)


@pedidos_bp.route('/<int:id>/facturar')
def facturar(id):
    return render_template('factura.html', invoice={}, items=[])


@pedidos_bp.route('/<int:id>/pdf')
def pdf(id):
    return '', 204
