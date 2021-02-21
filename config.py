import os
import datetime

basedir = os.path.abspath(os.path.dirname(__file__))


class Config(object):
    DEBUG = True
    TESTING = False
    CSRF_ENABLED = True
    SECRET_KEY = (
        "UK0eB70TndmOMqeb9Rh4e30igYyPmBHNSpymu3RuixIU2E6vJ"
        + "7Q9W95oyj3zBfDR0AFEZsjOz7tY8pW1NibCCg=="
    )
    SQLALCHEMY_DATABASE_URI = (
        "postgresql://ediman:FqHRxljLGP53@localhost:5432/webcono_dev"
    )
    PERMANENT_SESSION_LIFETIME = datetime.timedelta(days=7)


class ProductionConfig(Config):
    DEBUG = False


class StagingConfig(Config):
    DEVELOPMENT = True
    DEBUG = True


class DevelopmentConfig(Config):
    DEVELOPMENT = True


class TestingConfig(Config):
    TESTING = True
