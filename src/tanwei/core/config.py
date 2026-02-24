"""配置加载与校验"""
import os
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml
from dotenv import load_dotenv

from tanwei.core.logger import get_logger

logger = get_logger("config")


class ConfigError(Exception):
    """配置错误"""
    pass


# ========== 数据类 ==========

@dataclass
class ProviderConfig:
    api_key: str
    base_url: str


@dataclass
class ModelConfig:
    provider: str
    model: str
    max_tokens: int = 2000
    timeout: int = 180


@dataclass
class ChannelConfig:
    type: str
    webhook: str
    secret: str | None = None


@dataclass
class SourceConfig:
    type: str
    url: str
    label: str = ""


@dataclass
class FallbackConfig:
    on_collect_fail: str = "abort"
    on_analyze_fail: str = "raw_push"
    on_push_fail: str = "retry_3"


@dataclass
class StepConfig:
    id: str
    action: str  # collect / analyze / publish
    agent: str | None = None
    sources: list[SourceConfig] | None = None
    input: str | None = None
    prompt: str | None = None
    channel: str | None = None
    config: dict | None = None
    output: str | None = None
    model: ModelConfig | None = None
    format: dict | None = None


@dataclass
class WorkflowConfig:
    name: str
    schedule: str | None = None
    steps: list[StepConfig] = field(default_factory=list)
    fallback: FallbackConfig = field(default_factory=FallbackConfig)


@dataclass
class BotConfig:
    name: str = "tanwei-bot"
    timezone: str = "Asia/Shanghai"
    log_level: str = "INFO"
    providers: dict[str, ProviderConfig] = field(default_factory=dict)
    default_model: ModelConfig | None = None
    channels: dict[str, ChannelConfig] = field(default_factory=dict)
    workflow_names: list[str] = field(default_factory=list)


# ========== 环境变量替换 ==========

# 只替换全大写的环境变量（如 ${DASHSCOPE_API_KEY}）
# 不替换小写的步骤输出引用（如 ${raw_news}）
ENV_VAR_PATTERN = re.compile(r"\$\{([A-Z][A-Z0-9_]*)(:-(.*?))?\}")


def _resolve_env(value: str) -> str:
    """替换 ${VAR} 和 ${VAR:-default}，只处理全大写变量名"""
    def _replace(match):
        var = match.group(1)
        default = match.group(3)
        result = os.environ.get(var)
        if result is None:
            if default is not None:
                return default
            raise ConfigError(f"环境变量 {var} 未设置且无默认值")
        return result

    return ENV_VAR_PATTERN.sub(_replace, value)


def _resolve_env_recursive(data: Any) -> Any:
    """递归替换字典/列表中的环境变量"""
    if isinstance(data, str):
        return _resolve_env(data)
    elif isinstance(data, dict):
        return {k: _resolve_env_recursive(v) for k, v in data.items()}
    elif isinstance(data, list):
        return [_resolve_env_recursive(item) for item in data]
    return data


# ========== 解析函数 ==========

def _parse_model(data: dict | None) -> ModelConfig | None:
    if not data:
        return None
    return ModelConfig(
        provider=data.get("provider", ""),
        model=data.get("model", ""),
        max_tokens=data.get("max_tokens", 2000),
        timeout=data.get("timeout", 180),
    )


def _parse_source(data: dict) -> SourceConfig:
    return SourceConfig(
        type=data.get("type", "rss"),
        url=data.get("url", ""),
        label=data.get("label", ""),
    )


def _parse_step(data: dict) -> StepConfig:
    sources = None
    if "sources" in data:
        sources = [_parse_source(s) for s in data["sources"]]

    return StepConfig(
        id=data.get("id", ""),
        action=data.get("action", ""),
        agent=data.get("agent"),
        sources=sources,
        input=data.get("input"),
        prompt=data.get("prompt"),
        channel=data.get("channel"),
        config=data.get("config"),
        output=data.get("output"),
        model=_parse_model(data.get("model")),
        format=data.get("format"),
    )


def _parse_fallback(data: dict | None) -> FallbackConfig:
    if not data:
        return FallbackConfig()
    return FallbackConfig(
        on_collect_fail=data.get("on_collect_fail", "abort"),
        on_analyze_fail=data.get("on_analyze_fail", "raw_push"),
        on_push_fail=data.get("on_push_fail", "retry_3"),
    )


# ========== 公开接口 ==========

def load_config(config_dir: str = "config") -> BotConfig:
    """加载主配置"""
    load_dotenv()

    config_path = Path(config_dir) / "bot.yaml"
    if not config_path.exists():
        raise ConfigError(f"配置文件不存在: {config_path}")

    with open(config_path, "r", encoding="utf-8") as f:
        raw = yaml.safe_load(f)

    raw = _resolve_env_recursive(raw)

    # 解析 providers
    providers = {}
    for name, pdata in raw.get("providers", {}).items():
        providers[name] = ProviderConfig(
            api_key=pdata.get("api_key", ""),
            base_url=pdata.get("base_url", ""),
        )

    # 解析 channels
    channels = {}
    for name, cdata in raw.get("channels", {}).items():
        channels[name] = ChannelConfig(
            type=cdata.get("type", ""),
            webhook=cdata.get("webhook", ""),
            secret=cdata.get("secret"),
        )

    bot_config = BotConfig(
        name=raw.get("name", "tanwei-bot"),
        timezone=raw.get("timezone", "Asia/Shanghai"),
        log_level=raw.get("log_level", "INFO"),
        providers=providers,
        default_model=_parse_model(raw.get("default_model")),
        channels=channels,
        workflow_names=raw.get("workflows", []),
    )

    logger.info(f"配置加载完成: {bot_config.name}")
    logger.info(f"  providers: {list(providers.keys())}")
    logger.info(f"  channels: {list(channels.keys())}")
    logger.info(f"  workflows: {bot_config.workflow_names}")

    return bot_config


def load_workflow(workflow_path: str) -> WorkflowConfig:
    """加载单个工作流配置"""
    path = Path(workflow_path)
    if not path.exists():
        raise ConfigError(f"工作流文件不存在: {path}")

    with open(path, "r", encoding="utf-8") as f:
        raw = yaml.safe_load(f)

    raw = _resolve_env_recursive(raw)

    steps = [_parse_step(s) for s in raw.get("steps", [])]

    wf = WorkflowConfig(
        name=raw.get("name", path.stem),
        schedule=raw.get("schedule"),
        steps=steps,
        fallback=_parse_fallback(raw.get("fallback")),
    )

    logger.info(f"工作流加载: {wf.name} ({len(wf.steps)} 步骤, schedule={wf.schedule})")
    return wf


def load_all_workflows(config_dir: str, workflow_names: list[str]) -> list[WorkflowConfig]:
    """加载所有工作流"""
    workflows = []
    wf_dir = Path(config_dir) / "workflows"

    for name in workflow_names:
        wf_path = wf_dir / f"{name}.yaml"
        try:
            wf = load_workflow(str(wf_path))
            workflows.append(wf)
        except ConfigError as e:
            logger.error(f"加载工作流失败 [{name}]: {e}")

    logger.info(f"共加载 {len(workflows)}/{len(workflow_names)} 个工作流")
    return workflows
