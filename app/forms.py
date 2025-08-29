try:
    from flask_wtf import FlaskForm
    from wtforms import (StringField, PasswordField, SubmitField, FloatField,
                         BooleanField)
    from wtforms.validators import DataRequired, Email
except ModuleNotFoundError:  # pragma: no cover
    from flask import request, session, abort

    class _Field:
        def __init__(self, label='', validators=None):
            self.label = label
            self.validators = validators or []
            self.data = ''

        def __call__(self, *args, **kwargs):
            return ''

    def DataRequired():
        return 'required'

    def Email():
        return 'email'

    class FlaskForm:
        def validate_on_submit(self):
            if request.method != 'POST':
                return False
            return self.validate()

        def validate(self):
            for name, field in self.__class__.__dict__.items():
                if isinstance(field, _Field):
                    val = request.form.get(name, '')
                    if 'required' in field.validators and not val:
                        return False
                    if 'email' in field.validators and '@' not in val:
                        return False
            return True

        def hidden_tag(self):
            token = session.get('csrf_token', 'stub-token')
            session['csrf_token'] = token
            return f'<input type="hidden" name="csrf_token" value="{token}">'  

    StringField = PasswordField = SubmitField = FloatField = BooleanField = _Field

class LoginForm(FlaskForm):
    username = StringField('Usuario', validators=[DataRequired()])
    password = PasswordField('PIN', validators=[DataRequired()])
    submit = SubmitField('Entrar')


class ClientForm(FlaskForm):
    name = StringField('Nombre', validators=[DataRequired()])
    email = StringField('Email')
    identifier = StringField('Identificador')
    phone = StringField('Teléfono')
    street = StringField('Calle')
    sector = StringField('Sector')
    province = StringField('Provincia')


class ProductForm(FlaskForm):
    name = StringField('Nombre', validators=[DataRequired()])
    unit = StringField('Unidad', validators=[DataRequired()])
    code = StringField('Código', validators=[DataRequired()])
    reference = StringField('Referencia')
    price = FloatField('Precio', validators=[DataRequired()])
    category = StringField('Categoría', validators=[DataRequired()])
    has_itbis = BooleanField('Aplicar ITBIS')
