from flask import Blueprint

cotizaciones_bp = Blueprint('cotizaciones', __name__, url_prefix='/cotizaciones')

@cotizaciones_bp.route('/')
def lista_cotizaciones():
    return 'cotizaciones'

@cotizaciones_bp.route('/nueva')
def nueva_cotizacion():
    return 'nueva cotizacion'
