import logging
import time
import uuid
from collections.abc import Generator, Mapping
from datetime import timedelta
from typing import Any, Optional, Union

from core.errors.error import AppInvokeQuotaExceededError
from extensions.ext_redis import redis_client

logger = logging.getLogger(__name__)


class RateLimit:
    _MAX_ACTIVE_REQUESTS_KEY = "dify:rate_limit:{}:max_active_requests" # 保存最大并发数
    _ACTIVE_REQUESTS_KEY = "dify:rate_limit:{}:active_requests" # 哈希表，保存当前活跃请求
    _UNLIMITED_REQUEST_ID = "unlimited_request_id"
    _REQUEST_MAX_ALIVE_TIME = 10 * 60  # 10 minutes
    _ACTIVE_REQUESTS_COUNT_FLUSH_INTERVAL = 5 * 60  # recalculate request_count from request_detail every 5 minutes
    _instance_dict: dict[str, "RateLimit"] = {} # 实例字典

    def __new__(cls: type["RateLimit"], client_id: str, max_active_requests: int):
        """ 单例模式：每个 client_id 只创建一个实例。 """
        if client_id not in cls._instance_dict:
            instance = super().__new__(cls)
            cls._instance_dict[client_id] = instance
        return cls._instance_dict[client_id]

    def __init__(self, client_id: str, max_active_requests: int):
        """ 判断是否可用或者已经初始化之后：进行初始化操作 """
        self.max_active_requests = max_active_requests
        # must be called after max_active_requests is set
        if self.disabled():
            return
        if hasattr(self, "initialized"):
            return
        self.initialized = True
        self.client_id = client_id
        self.active_requests_key = self._ACTIVE_REQUESTS_KEY.format(client_id)
        self.max_active_requests_key = self._MAX_ACTIVE_REQUESTS_KEY.format(client_id)
        self.last_recalculate_time = float("-inf")
        self.flush_cache(use_local_value=True)

    def flush_cache(self, use_local_value=False):
        """ 定期清理超时请求（默认 5 分钟一次） """
        if self.disabled():
            return
        self.last_recalculate_time = time.time()
        # flush max active requests
        if use_local_value or not redis_client.exists(self.max_active_requests_key):
            redis_client.setex(self.max_active_requests_key, timedelta(days=1), self.max_active_requests)
        else:
            self.max_active_requests = int(redis_client.get(self.max_active_requests_key).decode("utf-8"))
            redis_client.expire(self.max_active_requests_key, timedelta(days=1))

        # flush max active requests (in-transit request list)
        if not redis_client.exists(self.active_requests_key):
            return
        request_details = redis_client.hgetall(self.active_requests_key)
        redis_client.expire(self.active_requests_key, timedelta(days=1))
        timeout_requests = [
            k
            for k, v in request_details.items()
            if time.time() - float(v.decode("utf-8")) > RateLimit._REQUEST_MAX_ALIVE_TIME
        ]
        if timeout_requests:
            redis_client.hdel(self.active_requests_key, *timeout_requests)

    def enter(self, request_id: Optional[str] = None) -> str:
        """ 尝试进入请求，成功返回 request_id，失败抛出 AppInvokeQuotaExceededError """
        if self.disabled():
            return RateLimit._UNLIMITED_REQUEST_ID
        if time.time() - self.last_recalculate_time > RateLimit._ACTIVE_REQUESTS_COUNT_FLUSH_INTERVAL:
            self.flush_cache()
        if not request_id:
            request_id = RateLimit.gen_request_key()

        active_requests_count = redis_client.hlen(self.active_requests_key)
        if active_requests_count >= self.max_active_requests:
            raise AppInvokeQuotaExceededError(
                f"Too many requests. Please try again later. The current maximum concurrent requests allowed "
                f"for {self.client_id} is {self.max_active_requests}."
            )
        redis_client.hset(self.active_requests_key, request_id, str(time.time()))
        return request_id

    def exit(self, request_id: str):
        """ 请求结束时调用，释放资源 """
        if request_id == RateLimit._UNLIMITED_REQUEST_ID:
            return
        redis_client.hdel(self.active_requests_key, request_id)

    def disabled(self):
        return self.max_active_requests <= 0

    @staticmethod
    def gen_request_key() -> str:
        return str(uuid.uuid4())

    def generate(self, generator: Union[Generator[str, None, None], Mapping[str, Any]], request_id: str):
        if isinstance(generator, Mapping):
            return generator
        else:
            return RateLimitGenerator(rate_limit=self, generator=generator, request_id=request_id)


class RateLimitGenerator:
    """ 确保生成器（或其他可迭代对象）在迭代完成或发生异常时，自动释放限流资源（调用 rate_limit.exit()）。 """
    def __init__(self, rate_limit: RateLimit, generator: Generator[str, None, None], request_id: str):
        """

        typing.Generator：Generator[YieldType, SendType, ReturnType]
        - 只能 yield 出字符串
        - 不支持 .send(value)
        - 不会 return 任何值

        """
        self.rate_limit = rate_limit # 频率
        self.generator = generator # 生成器
        self.request_id = request_id # 请求ID
        self.closed = False # 是否已经关闭

    def __iter__(self):
        return self

    def __next__(self):
        if self.closed:
            raise StopIteration
        try:
            return next(self.generator)
        except Exception:
            self.close()
            raise

    def close(self):
        if not self.closed:
            self.closed = True
            self.rate_limit.exit(self.request_id)
            if self.generator is not None and hasattr(self.generator, "close"):
                # 原生的生成器关闭
                self.generator.close()
