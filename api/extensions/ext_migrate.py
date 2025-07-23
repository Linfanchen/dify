from dify_app import DifyApp

""" 迁移扩展 """
def init_app(app: DifyApp):
    # 使用这个依赖实现
    import flask_migrate  # type: ignore

    from extensions.ext_database import db

    flask_migrate.Migrate(app, db)
