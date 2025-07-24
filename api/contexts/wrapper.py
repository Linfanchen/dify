from contextvars import ContextVar
from typing import Generic, TypeVar

T = TypeVar("T")


class HiddenValue:
    pass


_default = HiddenValue()


class RecyclableContextVar(Generic[T]):
    """
    RecyclableContextVar is a wrapper around ContextVar
    It's safe to use in gunicorn with thread recycling, but features like `reset` are not available for now

    NOTE: you need to call `increment_thread_recycles` before requests

    协程安全：ContextVar 在协程切换时会正确保存/恢复，RecyclableContextVar 只是额外加了一层计数器，逻辑不变。
    为什么不用 ContextVar.reset()？ 因为 gunicorn 线程池复用后，token 已经失效，reset 反而容易踩坑。
    """

    # 定义上下文变量：线程回收计数器（单调递增的整数）
    _thread_recycles: ContextVar[int] = ContextVar("thread_recycles")

    @classmethod
    def increment_thread_recycles(cls):
        """
            必须在每次请求真正开始之前调用一次（例如在 ASGI middleware 或 Flask/Gunicorn 的 pre_request 钩子）。
            如果忘了调，那么 thread_recycles 永远为 0，会导致“回收保护”失效。
            如果调多了也没事，只是计数器变大，逻辑仍然正确。
        """
        try:
            recycles = cls._thread_recycles.get()
            cls._thread_recycles.set(recycles + 1)
        except LookupError:
            cls._thread_recycles.set(0)

    def __init__(self, context_var: ContextVar[T]):
        """
            把真正的 ContextVar 包起来。
            再创建一个“子计数器” _updates，用来记录 本实例 在这个线程里被 set 的次数。
            当发现 _thread_recycles > _updates 时，说明线程被回收过，原来存的值应被视为“过期”。
        """
        self._context_var = context_var
        self._updates = ContextVar[int](context_var.name + "_updates", default=0)

    def get(self, default: T | HiddenValue = _default) -> T:
        """ 获取变量值 """
        thread_recycles = self._thread_recycles.get(0)
        self_updates = self._updates.get()
        if thread_recycles > self_updates:
            self._updates.set(thread_recycles)

        # check if thread is recycled and should be updated
        if thread_recycles < self_updates:
            return self._context_var.get()
        else:
            # thread_recycles >= self_updates, means current context is invalid
            if isinstance(default, HiddenValue) or default is _default:
                raise LookupError
            else:
                return default

    def set(self, value: T):
        """
            同样先检查线程是否被回收过；如果是，把 _updates 拉到与 thread_recycles 平齐，避免“负向偏移”。
            再把 _updates 加 1，表示“本实例在这个线程里已经 set 过一次”。
        """
        # it leads to a situation that self.updates is less than cls.thread_recycles if `set` was never called before
        # increase it manually
        thread_recycles = self._thread_recycles.get(0)
        self_updates = self._updates.get()
        if thread_recycles > self_updates:
            self._updates.set(thread_recycles)

        if self._updates.get() == self._thread_recycles.get(0):
            # after increment,
            self._updates.set(self._updates.get() + 1)

        # set the context
        self._context_var.set(value)
