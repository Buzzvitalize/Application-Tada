from flask import Blueprint, render_template, session, redirect, url_for
from functools import wraps

ajustes_bp = Blueprint('ajustes', __name__, url_prefix='/ajustes',
                       template_folder='../../templates')

def admin_required(f):
    @wraps(f)
    def wrapped(*a, **k):
        if session.get('role') != 'admin':
            return redirect(url_for('auth.login'))
        return f(*a, **k)
    return wrapped

@ajustes_bp.route('/')
@admin_required
def index():
    return render_template('ajustes_empresa.html', company={})
