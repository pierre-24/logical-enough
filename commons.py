from flask import Flask
from flask_restful import Api
from flask_sqlalchemy import SQLAlchemy

import settings


# create and configure app:
db = SQLAlchemy()


def create_app():
    # app
    _app = Flask(__name__)
    _app.config.update(settings.APP_SETTINGS)
    db.init_app(_app)

    # api
    _api = Api(_app)

    return _app, _api
