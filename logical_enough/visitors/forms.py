import wtforms as f
from flask_wtf import FlaskForm


class LoginForm(FlaskForm):
    login = f.StringField('Login', validators=[f.validators.InputRequired()])
    login_button = f.SubmitField('Login')
