from flask_wtf import FlaskForm
from wtforms import BooleanField, PasswordField, StringField, SubmitField
from wtforms.validators import DataRequired

class LoginForm(FlaskForm):
    username = StringField('Usuario', validators=[DataRequired()])
    password = PasswordField('PIN', validators=[DataRequired()])
    submit = SubmitField('Entrar')


class ResetRequestForm(FlaskForm):
    email = StringField('Email', validators=[DataRequired()])
    submit = SubmitField('Enviar')


class AccountRequestForm(FlaskForm):
    """Form for account requests, primarily for CSRF protection."""
    accepted_terms = BooleanField(
        "He leído y acepto los Términos y Condiciones",
        validators=[
            DataRequired(
                message="Debe aceptar los Términos y Condiciones para crear una cuenta en Tiendix."
            )
        ],
    )
