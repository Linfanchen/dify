from core.hosting_configuration import HostingConfiguration

hosting_configuration = HostingConfiguration()


from dify_app import DifyApp

""" 云厂商接入 """
def init_app(app: DifyApp):
    hosting_configuration.init_app(app)
