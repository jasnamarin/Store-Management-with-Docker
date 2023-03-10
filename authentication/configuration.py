from datetime import timedelta
import os

try:
    databaseUrl = os.environ['DATABASE_URL']
except KeyError:
    databaseUrl = 'authenticationDB'


class Configuration:
    SQLALCHEMY_DATABASE_URI = f'mysql+pymysql://root:root@{databaseUrl}/authenticationDB'
    JWT_SECRET_KEY = 'JWT_SECRET_KEY'
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(hours=1)
    JWT_REFRESH_TOKEN_EXPIRES = timedelta(days=30)
