from commons import db


class User(db.Model):
    """An user"""

    id = db.Column(db.Integer, primary_key=True)
    eid = db.Column(db.Text)
    is_admin = db.Column(db.Boolean, default=False)

    def __init__(self, name, is_admin=False):
        self.eid = name
        self.is_admin = is_admin


class Challenge(db.Model):
    """A challenge"""

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.Text)
    is_public = db.Column(db.Boolean)

    def __init__(self, name, is_public=False):
        self.name = name
        self.is_public = is_public


class UserChallenge(db.Model):

    id = db.Column(db.Integer, primary_key=True)
    user = db.Column(db.Integer, db.ForeignKey(User.id))
    challenge = db.Column(db.Integer, db.ForeignKey(Challenge.id))
    is_done = db.Column(db.Boolean, default=False)

    def __init__(self, user, challenge, is_done=False):
        self.user = user
        self.challenge = challenge
        self.is_done = is_done


class Question(db.Model):

    id = db.Column(db.Integer, primary_key=True)
    challenge = db.Column(db.Integer, db.ForeignKey(Challenge.id))
    position = db.Column(db.Integer)
    wrong_documents = db.Column(db.Text)
    good_documents = db.Column(db.Text)
    hint = db.Column(db.Text, default='')
    hint_expr = db.Column(db.Text, default='')

    def __init__(self, challenge, position, wrong_docs, good_docs, hint='', hint_expr=''):
        self.challenge = challenge
        self.position = position
        self.wrong_documents = wrong_docs
        self.good_documents = good_docs
        self.hint = hint
        self.hint_expr = hint_expr


class Answer(db.Model):

    id = db.Column(db.Integer, primary_key=True)
    challenge = db.Column(db.Integer, db.ForeignKey(Question.id))
    answer = db.Column(db.Text)

    def __init__(self, question, answer):
        self.question = question
        self.answer = answer
