from flask import Blueprint, render_template, request
from datetime import datetime, timedelta

cotizaciones_bp = Blueprint('cotizaciones', __name__, url_prefix='/cotizaciones', template_folder='../../templates')

@cotizaciones_bp.route('/')
def index():
    q = request.args.get('q')
    quotations = []
    return render_template('cotizaciones.html', quotations=quotations, q=q, now=datetime.utcnow(), timedelta=timedelta)

@cotizaciones_bp.route('/nueva', methods=['GET', 'POST'])
def nueva_cotizacion():
    return render_template('cotizacion.html')
