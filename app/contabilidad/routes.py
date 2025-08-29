from flask import Blueprint, render_template

contabilidad_bp = Blueprint('contabilidad', __name__, url_prefix='/contabilidad',
                            template_folder='../../templates')


@contabilidad_bp.route('/')
def index():
    return render_template('contabilidad.html')


@contabilidad_bp.route('/catalogo')
def catalogo():
    return render_template('contabilidad_catalogo.html')


@contabilidad_bp.route('/entradas')
def entradas():
    return render_template('contabilidad_entradas.html')


@contabilidad_bp.route('/estados')
def estados():
    return render_template('contabilidad_estados.html')


@contabilidad_bp.route('/libro-mayor')
def libro_mayor():
    return render_template('contabilidad_libro_mayor.html')


@contabilidad_bp.route('/impuestos')
def impuestos():
    return render_template('contabilidad_impuestos.html')


@contabilidad_bp.route('/balanza')
def balanza():
    return render_template('contabilidad_balanza.html')


@contabilidad_bp.route('/asignacion')
def asignacion():
    return render_template('contabilidad_asignacion.html')


@contabilidad_bp.route('/centro-costo')
def centro_costo():
    return render_template('contabilidad_centro_costo.html')


@contabilidad_bp.route('/reportes')
def reportes():
    return render_template('contabilidad_reportes.html')


@contabilidad_bp.route('/dgii')
def dgii():
    return render_template('contabilidad_dgii.html')
