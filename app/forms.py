try:
    from flask_wtf import FlaskForm
    from wtforms import StringField, PasswordField, SubmitField
    from wtforms.validators import DataRequired
except ModuleNotFoundError:  # pragma: no cover
    from flask import request

    class FlaskForm:
        def validate_on_submit(self):
            return request.method == 'POST'

        def hidden_tag(self):
            return ''

    class _Field:
        def __init__(self, *args, **kwargs):
            self.data = ''

        def __call__(self, *args, **kwargs):
            return ''

    StringField = PasswordField = SubmitField = _Field

    def DataRequired():
        return None

class LoginForm(FlaskForm):
    username = StringField('Usuario', validators=[DataRequired()])
    password = PasswordField('PIN', validators=[DataRequired()])
    submit = SubmitField('Entrar')
