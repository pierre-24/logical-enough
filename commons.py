from flask import Flask
from flask_restful import Api

import settings


def create_app():
    _app = Flask(__name__)
    _app.config.update(settings.APP_SETTINGS)

    _api = Api(_app)
    return _app, _api
