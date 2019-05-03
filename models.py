from commons import db


class User(db.Model):
    """An user"""

    id = db.Column(db.Integer, primary_key=True)
    eid = db.Column(db.Text)
    is_admin = db.Column(db.Boolean, default=False)

    def __init__(self, name, is_admin=False):
        self.eid = name
        self.is_admin = is_admin
