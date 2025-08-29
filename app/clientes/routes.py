from flask import Blueprint, render_template, redirect, url_for, request, jsonify
from ..models import db, Client, CompanyInfo
from ..forms import ClientForm

clientes_bp = Blueprint('clientes', __name__, url_prefix='/clientes',
                        template_folder='../../templates')


@clientes_bp.route('/', methods=['GET', 'POST'])
def index():
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
        return redirect(url_for('clientes.index'))
    clients = Client.query.all()
    return render_template('clientes.html', clients=clients, form=form)


@clientes_bp.route('/edit/<int:id>', methods=['GET', 'POST'])
def edit(id):
    client = Client.query.get_or_404(id)
    form = ClientForm(obj=client)
    if form.validate_on_submit():
        form.populate_obj(client)
        db.session.commit()
        return redirect(url_for('clientes.index'))
    return render_template('cliente_form.html', form=form)


@clientes_bp.route('/delete/<int:id>', methods=['POST'])
def delete(id):
    client = Client.query.get_or_404(id)
    db.session.delete(client)
    db.session.commit()
    return redirect(url_for('clientes.index'))


@clientes_bp.route('/api')
def api_clients():
    data = [{'id': c.id, 'name': c.name, 'identifier': c.identifier}
            for c in Client.query.all()]
    return jsonify(data)
