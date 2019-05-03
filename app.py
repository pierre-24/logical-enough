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

app.add_url_rule(
    '/admin/utilisateurs.html', view_func=views.AdminUsersPage.as_view('admin-users'), endpoint='admin-users')
app.add_url_rule(
    '/admin/utilisateurs-del-<int:id>.html',
    view_func=views.AdminUsersDelete.as_view('admin-users-delete'),
    endpoint='admin-users-delete')

app.add_url_rule(
    '/admin/challenges.html',
    view_func=views.AdminChallengePage.as_view('admin-challenges'),
    endpoint='admin-challenges')
app.add_url_rule(
    '/admin/challenges-del-<int:id>.html',
    view_func=views.AdminChallengesDelete.as_view('admin-challenges-delete'),
    endpoint='admin-challenges-delete')
app.add_url_rule(
    '/admin/challenges-vue-<int:id>.html',
    view_func=views.AdminChallengesToggle.as_view('admin-challenges-toggle'),
    endpoint='admin-challenges-toggle')


# API
api.add_resource(views_api.CheckMatch, '/api/check')


if __name__ == '__main__':
    app.run()
