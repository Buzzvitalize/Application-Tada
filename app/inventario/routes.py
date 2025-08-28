from flask import Blueprint, render_template

inventario_bp = Blueprint('inventario', __name__, url_prefix='/inventario', template_folder='../../templates')

@inventario_bp.route('/')
def index():
    return render_template('inventario.html', stocks=[], sales_total=0)
