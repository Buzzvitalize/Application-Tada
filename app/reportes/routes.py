from flask import Blueprint, render_template
from types import SimpleNamespace

reportes_bp = Blueprint('reportes', __name__, url_prefix='/reportes', template_folder='../../templates')

@reportes_bp.route('/')
def index():
    filters = {'fecha_inicio': '', 'fecha_fin': '', 'estado': '', 'categoria': ''}
    stats = SimpleNamespace(total_sales=0, unique_clients=0, invoices=0, pending=0, paid=0,
                            cash=0, transfer=0, avg_ticket=0, avg_ticket_month=0,
                            avg_ticket_year=0, retention=0)
    pagination = SimpleNamespace(page=1, pages=1)
    return render_template(
        'reportes.html',
        filters=filters,
        statuses=[],
        categories=[],
        stats=stats,
        pagination=pagination,
        invoices=[],
        sales_by_category=[],
        top_clients=[],
        trend_monthly=[],
        trend_24=[],
        data=[],
        cat_labels=[],
        cat_totals=[],
        date_counts=[],
        date_labels=[],
        date_totals=[],
        status_labels=[],
        status_values=[],
        months=[],
        year_current=[],
        year_prev=[],
        method_labels=[],
        method_values=[],
    )


@reportes_bp.route('/estado-cuentas')
def account_statement_clients():
    return ''


@reportes_bp.route('/export/inventario')
def export_inventory():
    return ''


@reportes_bp.route('/export/historial')
def export_history():
    return ''


@reportes_bp.route('/export')
def export_reportes():
    return ''
