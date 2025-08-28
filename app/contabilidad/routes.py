from flask import Blueprint, render_template

contabilidad_bp = Blueprint('contabilidad', __name__, url_prefix='/contabilidad', template_folder='../../templates')

@contabilidad_bp.route('/')
def index():
    return render_template('contabilidad.html')
