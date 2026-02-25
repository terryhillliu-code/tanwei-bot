"""LLM 调用层（OpenAI 兼容接口）"""
import asyncio
from dataclasses import dataclass

import httpx

from tanwei.core.config import ModelConfig, ProviderConfig
from tanwei.core.logger import get_logger
from tanwei.core.usage import record_usage

logger = get_logger("agent.llm")

RETRY_DELAY = 5
MAX_RETRIES = 1


@dataclass
class LLMResponse:
    content: str
    model: str
    tokens_used: int | None = None


class LLMClient:
    def __init__(self, providers: dict[str, ProviderConfig]):
        self.providers = providers

    async def chat(
        self,
        messages: list[dict],
        model_config: ModelConfig,
        workflow_name: str = "",
    ) -> LLMResponse | None:
        """调用 LLM chat completion"""
        provider = self.providers.get(model_config.provider)
        if not provider:
            logger.error(f"未找到 provider: {model_config.provider}")
            return None

        url = f"{provider.base_url.rstrip('/')}/chat/completions"
        headers = {
            "Authorization": f"Bearer {provider.api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": model_config.model,
            "messages": messages,
            "max_tokens": model_config.max_tokens,
        }

        for attempt in range(MAX_RETRIES + 1):
            try:
                logger.info(
                    f"LLM 调用: {model_config.provider}/{model_config.model} "
                    f"(attempt {attempt + 1})"
                )
                async with httpx.AsyncClient(timeout=model_config.timeout) as client:
                    resp = await client.post(url, headers=headers, json=payload)
                    resp.raise_for_status()
                    data = resp.json()

                choice = data.get("choices", [{}])[0]
                content = choice.get("message", {}).get("content", "")
                usage = data.get("usage", {})
                tokens = usage.get("total_tokens")

                logger.info(
                    f"LLM 完成: {len(content)} 字符"
                    + (f", tokens={tokens}" if tokens else "")
                )

                # 记录用量
                if tokens:
                    record_usage(
                        provider=model_config.provider,
                        model=model_config.model,
                        tokens=tokens,
                        source="tanwei-bot",
                        workflow=workflow_name,
                    )

                return LLMResponse(
                    content=content,
                    model=model_config.model,
                    tokens_used=tokens,
                )

            except httpx.TimeoutException:
                logger.warning(f"LLM 超时 ({model_config.timeout}s)")
            except httpx.HTTPStatusError as e:
                logger.warning(f"LLM HTTP 错误: {e.response.status_code}")
            except Exception as e:
                logger.warning(f"LLM 调用异常: {e}")

            if attempt < MAX_RETRIES:
                logger.info(f"等待 {RETRY_DELAY}s 后重试...")
                await asyncio.sleep(RETRY_DELAY)

        logger.error("LLM 调用失败，已用尽重试次数")
        return None

    async def analyze(
        self,
        system_prompt: str,
        user_content: str,
        model_config: ModelConfig,
        workflow_name: str = "",
    ) -> str | None:
        """便捷方法：分析内容"""
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_content},
        ]
        result = await self.chat(messages, model_config, workflow_name=workflow_name)
        return result.content if result else None
