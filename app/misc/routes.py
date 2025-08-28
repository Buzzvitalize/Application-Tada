from flask import Blueprint, render_template

misc_bp = Blueprint('misc', __name__, template_folder='../../templates')

@misc_bp.route('/cpanel')
def cpanel():
    return render_template('cpaneltx.html')

@misc_bp.route('/cpanel/companies')
def cpanel_companies():
    return render_template('cpanel_companies.html')

@misc_bp.route('/cpanel/users')
def cpanel_users():
    return render_template('cpanel_users.html')

@misc_bp.route('/cpanel/orders')
def cpanel_orders():
    return render_template('cpanel_orders.html')

@misc_bp.route('/cpanel/invoices')
def cpanel_invoices():
    return render_template('cpanel_invoices.html')

@misc_bp.route('/pedido')
def pedido():
    return render_template('pedido.html')

@misc_bp.route('/ajustes')
def ajustes():
    return render_template('ajustes_empresa.html', company={})

@misc_bp.route('/notificaciones')
def notifications():
    return render_template('notifications.html')

@misc_bp.route('/inventario')
def inventario():
    return render_template('inventario.html', stocks=[], warehouses=[], sales_total=0)

@misc_bp.route('/contabilidad')
def contabilidad():
    return render_template('contabilidad.html')
