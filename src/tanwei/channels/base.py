"""推送渠道基类"""
from abc import ABC, abstractmethod
from dataclasses import dataclass

from tanwei.core.config import ChannelConfig


@dataclass
class PushResult:
    success: bool
    channel: str
    error: str | None = None


class BaseChannel(ABC):
    @abstractmethod
    async def send(self, title: str, content: str, channel_config: ChannelConfig) -> PushResult:
        pass


# 渠道注册表
_CHANNEL_REGISTRY: dict[str, type[BaseChannel]] = {}


def register_channel(channel_type: str):
    """装饰器：注册渠道类型"""
    def decorator(cls):
        _CHANNEL_REGISTRY[channel_type] = cls
        return cls
    return decorator


def get_channel(channel_type: str) -> BaseChannel:
    """根据类型获取渠道实例"""
    cls = _CHANNEL_REGISTRY.get(channel_type)
    if not cls:
        raise ValueError(f"未知渠道类型: {channel_type}，可用: {list(_CHANNEL_REGISTRY.keys())}")
    return cls()
