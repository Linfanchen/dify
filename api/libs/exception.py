from typing import Optional

from werkzeug.exceptions import HTTPException


class BaseHTTPException(HTTPException):
    """ 基础的异常类 """
    error_code: str = "unknown"
    data: Optional[dict] = None

    def __init__(self, description=None, response=None):
        super().__init__(description, response)

        self.data = {
            "code": self.error_code,
            "message": self.description,
            "status": self.code,
        }
