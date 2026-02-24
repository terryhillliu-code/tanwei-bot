"""飞书正式应用推送（探微情报）"""
import json
import os
import time
import httpx

from tanwei.core.config import ChannelConfig
from tanwei.core.logger import get_logger
from tanwei.channels.base import BaseChannel, PushResult, register_channel

logger = get_logger("channel.feishu")

FEISHU_MAX_LEN = 8000
TOKEN_CACHE = {"token": None, "expire_at": 0}


def _get_tenant_token() -> str | None:
    """获取 tenant_access_token（带缓存）"""
    now = time.time()
    if TOKEN_CACHE["token"] and TOKEN_CACHE["expire_at"] > now + 60:
        return TOKEN_CACHE["token"]

    app_id = os.environ.get("FEISHU_APP_ID", "")
    app_secret = os.environ.get("FEISHU_APP_SECRET", "")

    if not app_id or not app_secret:
        logger.error("FEISHU_APP_ID 或 FEISHU_APP_SECRET 未配置")
        return None

    try:
        resp = httpx.post(
            "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal",
            json={"app_id": app_id, "app_secret": app_secret},
            timeout=10
        )
        data = resp.json()
        if data.get("code") != 0:
            logger.error(f"获取 token 失败: {data}")
            return None

        TOKEN_CACHE["token"] = data["tenant_access_token"]
        TOKEN_CACHE["expire_at"] = now + data.get("expire", 7200)
        logger.debug("飞书 token 已刷新")
        return TOKEN_CACHE["token"]
    except Exception as e:
        logger.error(f"获取 token 异常: {e}")
        return None


@register_channel("feishu")
class FeishuChannel(BaseChannel):
    async def send(self, title: str, content: str, channel_config: ChannelConfig) -> PushResult:
        logger.info(f"飞书推送: {title}")

        # 截断
        if len(content) > FEISHU_MAX_LEN:
            content = content[:FEISHU_MAX_LEN] + "\n\n...(内容过长已截断)"
            logger.warning("内容超长，已截断")

        # 优先使用正式应用 API
        chat_id = os.environ.get("FEISHU_CHAT_ID", "") or channel_config.extra.get("chat_id", "")

        if chat_id:
            result = await self._send_via_app(title, content, chat_id)
            if result.success:
                return result
            logger.warning("正式应用推送失败，尝试 Webhook 降级")

        # 降级：使用 Webhook（兼容旧配置）
        webhook = channel_config.webhook
        if webhook:
            return await self._send_via_webhook(title, content, webhook)

        return PushResult(success=False, channel="feishu", error="无可用推送方式")

    async def _send_via_app(self, title: str, content: str, chat_id: str) -> PushResult:
        """通过正式应用 API 推送"""
        token = _get_tenant_token()
        if not token:
            return PushResult(success=False, channel="feishu", error="获取 token 失败")

        # 构建卡片消息
        card = json.dumps({
            "header": {
                "title": {"tag": "plain_text", "content": title},
                "template": "blue"
            },
            "elements": [
                {"tag": "markdown", "content": content}
            ]
        })

        payload = {
            "receive_id": chat_id,
            "msg_type": "interactive",
            "content": card
        }

        try:
            async with httpx.AsyncClient(timeout=15) as client:
                resp = await client.post(
                    "https://open.feishu.cn/open-apis/im/v1/messages?receive_id_type=chat_id",
                    json=payload,
                    headers={
                        "Authorization": f"Bearer {token}",
                        "Content-Type": "application/json"
                    }
                )
                data = resp.json()

            if data.get("code") == 0:
                logger.info("飞书推送成功（正式应用）")
                return PushResult(success=True, channel="feishu")
            else:
                err = f"code={data.get('code')} msg={data.get('msg')}"
                logger.error(f"飞书返回错误: {err}")
                return PushResult(success=False, channel="feishu", error=err)

        except Exception as e:
            logger.error(f"飞书推送异常: {e}")
            return PushResult(success=False, channel="feishu", error=str(e))

    async def _send_via_webhook(self, title: str, content: str, webhook: str) -> PushResult:
        """通过 Webhook 推送（降级方案）"""
        payload = {
            "msg_type": "interactive",
            "card": {
                "header": {
                    "title": {"tag": "plain_text", "content": title},
                    "template": "blue"
                },
                "elements": [
                    {"tag": "markdown", "content": content}
                ]
            }
        }

        try:
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.post(webhook, json=payload)
                resp.raise_for_status()
                data = resp.json()

            if data.get("code", 0) != 0:
                err = data.get("msg", "unknown error")
                logger.error(f"飞书 Webhook 返回错误: {err}")
                return PushResult(success=False, channel="feishu", error=err)

            logger.info("飞书推送成功（Webhook）")
            return PushResult(success=True, channel="feishu")

        except Exception as e:
            logger.error(f"飞书 Webhook 推送失败: {e}")
            return PushResult(success=False, channel="feishu", error=str(e))
