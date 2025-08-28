from flask import Blueprint, render_template, redirect, url_for, session, request, flash
from ..forms import LoginForm

auth_bp = Blueprint('auth', __name__)


@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        if form.username.data == 'admin' and form.password.data == '363636':
            session['user'] = form.username.data
            return redirect(url_for('clientes.lista'))
        flash('Credenciales inválidas', 'login')
    return render_template('login.html', form=form)


@auth_bp.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('auth.login'))


@auth_bp.route('/solicitar-cuenta')
def request_account():
    return 'solicitar'
