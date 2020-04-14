from flask_wtf import FlaskForm
import wtforms as f


class UserForm(FlaskForm):
    login = f.StringField('Login', validators=[f.validators.InputRequired()])
    is_admin = f.BooleanField('Est admin')
    add_button = f.SubmitField('Ajouter un nouvel utilisateur')


class ChallengeForm(FlaskForm):
    name = f.StringField('Nom du challenge', validators=[f.validators.InputRequired()])
    add_button = f.SubmitField('Ajouter un nouveau challenge')


class QuestionForm(FlaskForm):
    hint_expr = f.StringField('Expression de recherche', validators=[f.validators.InputRequired()])
    hint = f.TextAreaField('Aide')
    documents = f.StringField('Documents')
    add_button = f.SubmitField('Valider')