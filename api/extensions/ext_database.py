from dify_app import DifyApp
from models import db

""" 数据库扩展：flask_sqlalchemy """
def init_app(app: DifyApp):
    db.init_app(app)
