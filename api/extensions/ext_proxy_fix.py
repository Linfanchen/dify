from configs import dify_config
from dify_app import DifyApp

"""
让运行在反向代理（Nginx、Traefik、ELB、Cloudflare…）后面的 Flask 应用正确识别客户端的真实 IP 和端口，而不是拿到代理服务器的值。
"""
def init_app(app: DifyApp):
    if dify_config.RESPECT_XFORWARD_HEADERS_ENABLED:
        from werkzeug.middleware.proxy_fix import ProxyFix

        app.wsgi_app = ProxyFix(app.wsgi_app, x_port=1)  # type: ignore
