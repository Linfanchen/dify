from dify_app import DifyApp

""" 加载事件处理器 """
def init_app(app: DifyApp):
    from events import event_handlers  # noqa: F401
