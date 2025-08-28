from flask import Blueprint, render_template
auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/login')
def login():
    return 'login'

@auth_bp.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('auth.login'))
