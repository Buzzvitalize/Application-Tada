from flask import Blueprint, render_template, session, redirect, url_for
from functools import wraps

cpanel_bp = Blueprint('cpanel', __name__, url_prefix='/cpanel',
                      template_folder='../../templates')

def admin_required(f):
    @wraps(f)
    def wrapped(*a, **k):
        if session.get('role') != 'admin':
            return redirect(url_for('auth.login'))
        return f(*a, **k)
    return wrapped

@cpanel_bp.route('/')
@admin_required
def index():
    return render_template('cpaneltx.html')

@cpanel_bp.route('/users')
@admin_required
def users():
    return render_template('cpanel_users.html')

@cpanel_bp.route('/companies')
@admin_required
def companies():
    return render_template('cpanel_companies.html')

@cpanel_bp.route('/orders')
@admin_required
def orders():
    return render_template('cpanel_orders.html')

@cpanel_bp.route('/invoices')
@admin_required
def invoices():
    return render_template('cpanel_invoices.html')
