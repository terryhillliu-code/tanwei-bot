"""RSS 信息源"""
import re
from html import unescape

import feedparser
import httpx

from tanwei.core.config import SourceConfig
from tanwei.core.logger import get_logger
from tanwei.sources.base import BaseSource, SourceResult, register_source

logger = get_logger("source.rss")

MAX_ITEMS = 20
SUMMARY_MAX_LEN = 500
FETCH_TIMEOUT = 30


def _clean_html(text: str) -> str:
    """简单去除 HTML 标签"""
    text = re.sub(r"<[^>]+>", "", text)
    return unescape(text).strip()


@register_source("rss")
class RSSSource(BaseSource):
    async def fetch(self, source_config: SourceConfig) -> list[SourceResult]:
        label = source_config.label or source_config.url
        logger.info(f"采集 RSS: {label}")

        try:
            async with httpx.AsyncClient(timeout=FETCH_TIMEOUT) as client:
                resp = await client.get(
                    source_config.url,
                    headers={"User-Agent": "tanwei-bot/0.1"},
                    follow_redirects=True,
                )
                resp.raise_for_status()
                content = resp.text
        except Exception as e:
            logger.warning(f"RSS 获取失败 [{label}]: {e}")
            return []

        try:
            feed = feedparser.parse(content)
        except Exception as e:
            logger.warning(f"RSS 解析失败 [{label}]: {e}")
            return []

        results = []
        for entry in feed.entries[:MAX_ITEMS]:
            title = entry.get("title", "").strip()
            if not title:
                continue

            summary = entry.get("summary", "") or entry.get("description", "")
            summary = _clean_html(summary)
            if len(summary) > SUMMARY_MAX_LEN:
                summary = summary[:SUMMARY_MAX_LEN] + "..."

            link = entry.get("link", "")
            published = entry.get("published", "") or entry.get("updated", "")

            results.append(SourceResult(
                title=title,
                summary=summary,
                url=link,
                source_label=label,
                published=published,
                raw=dict(entry),
            ))

        logger.info(f"RSS 采集完成 [{label}]: {len(results)} 条")
        return results
