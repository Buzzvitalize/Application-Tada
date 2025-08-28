from flask import Blueprint

facturas_bp = Blueprint('facturas', __name__, url_prefix='/facturas')

@facturas_bp.route('/')
def lista_facturas():
    return 'facturas'
