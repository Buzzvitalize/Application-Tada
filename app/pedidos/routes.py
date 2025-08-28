from flask import Blueprint, render_template

pedidos_bp = Blueprint('pedidos', __name__, url_prefix='/pedidos', template_folder='../../templates')

@pedidos_bp.route('/')
def index():
    return render_template('pedido.html', orders=[], q=None)
