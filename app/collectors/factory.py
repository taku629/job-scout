"""収集器のファクトリー関数"""
from typing import Any

from app.collectors.base import BaseCollector
from app.collectors.html_collector import HTMLCollector
from app.collectors.rss_collector import RSSCollector
from app.utils.logger import logger


def create_collector(source: dict[str, Any], config: dict[str, Any]) -> BaseCollector | None:
    """ソース設定から適切なコレクターを生成して返す"""
    collector_type = source.get("type", "").lower()

    if collector_type == "rss":
        return RSSCollector(source, config)
    elif collector_type == "html":
        return HTMLCollector(source, config)
    else:
        logger.warning(f"未知のコレクタータイプ: '{collector_type}' (source: {source.get('name')})")
        return None
