from flask import Blueprint

from libs.external_api import ExternalApi

# 服务端接口蓝图
bp = Blueprint("service_api", __name__, url_prefix="/v1")
api = ExternalApi(bp)

from . import index
from .app import annotation, app, audio, completion, conversation, file, message, site, workflow
from .dataset import dataset, document, hit_testing, metadata, segment, upload_file
from .workspace import models
