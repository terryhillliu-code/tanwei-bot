"""定时调度器"""
import asyncio
import re
import time

import schedule

from tanwei.core.config import BotConfig, WorkflowConfig
from tanwei.core.engine import WorkflowEngine
from tanwei.core.logger import get_logger

logger = get_logger("scheduler")


class Scheduler:
    def __init__(self, bot_config: BotConfig, workflows: list[WorkflowConfig]):
        self.bot_config = bot_config
        self.workflows = {wf.name: wf for wf in workflows}
        self.engine = WorkflowEngine(bot_config)

    def setup(self):
        """根据 schedule 字段注册定时任务"""
        for wf in self.workflows.values():
            if not wf.schedule:
                logger.info(f"工作流 [{wf.name}] 无定时配置，仅支持手动触发")
                continue

            self._register_schedule(wf)

        jobs = schedule.get_jobs()
        logger.info(f"已注册 {len(jobs)} 个定时任务")

    def _register_schedule(self, wf: WorkflowConfig):
        """解析 schedule 字符串并注册"""
        s = wf.schedule.strip()

        # every Xh / every Xm
        match = re.match(r"every\s+(\d+)\s*([hm])", s, re.IGNORECASE)
        if match:
            value = int(match.group(1))
            unit = match.group(2).lower()
            if unit == "h":
                schedule.every(value).hours.do(self._run_async, wf.name)
            elif unit == "m":
                schedule.every(value).minutes.do(self._run_async, wf.name)
            logger.info(f"定时任务: [{wf.name}] every {value}{unit}")
            return

        # daily HH:MM 或 daily HH:MM,HH:MM
        match = re.match(r"daily\s+([\d:,]+)", s, re.IGNORECASE)
        if match:
            times = match.group(1).split(",")
            for t in times:
                t = t.strip()
                schedule.every().day.at(t).do(self._run_async, wf.name)
                logger.info(f"定时任务: [{wf.name}] daily at {t}")
            return

        logger.warning(f"无法解析 schedule: '{s}' (工作流: {wf.name})")

    def _run_async(self, workflow_name: str):
        """同步包装异步执行"""
        wf = self.workflows.get(workflow_name)
        if not wf:
            logger.error(f"工作流不存在: {workflow_name}")
            return

        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            result = loop.run_until_complete(self.engine.run_workflow(wf))
            loop.close()
            status = "成功" if result else "失败"
            logger.info(f"定时执行: [{workflow_name}] {status}")
        except Exception as e:
            logger.error(f"定时执行异常: [{workflow_name}] {e}")

    async def run_once(self, workflow_name: str) -> bool:
        """手动触发单个工作流"""
        wf = self.workflows.get(workflow_name)
        if not wf:
            logger.error(f"工作流不存在: {workflow_name}")
            return False

        return await self.engine.run_workflow(wf)

    def run_forever(self):
        """持续运行调度器"""
        logger.info("调度器启动，等待任务触发...")
        try:
            while True:
                schedule.run_pending()
                time.sleep(30)
        except KeyboardInterrupt:
            logger.info("调度器停止")
