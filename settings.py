import os

DATA_FILES_DIRECTORY = './data/'
DATABASE_FILE = 'logical-enough.db'

APP_SETTINGS = {
    'SQLALCHEMY_TRACK_MODIFICATIONS': False,
    'SECRET_KEY': 'Cv6(ePlTWZ 098C9_%{5!E4t',
    'SQLALCHEMY_DATABASE_URI': 'sqlite:///' + os.path.join(os.path.abspath(DATA_FILES_DIRECTORY), DATABASE_FILE)
}

# Load the production settings, overwrite the existing ones if needed
try:
    from settings_prod import *  # noqa
except ImportError:
    pass
