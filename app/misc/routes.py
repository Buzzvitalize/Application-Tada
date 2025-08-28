from flask import Blueprint, render_template, session, redirect, url_for
from functools import wraps

misc_bp = Blueprint('misc', __name__, template_folder='../../templates')


def admin_required(f):
    @wraps(f)
    def wrapped(*args, **kwargs):
        if session.get('role') != 'admin':
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    return wrapped

@misc_bp.route('/cpanel')
@admin_required
def cpanel():
    return render_template('cpaneltx.html')

@misc_bp.route('/cpanel/companies')
@admin_required
def cpanel_companies():
    return render_template('cpanel_companies.html')

@misc_bp.route('/cpanel/users')
@admin_required
def cpanel_users():
    return render_template('cpanel_users.html')

@misc_bp.route('/cpanel/orders')
@admin_required
def cpanel_orders():
    return render_template('cpanel_orders.html')

@misc_bp.route('/cpanel/invoices')
@admin_required
def cpanel_invoices():
    return render_template('cpanel_invoices.html')

@misc_bp.route('/ajustes')
@misc_bp.route('/adjustes')
@admin_required
def ajustes():
    return render_template('ajustes_empresa.html', company={})

@misc_bp.route('/notificaciones')
def notifications():
    return render_template('notifications.html')

@misc_bp.route('/solicitudes')
@misc_bp.route('/admin/solicitudes')
def solicitudes():
    return render_template('admin_solicitudes.html')
