"""钉钉 Webhook 推送"""
import base64
import hashlib
import hmac
import time
import urllib.parse

import httpx

from tanwei.core.config import ChannelConfig
from tanwei.core.logger import get_logger
from tanwei.channels.base import BaseChannel, PushResult, register_channel

logger = get_logger("channel.dingtalk")

DINGTALK_MAX_LEN = 4000
SEND_TIMEOUT = 10


def _sign(secret: str) -> tuple[str, str]:
    """生成钉钉签名"""
    timestamp = str(round(time.time() * 1000))
    string_to_sign = f"{timestamp}\n{secret}"
    hmac_code = hmac.new(
        secret.encode("utf-8"),
        string_to_sign.encode("utf-8"),
        digestmod=hashlib.sha256,
    ).digest()
    sign = urllib.parse.quote_plus(base64.b64encode(hmac_code))
    return timestamp, sign


@register_channel("dingtalk")
class DingtalkChannel(BaseChannel):
    async def send(self, title: str, content: str, channel_config: ChannelConfig) -> PushResult:
        logger.info(f"钉钉推送: {title}")

        # 截断
        if len(content) > DINGTALK_MAX_LEN:
            content = content[:DINGTALK_MAX_LEN] + "\n\n...(内容过长已截断)"
            logger.warning("内容超长，已截断")

        # 构建 URL
        url = channel_config.webhook
        if channel_config.secret:
            timestamp, sign = _sign(channel_config.secret)
            url = f"{url}&timestamp={timestamp}&sign={sign}"

        # 构建消息体
        payload = {
            "msgtype": "markdown",
            "markdown": {
                "title": title,
                "text": content,
            },
        }

        try:
            async with httpx.AsyncClient(timeout=SEND_TIMEOUT) as client:
                resp = await client.post(url, json=payload)
                resp.raise_for_status()
                data = resp.json()

            if data.get("errcode", 0) != 0:
                err = data.get("errmsg", "unknown error")
                logger.error(f"钉钉返回错误: {err}")
                return PushResult(success=False, channel="dingtalk", error=err)

            logger.info("钉钉推送成功")
            return PushResult(success=True, channel="dingtalk")

        except Exception as e:
            logger.error(f"钉钉推送失败: {e}")
            return PushResult(success=False, channel="dingtalk", error=str(e))
