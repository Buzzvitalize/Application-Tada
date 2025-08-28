from flask import Blueprint, render_template, redirect, url_for, session, request, flash
from ..forms import LoginForm
from ..models import CompanyInfo

auth_bp = Blueprint('auth', __name__, template_folder='../../templates')


@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    company = CompanyInfo.query.first()
    form = LoginForm()
    if form.validate_on_submit():
        if form.username.data == 'admin' and form.password.data == '363636':
            session['user'] = form.username.data
            return redirect(url_for('clientes.lista'))
        flash('Credenciales inválidas', 'login')
    return render_template('login.html', form=form, company=company)


@auth_bp.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('auth.login'))


@auth_bp.route('/solicitar')
def request_account():
    return render_template('solicitar_cuenta.html')
