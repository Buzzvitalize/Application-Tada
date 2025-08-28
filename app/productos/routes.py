from flask import Blueprint, render_template, redirect, url_for
from ..models import db, Product, CompanyInfo
from ..forms import ProductForm

productos_bp = Blueprint('productos', __name__, url_prefix='/productos')

UNITS = ['Unidad', 'Metro', 'Onza']
CATEGORIES = ['Servicios', 'Consumo', 'Líquido']

@productos_bp.route('/nuevo', methods=['GET', 'POST'])
def nuevo():
    form = ProductForm()
    if form.validate_on_submit():
        company = CompanyInfo.query.first()
        if not company:
            company = CompanyInfo(name='Demo Co')
            db.session.add(company)
            db.session.commit()
        product = Product(name=form.name.data,
                          unit=form.unit.data,
                          code=form.code.data,
                          reference=form.reference.data,
                          price=form.price.data or 0,
                          category=form.category.data,
                          has_itbis=bool(form.has_itbis.data),
                          company_id=company.id)
        db.session.add(product)
        db.session.commit()
        return redirect(url_for('productos.lista'))
    return render_template('producto_form.html', form=form, units=UNITS, categories=CATEGORIES)


@productos_bp.route('/')
def lista():
    products = Product.query.all()
    return render_template('productos.html', products=products)
