import os
import shutil
import random
import click

from flask import Flask
from flask.cli import with_appcontext

from flask_restful import Api
from flask_sqlalchemy import SQLAlchemy
from flask_bootstrap import Bootstrap, WebCDN

from sqlalchemy.engine import Engine
from sqlalchemy import event

from logical_enough import settings


# create db
db = SQLAlchemy()


@event.listens_for(Engine, 'connect')
def set_sqlite_pragma(dbapi_connection, connection_record):
    cursor = dbapi_connection.cursor()
    cursor.execute('PRAGMA foreign_keys=ON')
    cursor.close()


@click.command('init')
@with_appcontext
def init_command():
    """Initializes the directory and the database"""

    data_dir = settings.DATA_FILES_DIRECTORY
    path = os.path.join(data_dir, settings.DATABASE_FILE)

    if os.path.exists(data_dir):
        shutil.rmtree(data_dir)

    os.mkdir(data_dir)
    print('!! Data files directory in {}'.format(data_dir))

    if os.path.exists(path):  # remove previous db
        os.remove(path)

    db.create_all()
    print('!! SQLite database in {}'.format(path))

    # add an admin user
    from logical_enough import models

    name_admin = 'admin{}'.format(''.join([chr(random.randrange(65, 90)) for _ in range(6)]))
    user = models.User(name_admin, is_admin=True)
    db.session.add(user)
    db.session.commit()
    print('!! Created user', name_admin)


def create_app():
    # app
    app = Flask(__name__)
    app.config.update(settings.APP_SETTINGS)

    # db
    db.init_app(app)

    # bootstrap
    Bootstrap(app)
    app.extensions['bootstrap']['cdns']['jquery'] = WebCDN('//cdnjs.cloudflare.com/ajax/libs/jquery/3.2.1/')

    # cli
    app.cli.add_command(init_command)

    # api
    api = Api(app)

    # Views
    from logical_enough.visitors import views as user_views
    app.add_url_rule('/', view_func=user_views.IndexPage.as_view('index'), endpoint='index')

    app.add_url_rule('/login.html', view_func=user_views.LoginPage.as_view('login'), endpoint='login')
    app.add_url_rule('/logout.html', view_func=user_views.logout, endpoint='logout')

    app.add_url_rule(
        '/challenge-<int:id>.html', view_func=user_views.ChallengePage.as_view('challenge'), endpoint='challenge')

    from logical_enough.admin.views import admin_blueprint
    app.register_blueprint(admin_blueprint)

    # API
    from logical_enough.visitors import views_api
    api.add_resource(views_api.CheckMatch, '/api/checks')
    api.add_resource(views_api.CheckMatchMany, '/api/checks_many')
    api.add_resource(views_api.CheckQuestion, '/api/check_question')

    return app
