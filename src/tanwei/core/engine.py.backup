"""工作流引擎"""
import asyncio
from datetime import datetime
from pathlib import Path

from jinja2 import Template

from tanwei.agents.llm import LLMClient
from tanwei.channels.base import get_channel
from tanwei.core.config import (
    BotConfig, ModelConfig, StepConfig, WorkflowConfig,
)
from tanwei.core.logger import get_logger
from tanwei.sources.base import SourceResult, get_source

# 确保插件注册
import tanwei.sources.rss  # noqa: F401
import tanwei.channels.dingtalk  # noqa: F401
import tanwei.channels.feishu  # noqa: F401

logger = get_logger("engine")


class WorkflowEngine:
    def __init__(self, bot_config: BotConfig):
        self.config = bot_config
        self.llm = LLMClient(bot_config.providers)
        self.context: dict[str, str] = {}

    async def run_workflow(self, workflow: WorkflowConfig) -> bool:
        """执行工作流"""
        self.context = {}
        logger.info(f"=== 开始工作流: {workflow.name} ===")
        start = datetime.now()

        for step in workflow.steps:
            logger.info(f"步骤 [{step.id}]: {step.action}")
            result = None

            try:
                if step.action == "collect":
                    result = await self._step_collect(step)
                elif step.action == "analyze":
                    result = await self._step_analyze(step, workflow)
                elif step.action == "publish":
                    success = await self._step_publish(step, workflow)
                    if not success:
                        result = None
                    else:
                        continue
                else:
                    logger.warning(f"未知步骤类型: {step.action}")
                    continue
            except Exception as e:
                logger.error(f"步骤 [{step.id}] 异常: {e}")
                result = None

            # 处理失败
            if result is None and step.action != "publish":
                fallback_action = self._get_fallback(step, workflow)
                logger.warning(f"步骤 [{step.id}] 失败，降级策略: {fallback_action}")

                if fallback_action == "abort":
                    logger.error("工作流终止")
                    return False
                elif fallback_action == "skip_step":
                    continue
                elif fallback_action == "raw_push":
                    # 跳过分析，直接用已有数据推送
                    continue

            # 保存输出
            if result and step.output:
                self.context[step.output] = result

        elapsed = (datetime.now() - start).total_seconds()
        logger.info(f"=== 工作流完成: {workflow.name} ({elapsed:.1f}s) ===")
        return True

    async def _step_collect(self, step: StepConfig) -> str | None:
        """采集步骤"""
        if not step.sources:
            logger.warning("采集步骤无数据源配置")
            return None

        all_results: list[SourceResult] = []

        for src_cfg in step.sources:
            try:
                source = get_source(src_cfg.type)
                results = await source.fetch(src_cfg)
                all_results.extend(results)
            except Exception as e:
                logger.warning(f"数据源 [{src_cfg.label}] 采集失败: {e}")

        if not all_results:
            logger.warning("所有数据源采集失败")
            return None

        # 格式化为文本
        lines = []
        for i, r in enumerate(all_results, 1):
            line = f"{i}. 【{r.source_label}】{r.title}"
            if r.summary:
                line += f"\n   摘要: {r.summary[:150]}"
            if r.url:
                line += f"\n   链接: {r.url}"
            lines.append(line)

        text = "\n\n".join(lines)
        logger.info(f"采集完成: {len(all_results)} 条，{len(text)} 字符")
        return text

    async def _step_analyze(self, step: StepConfig, workflow: WorkflowConfig) -> str | None:
        """分析步骤"""
        # 解析输入
        user_content = self._resolve_variable(step.input or "")
        if not user_content:
            logger.warning("分析步骤无输入内容")
            return None

        # 加载 prompt 模板
        system_prompt = "你是一位专业的情报分析师。请分析以下信息并输出简报。"
        if step.prompt:
            prompt_path = Path(step.prompt)
            if prompt_path.exists():
                template_text = prompt_path.read_text(encoding="utf-8")
                try:
                    tmpl = Template(template_text)
                    system_prompt = tmpl.render(
                        input=user_content,
                        date=datetime.now().strftime("%m月%d日"),
                        time=datetime.now().strftime("%H:%M"),
                    )
                except Exception as e:
                    logger.warning(f"模板渲染失败: {e}，使用原始模板")
                    system_prompt = template_text
            else:
                logger.warning(f"prompt 模板不存在: {step.prompt}")

        # 确定模型
        model_config = step.model or self.config.default_model
        if not model_config:
            logger.error("未配置模型")
            return None

        # 调用 LLM
        result = await self.llm.analyze(system_prompt, user_content, model_config, workflow_name=workflow.name)
        return result

    async def _step_publish(self, step: StepConfig, workflow: WorkflowConfig) -> bool:
        """推送步骤"""
        # 解析输入
        content = self._resolve_variable(step.input or "")
        if not content:
            logger.warning("推送步骤无内容")
            return False

        # 获取渠道
        channel_name = step.channel
        if not channel_name:
            logger.error("推送步骤未指定 channel")
            return False

        channel_config = self.config.channels.get(channel_name)
        if not channel_config:
            logger.error(f"未找到渠道配置: {channel_name}")
            return False

        # 格式化
        fmt = step.format or {}
        title = self._resolve_format(fmt.get("title", "📰 消息推送"))
        footer = fmt.get("footer", "")
        if footer:
            footer = self._resolve_format(footer)
            content = f"{content}\n\n---\n*{footer}*"

        # 推送（支持重试）
        channel = get_channel(channel_config.type)
        retry_count = self._parse_retry(workflow.fallback.on_push_fail)

        for attempt in range(retry_count + 1):
            result = await channel.send(title, content, channel_config)
            if result.success:
                return True
            if attempt < retry_count:
                logger.info(f"推送重试 ({attempt + 1}/{retry_count})")
                await asyncio.sleep(3)

        return False

    def _resolve_variable(self, template: str) -> str:
        """替换 ${variable} 引用"""
        import re
        def _replace(match):
            var_name = match.group(1)
            return self.context.get(var_name, "")
        return re.sub(r"\$\{(\w+)\}", _replace, template)

    def _resolve_format(self, template: str) -> str:
        """替换 {date} {time} 等格式变量"""
        now = datetime.now()
        return (
            template
            .replace("{date}", now.strftime("%m月%d日"))
            .replace("{time}", now.strftime("%H:%M"))
            .replace("{datetime}", now.strftime("%Y-%m-%d %H:%M"))
        )

    def _get_fallback(self, step: StepConfig, workflow: WorkflowConfig) -> str:
        """获取降级策略"""
        fb = workflow.fallback
        if step.action == "collect":
            return fb.on_collect_fail
        elif step.action == "analyze":
            return fb.on_analyze_fail
        elif step.action == "publish":
            return fb.on_push_fail
        return "abort"

    @staticmethod
    def _parse_retry(fallback_str: str) -> int:
        """解析重试次数，如 retry_3 → 3"""
        if fallback_str.startswith("retry_"):
            try:
                return int(fallback_str.split("_")[1])
            except (IndexError, ValueError):
                pass
        return 0
