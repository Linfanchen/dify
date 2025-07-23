from configs import dify_config
from dify_app import DifyApp


def is_enabled() -> bool:
    return dify_config.API_COMPRESSION_ENABLED

"""
在 Flask 应用返回数据给浏览器之前，自动用 gzip / deflate / brotli 等算法把响应体压小，从而减少传输量、加快页面加载速度。
"""
def init_app(app: DifyApp):
    from flask_compress import Compress  # type: ignore

    compress = Compress()
    compress.init_app(app)
