# util/visited_decorator.py
from functools import wraps
from .visited_util import VisitedRegistry

_registry = VisitedRegistry()   # 单例

def skip_if_visited(fn):
    """
    用于包裹抓取 / 解析函数：
       ① 在调用前检查 URL，若已处理过则直接返回 None
       ② 调用成功后自动写入已访问表
    """
    @wraps(fn)
    async def wrapper(url, *args, **kwargs):
        if _registry.has(url):
            # 直接返回，可按需改成 {}
            return None
        result = await fn(url, *args, **kwargs)
        if result:          # 成功才标记
            _registry.add(url)
        return result
    return wrapper
