from flask import Blueprint

clientes_bp = Blueprint('clientes', __name__, url_prefix='/clientes')

@clientes_bp.route('/')
def lista_clientes():
    return 'clientes'
