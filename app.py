import os
import random

import commons
import views_api
import settings
import models
import views

app, api = commons.create_app()


# CLI
@app.cli.command('init')
def init_db_command():
    """Initializes the directory and the database"""

    directory = settings.DATA_FILES_DIRECTORY
    path = os.path.join(directory, settings.DATABASE_FILE)

    if os.path.exists(path):  # remove previous db
        os.remove(path)

    if not os.path.exists(directory):
        os.mkdir(directory)
        print('!! Data files directory in {}'.format(directory))

    commons.db.create_all()
    print('!! SQLite database in {}'.format(path))

    # add an admin user
    name_admin = 'admin{}'.format(''.join([chr(random.randrange(65, 90)) for _ in range(6)]))
    user = models.User(name_admin, is_admin=True)
    commons.db.session.add(user)
    commons.db.session.commit()
    print('!! Created user', name_admin)


# Views
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


# API
api.add_resource(views_api.CheckMatch, '/api/checks')
api.add_resource(views_api.CheckMatchMany, '/api/checks_many')
api.add_resource(views_api.CheckQuestion, '/api/check_question')


if __name__ == '__main__':
    app.run()
