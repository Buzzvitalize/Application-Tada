from flask import Blueprint

reportes_bp = Blueprint('reportes', __name__, url_prefix='/reportes')

@reportes_bp.route('/')
def ver_reportes():
    return 'reportes'
