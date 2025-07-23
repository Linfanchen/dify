from dify_app import DifyApp

""" 初始化告警 """
def init_app(app: DifyApp):
    import warnings

    warnings.simplefilter("ignore", ResourceWarning)
