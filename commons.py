from flask import Flask
from flask_restful import Api
from flask_sqlalchemy import SQLAlchemy
from flask_bootstrap import Bootstrap, WebCDN

from sqlalchemy.engine import Engine
from sqlalchemy import event

import settings


# create and configure app:
db = SQLAlchemy()


@event.listens_for(Engine, 'connect')
def set_sqlite_pragma(dbapi_connection, connection_record):
    cursor = dbapi_connection.cursor()
    cursor.execute('PRAGMA foreign_keys=ON')
    cursor.close()


def create_app():
    # app
    _app = Flask(__name__)
    _app.config.update(settings.APP_SETTINGS)

    # bootstrap
    Bootstrap(_app)
    _app.extensions['bootstrap']['cdns']['jquery'] = WebCDN('//cdnjs.cloudflare.com/ajax/libs/jquery/3.2.1/')

    # sqlalchemy
    db.init_app(_app)

    # api
    _api = Api(_app)

    return _app, _api
