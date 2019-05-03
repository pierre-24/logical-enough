import os
import random

import commons
import views_api
import settings
import models

app, api = commons.create_app()


# APP
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
@app.route('/')
def hello_world():
    return 'Hello World!'


# API
api.add_resource(views_api.CheckMatch, '/api/check')


if __name__ == '__main__':
    app.run()
