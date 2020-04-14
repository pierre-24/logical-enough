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

    if os.path.exists(path): # remove previous db
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
    from logical_enough import views, views_api
    app.add_url_rule('/', view_func=views.IndexPage.as_view('index'), endpoint='index')

    app.add_url_rule('/login.html', view_func=views.LoginPage.as_view('login'), endpoint='login')
    app.add_url_rule('/logout.html', view_func=views.logout, endpoint='logout')

    app.add_url_rule('/challenge-<int:id>.html', view_func=views.ChallengePage.as_view('challenge'), endpoint='challenge')

    app.add_url_rule(
        '/admin/utilisateurs.html', view_func=views.AdminUsersPage.as_view('admin-users'), endpoint='admin-users')
    app.add_url_rule(
        '/admin/utilisateurs-del-<int:id>.html',
        view_func=views.AdminUsersDelete.as_view('admin-users-delete'),
        endpoint='admin-users-delete')

    app.add_url_rule(
        '/admin/challenges.html',
        view_func=views.AdminChallengesPage.as_view('admin-challenges'),
        endpoint='admin-challenges')

    app.add_url_rule(
        '/admin/challenge-<int:id>.html',
        view_func=views.AdminChallengePage.as_view('admin-challenge'),
        endpoint='admin-challenge')
    app.add_url_rule(
        '/admin/challenges-<int:id>-changer-vue.html',
        view_func=views.AdminChallengesToggle.as_view('admin-challenge-toggle'),
        endpoint='admin-challenge-toggle')
    app.add_url_rule(
        '/admin/challenges-<int:id>-del.html',
        view_func=views.AdminChallengesDelete.as_view('admin-challenge-delete'),
        endpoint='admin-challenge-delete')

    app.add_url_rule(
        '/admin/challenge-<int:id>/nouvelle-question.html',
        view_func=views.AdminCreateQuestionPage.as_view('admin-question-create'),
        endpoint='admin-question-create')
    app.add_url_rule(
        '/admin/challenge-<int:challenge_id>/question-<int:id>.html',
        view_func=views.AdminQuestionPage.as_view('admin-question'),
        endpoint='admin-question')
    app.add_url_rule(
        '/admin/challenge-<int:challenge_id>/question-<int:id>-del.html',
        view_func=views.AdminQuestionDelete.as_view('admin-question-delete'),
        endpoint='admin-question-delete')
    app.add_url_rule(
        '/admin/challenge-<int:challenge_id>/question-<int:id>/reponses.html',
        view_func=views.AdminViewAnswerPage.as_view('admin-answers'),
        endpoint='admin-answers')

    # API
    api.add_resource(views_api.CheckMatch, '/api/checks')
    api.add_resource(views_api.CheckMatchMany, '/api/checks_many')
    api.add_resource(views_api.CheckQuestion, '/api/check_question')

    return app
