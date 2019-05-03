APP_SETTINGS = {
    'SQLALCHEMY_TRACK_MODIFICATIONS': False,
    'SECRET_KEY': 'Cv6(ePlTWZ 098C9_%{5!E4t',
}

# Load the production settings, overwrite the existing ones if needed
try:
    from settings_prod import *  # noqa
except ImportError:
    pass
