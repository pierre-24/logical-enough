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

    def get_questions(self):
        return Question.query.filter(Question.challenge.is_(self.id)).all()


class Question(db.Model):

    id = db.Column(db.Integer, primary_key=True)
    challenge = db.Column(db.Integer, db.ForeignKey(Challenge.id, ondelete='CASCADE'))
    position = db.Column(db.Integer)
    wrong_documents = db.Column(db.Text)
    good_documents = db.Column(db.Text)
    hint = db.Column(db.Text, default='')
    hint_expr = db.Column(db.Text, default='')

    SEP = ';'

    def __init__(self, challenge, hint_expr, wrong_docs, good_docs, hint='', position=0):
        self.challenge = challenge
        self.position = position
        self.wrong_documents = Question.SEP.join(wrong_docs) if type(wrong_docs) is list else wrong_docs
        self.good_documents = Question.SEP.join(good_docs) if type(good_docs) is list else good_docs
        self.hint = hint
        self.hint_expr = hint_expr

    def get_documents(self):
        d = self.get_good_documents()
        d.extend(self.get_wrong_documents())
        return d

    def get_good_documents(self):
        return self.good_documents.split(Question.SEP)

    def get_wrong_documents(self):
        return self.wrong_documents.split(Question.SEP)


class UserChallenge(db.Model):

    id = db.Column(db.Integer, primary_key=True)
    user = db.Column(db.Integer, db.ForeignKey(User.id, ondelete='CASCADE'))
    challenge = db.Column(db.Integer, db.ForeignKey(Challenge.id, ondelete='CASCADE'))
    is_done = db.Column(db.Boolean, default=False)
    current_question = db.Column(db.Integer, db.ForeignKey(Question.id, ondelete='CASCADE'), nullable=True)

    def __init__(self, user, challenge, current_question, is_done=False):
        self.user = user
        self.challenge = challenge
        self.is_done = is_done
        self.current_question = current_question


class Answer(db.Model):

    id = db.Column(db.Integer, primary_key=True)
    question = db.Column(db.Integer, db.ForeignKey(Question.id, ondelete='CASCADE'))
    answer = db.Column(db.Text)
    user = db.Column(db.Integer, db.ForeignKey(User.id, ondelete='CASCADE'))

    def __init__(self, user, question, answer):
        self.user = user
        self.question = question
        self.answer = answer
