from flask import Blueprint, render_template, redirect, url_for, flash, session, request
from forms import LoginForm
from models import User

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        username = getattr(getattr(form, 'username', None), 'data', None) or request.form.get('username')
        password = getattr(getattr(form, 'password', None), 'data', None) or request.form.get('password')
        user = User.query.filter_by(username=username).first()
        if user and user.check_password(password):
            session['user_id'] = user.id
            session['role'] = user.role
            session['company_id'] = user.company_id
            return redirect(url_for('index'))
        flash('Credenciales inválidas', 'login')
    return render_template('login.html', form=form, company=None)

@auth_bp.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('auth.login'))
