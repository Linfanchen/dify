from configs import dify_config
from dify_app import DifyApp

""" 注册蓝图路由 """
def init_app(app: DifyApp):
    from flask_cors import CORS
    # 导入各模块的蓝图
    from controllers.console import bp as console_app_bp
    from controllers.files import bp as files_bp
    from controllers.inner_api import bp as inner_api_bp
    from controllers.mcp import bp as mcp_bp
    from controllers.service_api import bp as service_api_bp
    from controllers.web import bp as web_bp

    """
        Flask-CORS 通过 Flask 的 after_request 钩子 自动为响应添加 CORS 头：

        CORS(app, resources={
            r"/api/*": {
                "origins": ["https://trusted-site.com"],
                "methods": ["GET", "POST"],
                "allow_headers": ["Authorization"],
                "supports_credentials": True
            }
        })
    """
    # 注册服务接口蓝图
    CORS(
        service_api_bp,
        allow_headers=["Content-Type", "Authorization", "X-App-Code"],
        methods=["GET", "PUT", "POST", "DELETE", "OPTIONS", "PATCH"],
    )
    app.register_blueprint(service_api_bp)

    # 注册web接口蓝图
    CORS(
        web_bp,
        resources={r"/*": {"origins": dify_config.WEB_API_CORS_ALLOW_ORIGINS}},
        supports_credentials=True,
        allow_headers=["Content-Type", "Authorization", "X-App-Code"],
        methods=["GET", "PUT", "POST", "DELETE", "OPTIONS", "PATCH"],
        expose_headers=["X-Version", "X-Env"],
    )
    app.register_blueprint(web_bp)

    # 注册控制台接口蓝图
    CORS(
        console_app_bp,
        resources={r"/*": {"origins": dify_config.CONSOLE_CORS_ALLOW_ORIGINS}},
        supports_credentials=True,
        allow_headers=["Content-Type", "Authorization"],
        methods=["GET", "PUT", "POST", "DELETE", "OPTIONS", "PATCH"],
        expose_headers=["X-Version", "X-Env"],
    )
    app.register_blueprint(console_app_bp)

    # 注册文件接口蓝图
    CORS(files_bp, allow_headers=["Content-Type"], methods=["GET", "PUT", "POST", "DELETE", "OPTIONS", "PATCH"])
    app.register_blueprint(files_bp)

    # 注册内部接口蓝图
    app.register_blueprint(inner_api_bp)

    # 注册MCP接口蓝图
    app.register_blueprint(mcp_bp)
