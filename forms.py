from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField
from wtforms.validators import DataRequired

class LoginForm(FlaskForm):
    username = StringField('Usuario', validators=[DataRequired()])
    password = PasswordField('PIN', validators=[DataRequired()])
    submit = SubmitField('Entrar')


class AccountRequestForm(FlaskForm):
    """Simple form used solely for CSRF protection when requesting accounts."""
    pass
