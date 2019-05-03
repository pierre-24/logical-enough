from flask_wtf import FlaskForm
import wtforms as f


class LoginForm(FlaskForm):
    login = f.StringField("eID de l'UNamur", validators=[f.validators.InputRequired()])

    login_button = f.SubmitField('Login')
