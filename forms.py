from flask_wtf import FlaskForm
import wtforms as f


class LoginForm(FlaskForm):
    login = f.StringField("eID de l'UNamur", validators=[f.validators.InputRequired()])

    login_button = f.SubmitField('Login')


class UserForm(FlaskForm):
    eid = f.StringField("eID de l'UNamur", validators=[f.validators.InputRequired()])
    is_admin = f.BooleanField('Est admin')
    add_button = f.SubmitField('Ajouter un nouvel utilisateur')


class ChallengeForm(FlaskForm):
    name = f.StringField('Nom du challenge', validators=[f.validators.InputRequired()])
    add_button = f.SubmitField('Ajouter un nouveau challenge')
