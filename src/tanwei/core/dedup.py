"""新闻去重模块"""
import hashlib
import json
import os
from datetime import datetime
from pathlib import Path
from typing import Set

from tanwei.core.logger import get_logger

logger = get_logger("dedup")

# 去重记录文件
DEDUP_FILE = Path(os.path.expanduser("~/logs/news_pushed.json"))


def _get_news_id(title: str, url: str = "") -> str:
    """生成新闻唯一标识"""
    content = f"{title}|{url}"
    return hashlib.md5(content.encode()).hexdigest()[:16]


def load_pushed_ids() -> dict:
    """加载已推送记录"""
    if not DEDUP_FILE.exists():
        return {"date": "", "ids": []}
    
    try:
        with open(DEDUP_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            return data
    except Exception as e:
        logger.warning(f"加载去重记录失败: {e}")
        return {"date": "", "ids": []}


def save_pushed_ids(data: dict):
    """保存已推送记录"""
    try:
        DEDUP_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(DEDUP_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        logger.warning(f"保存去重记录失败: {e}")


def filter_new_items(items: list, reset: bool = False) -> list:
    """
    过滤已推送的新闻
    
    Args:
        items: 新闻列表，每项需有 title 和 url 属性
        reset: True 表示全量推送（清空旧记录）
        
    Returns:
        未推送过的新闻列表
    """
    today = datetime.now().strftime("%Y-%m-%d")
    data = load_pushed_ids()
    
    # 如果是新的一天或要求重置，清空记录
    if reset or data.get("date") != today:
        logger.info(f"重置去重记录 (reset={reset}, old_date={data.get('date')}, today={today})")
        data = {"date": today, "ids": []}
    
    pushed_ids: Set[str] = set(data.get("ids", []))
    new_items = []
    new_ids = []
    
    for item in items:
        title = getattr(item, "title", "") or item.get("title", "")
        url = getattr(item, "url", "") or item.get("url", "")
        
        item_id = _get_news_id(title, url)
        
        if item_id not in pushed_ids:
            new_items.append(item)
            new_ids.append(item_id)
    
    # 更新记录
    if new_ids:
        data["ids"] = list(pushed_ids) + new_ids
        # 限制记录数量（保留最近500条）
        if len(data["ids"]) > 500:
            data["ids"] = data["ids"][-500:]
        save_pushed_ids(data)
    
    logger.info(f"去重: 总计 {len(items)} 条，已推送 {len(items) - len(new_items)} 条，新增 {len(new_items)} 条")
    return new_items


def mark_as_pushed(items: list):
    """标记新闻为已推送"""
    today = datetime.now().strftime("%Y-%m-%d")
    data = load_pushed_ids()
    
    if data.get("date") != today:
        data = {"date": today, "ids": []}
    
    pushed_ids = set(data.get("ids", []))
    
    for item in items:
        title = getattr(item, "title", "") or item.get("title", "")
        url = getattr(item, "url", "") or item.get("url", "")
        item_id = _get_news_id(title, url)
        pushed_ids.add(item_id)
    
    data["ids"] = list(pushed_ids)
    save_pushed_ids(data)


def clear_pushed_ids():
    """清空推送记录（用于每日早报后重置）"""
    today = datetime.now().strftime("%Y-%m-%d")
    save_pushed_ids({"date": today, "ids": []})
    logger.info("已清空去重记录")
