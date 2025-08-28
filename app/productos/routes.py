from flask import Blueprint

productos_bp = Blueprint('productos', __name__, url_prefix='/productos')

@productos_bp.route('/')
def lista_productos():
    return 'productos'
