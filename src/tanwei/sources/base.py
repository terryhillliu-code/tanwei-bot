"""信息源基类"""
from abc import ABC, abstractmethod
from dataclasses import dataclass, field

from tanwei.core.config import SourceConfig


@dataclass
class SourceResult:
    title: str
    summary: str
    url: str
    source_label: str
    published: str | None = None
    raw: dict | None = None


class BaseSource(ABC):
    @abstractmethod
    async def fetch(self, source_config: SourceConfig) -> list[SourceResult]:
        """采集信息，返回结果列表"""
        pass


# 信息源注册表
_SOURCE_REGISTRY: dict[str, type[BaseSource]] = {}


def register_source(source_type: str):
    """装饰器：注册信息源类型"""
    def decorator(cls):
        _SOURCE_REGISTRY[source_type] = cls
        return cls
    return decorator


def get_source(source_type: str) -> BaseSource:
    """根据类型获取信息源实例"""
    cls = _SOURCE_REGISTRY.get(source_type)
    if not cls:
        raise ValueError(f"未知信息源类型: {source_type}，可用: {list(_SOURCE_REGISTRY.keys())}")
    return cls()
