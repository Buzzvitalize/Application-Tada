import os
import warnings


class BaseConfig:
    """Base configuration with safe defaults.

    Falls back to a development key when ``SECRET_KEY`` isn't supplied so the
    application can still start in local environments.  A warning is emitted to
    remind deployers to set a proper secret in production.
    """

    SECRET_KEY = os.environ.get("SECRET_KEY", "dev")
    if SECRET_KEY == "dev":
        warnings.warn(
            "Using default SECRET_KEY; set the SECRET_KEY environment variable in production",
            UserWarning,
        )

    SQLALCHEMY_TRACK_MODIFICATIONS = False

class DevelopmentConfig(BaseConfig):
    SQLALCHEMY_DATABASE_URI = 'sqlite:///database.sqlite'

class TestingConfig(BaseConfig):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'sqlite://'
    WTF_CSRF_ENABLED = False

class ProductionConfig(BaseConfig):
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL', 'sqlite:///database.sqlite')
