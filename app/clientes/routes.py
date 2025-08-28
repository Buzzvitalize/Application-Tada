from flask import Blueprint, render_template, redirect, url_for
from ..models import db, Client, CompanyInfo
from ..forms import ClientForm

clientes_bp = Blueprint('clientes', __name__, url_prefix='/clientes', template_folder='../../templates')

@clientes_bp.route('/nuevo', methods=['GET', 'POST'])
def nuevo():
    form = ClientForm()
    if form.validate_on_submit():
        company = CompanyInfo.query.first()
        if not company:
            company = CompanyInfo(name='Demo Co')
            db.session.add(company)
            db.session.commit()
        client = Client(name=form.name.data,
                        email=form.email.data,
                        identifier=form.identifier.data,
                        phone=form.phone.data,
                        street=form.street.data,
                        sector=form.sector.data,
                        province=form.province.data,
                        company_id=company.id)
        db.session.add(client)
        db.session.commit()
        return redirect(url_for('clientes.lista'))
    return render_template('cliente_form.html', form=form)


@clientes_bp.route('/')
def lista():
    clients = Client.query.all()
    return render_template('clientes.html', clients=clients)
