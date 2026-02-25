"""命令行入口"""
import asyncio
import sys

import click

from tanwei.core.config import load_config, load_all_workflows, load_workflow, ConfigError
from tanwei.core.engine import WorkflowEngine
from tanwei.core.logger import setup_logging, get_logger
from tanwei.core.scheduler import Scheduler


@click.group()
def main():
    """探微 Bot - 配置驱动的 AI 信息监控与推送工具"""
    pass


@main.command()
@click.option("--config", "-c", "config_dir", default="config", help="配置目录路径")
def start(config_dir):
    """启动 Bot，按 schedule 自动运行"""
    try:
        bot_config = load_config(config_dir)
    except ConfigError as e:
        click.echo(f"❌ 配置错误: {e}")
        sys.exit(1)

    setup_logging(bot_config.log_level)
    logger = get_logger("cli")

    workflows = load_all_workflows(config_dir, bot_config.workflow_names)
    if not workflows:
        click.echo("❌ 没有加载到任何工作流")
        sys.exit(1)

    click.echo(f"🚀 {bot_config.name} 启动")
    click.echo(f"   工作流: {[wf.name for wf in workflows]}")

    scheduler = Scheduler(bot_config, workflows)
    scheduler.setup()
    scheduler.run_forever()


@main.command()
@click.argument("workflow_name")
@click.option("--config", "-c", "config_dir", default="config", help="配置目录路径")
def run(workflow_name, config_dir):
    """手动触发一个工作流"""
    try:
        bot_config = load_config(config_dir)
    except ConfigError as e:
        click.echo(f"❌ 配置错误: {e}")
        sys.exit(1)

    setup_logging(bot_config.log_level)

    wf_path = f"{config_dir}/workflows/{workflow_name}.yaml"
    try:
        workflow = load_workflow(wf_path)
    except ConfigError as e:
        click.echo(f"❌ 工作流加载失败: {e}")
        sys.exit(1)

    engine = WorkflowEngine(bot_config)
    success = asyncio.run(engine.run_workflow(workflow))

    if success:
        click.echo(f"✅ 工作流 [{workflow.name}] 执行成功")
    else:
        click.echo(f"❌ 工作流 [{workflow.name}] 执行失败")
        sys.exit(1)


@main.command()
@click.option("--config", "-c", "config_dir", default="config", help="配置目录路径")
def status(config_dir):
    """查看配置和状态"""
    try:
        bot_config = load_config(config_dir)
    except ConfigError as e:
        click.echo(f"❌ 配置错误: {e}")
        sys.exit(1)

    click.echo(f"📋 {bot_config.name}")
    click.echo(f"   时区: {bot_config.timezone}")
    click.echo()

    click.echo("🔑 Providers:")
    for name, p in bot_config.providers.items():
        key_preview = p.api_key[:8] + "..." if len(p.api_key) > 8 else "***"
        click.echo(f"   {name}: {p.base_url} (key={key_preview})")
    click.echo()

    click.echo("📡 Channels:")
    for name, c in bot_config.channels.items():
        click.echo(f"   {name}: type={c.type}")
    click.echo()

    click.echo("⚙️ Workflows:")
    workflows = load_all_workflows(config_dir, bot_config.workflow_names)
    for wf in workflows:
        schedule_str = wf.schedule or "手动触发"
        click.echo(f"   {wf.name}: {len(wf.steps)} 步骤, schedule={schedule_str}")


@main.command()
@click.option("--config", "-c", "config_dir", default="config", help="配置目录路径")
def check(config_dir):
    """验证配置文件"""
    errors = []
    warnings = []

    # 检查主配置
    try:
        bot_config = load_config(config_dir)
        click.echo("✅ bot.yaml 加载成功")
    except ConfigError as e:
        click.echo(f"❌ bot.yaml 错误: {e}")
        sys.exit(1)

    # 检查 providers
    for name, p in bot_config.providers.items():
        if not p.api_key or p.api_key.startswith("${"):
            errors.append(f"Provider [{name}]: API Key 未设置")
        if not p.base_url:
            errors.append(f"Provider [{name}]: base_url 为空")

    # 检查 channels
    for name, c in bot_config.channels.items():
        if not c.webhook or c.webhook.startswith("${"):
            errors.append(f"Channel [{name}]: webhook 未设置")

    # 检查 workflows
    for wf_name in bot_config.workflow_names:
        wf_path = f"{config_dir}/workflows/{wf_name}.yaml"
        try:
            wf = load_workflow(wf_path)
            click.echo(f"✅ 工作流 [{wf_name}] 加载成功 ({len(wf.steps)} 步骤)")

            # 检查 prompt 模板
            for step in wf.steps:
                if step.prompt:
                    from pathlib import Path
                    if not Path(step.prompt).exists():
                        warnings.append(f"工作流 [{wf_name}] 步骤 [{step.id}]: 模板不存在 {step.prompt}")

                # 检查 channel 引用
                if step.channel and step.channel not in bot_config.channels:
                    errors.append(f"工作流 [{wf_name}] 步骤 [{step.id}]: 渠道不存在 {step.channel}")

        except ConfigError as e:
            errors.append(f"工作流 [{wf_name}]: {e}")

    # 输出结果
    click.echo()
    if errors:
        click.echo(f"❌ {len(errors)} 个错误:")
        for e in errors:
            click.echo(f"   - {e}")
    if warnings:
        click.echo(f"⚠️ {len(warnings)} 个警告:")
        for w in warnings:
            click.echo(f"   - {w}")
    if not errors and not warnings:
        click.echo("✅ 所有配置验证通过")

    sys.exit(1 if errors else 0)


if __name__ == "__main__":
    main()

@main.command()
@click.option("--date", "-d", default=None, help="日期 (YYYY-MM-DD)，默认今天")
def usage(date):
    """查看 LLM 用量统计"""
    from tanwei.core.usage import format_usage_report, get_daily_usage
    
    report = format_usage_report(date)
    click.echo(report)
    
    # 简单费用估算（qwen-plus 约 0.004元/千tokens）
    usage_data = get_daily_usage(date)
    if usage_data["total"] > 0:
        cost = usage_data["total"] / 1000 * 0.004
        click.echo(f"\n**预估费用**: ¥{cost:.3f}")

