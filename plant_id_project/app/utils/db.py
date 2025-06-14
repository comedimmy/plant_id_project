import mysql.connector
from flask import g
from config import MYSQL_HOST, MYSQL_USER, MYSQL_PASSWORD, MYSQL_DB

def init_db(app):
    app.teardown_appcontext(close_db)  # 當請求結束時關閉連線

def get_db():
    if 'db' not in g:
        g.db = mysql.connector.connect(
            host=MYSQL_HOST,
            user=MYSQL_USER,
            password=MYSQL_PASSWORD,
            database=MYSQL_DB
        )
    return g.db

def close_db(error=None):
    db = g.pop('db', None)
    if db is not None:
        db.close()
