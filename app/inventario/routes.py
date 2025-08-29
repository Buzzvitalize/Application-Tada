from flask import Blueprint, render_template

inventario_bp = Blueprint('inventario', __name__, url_prefix='/inventario',
                          template_folder='../../templates')


@inventario_bp.route('/')
def index():
    return render_template('inventario.html', stocks=[], sales_total=0)


@inventario_bp.route('/ajustar')
def ajustar():
    return render_template('inventario_ajuste.html')


@inventario_bp.route('/importar', methods=['GET', 'POST'])
def importar():
    return render_template('inventario_importar.html')


@inventario_bp.route('/transferir', methods=['GET', 'POST'])
def transferir():
    return render_template('inventario_transferir.html')


@inventario_bp.route('/almacenes')
def almacenes():
    return render_template('almacenes.html')
