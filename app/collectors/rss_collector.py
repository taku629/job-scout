"""RSS/Atom フィードから求人情報を収集するコレクター"""
import time
from typing import Any

import feedparser
import requests

from app.collectors.base import BaseCollector, Job
from app.utils.logger import logger


class RSSCollector(BaseCollector):
    """
    feedparser を使って RSS/Atom フィードから求人を収集する。

    robots.txt や利用規約に反しないよう、
    - 適切な User-Agent を設定
    - リクエスト間隔を設ける
    """

    def __init__(self, source: dict[str, Any], config: dict[str, Any]) -> None:
        super().__init__(source, config)
        collection_cfg = config.get("collection", {})
        self.request_delay = collection_cfg.get("request_delay_seconds", 2)
        self.timeout = collection_cfg.get("request_timeout_seconds", 15)
        self.user_agent = collection_cfg.get(
            "user_agent",
            "job-scout-bot/1.0 (personal use)",
        )
        self.max_jobs = collection_cfg.get("max_jobs_per_source", 50)

    def collect(self) -> list[Job]:
        logger.info(f"[RSS] 収集開始: {self.name} ({self.url})")
        try:
            feed = self._fetch_feed()
            if feed is None:
                return []
            jobs = self._parse_entries(feed)
            logger.info(f"[RSS] {self.name}: {len(jobs)} 件取得")
            return jobs
        except Exception as e:
            logger.error(f"[RSS] {self.name} 収集エラー: {e}", exc_info=True)
            return []
        finally:
            time.sleep(self.request_delay)

    def _fetch_feed(self) -> feedparser.FeedParserDict | None:
        headers = {"User-Agent": self.user_agent}
        try:
            response = requests.get(
                self.url,
                headers=headers,
                timeout=self.timeout,
            )
            response.raise_for_status()
        except requests.RequestException as e:
            logger.warning(f"[RSS] {self.name} フェッチ失敗: {e}")
            return None

        feed = feedparser.parse(response.content)
        if feed.bozo:
            # bozo=True はパースエラー。データが取れていれば続行
            logger.warning(f"[RSS] {self.name} フィードのパース警告: {feed.bozo_exception}")
        return feed

    def _parse_entries(self, feed: feedparser.FeedParserDict) -> list[Job]:
        jobs: list[Job] = []
        entries = feed.entries[: self.max_jobs]

        for entry in entries:
            try:
                job = self._entry_to_job(entry)
                jobs.append(job)
            except Exception as e:
                logger.debug(f"[RSS] エントリのパース失敗: {e}")

        return jobs

    def _entry_to_job(self, entry: Any) -> Job:
        url = getattr(entry, "link", "") or getattr(entry, "id", "")
        title = getattr(entry, "title", "")
        company = self._extract_company(entry)
        location = self._extract_location(entry)
        description = self._extract_description(entry)

        return Job(
            id=Job.make_id(url, title),
            title=self._clean_text(title),
            company=self._clean_text(company),
            location=self._clean_text(location),
            description=self._clean_text(description)[:2000],
            url=url,
            source_name=self.name,
            tags=self.tags,
        )

    def _extract_company(self, entry: Any) -> str:
        # フィードによって会社名のフィールド名が異なる
        for attr in ("author", "author_detail", "publisher"):
            val = getattr(entry, attr, None)
            if val:
                if isinstance(val, dict):
                    return val.get("name", "")
                return str(val)
        # タグから会社名を探す
        tags = getattr(entry, "tags", []) or []
        for tag in tags:
            if hasattr(tag, "label") and tag.label:
                return tag.label
        return ""

    def _extract_location(self, entry: Any) -> str:
        for attr in ("location", "georss_featurename"):
            val = getattr(entry, attr, None)
            if val:
                return str(val)
        # タグから勤務地を探す（"remote", "tokyo" 等）
        tags = getattr(entry, "tags", []) or []
        location_hints = []
        for tag in tags:
            term = getattr(tag, "term", "") or ""
            if any(kw in term.lower() for kw in ("remote", "tokyo", "japan", "osaka", "us", "eu")):
                location_hints.append(term)
        return ", ".join(location_hints)

    def _extract_description(self, entry: Any) -> str:
        for attr in ("summary", "content", "description"):
            val = getattr(entry, attr, None)
            if val:
                if isinstance(val, list) and val:
                    return val[0].get("value", "")
                return str(val)
        return ""

    def _clean_text(self, text: str) -> str:
        """HTMLタグを除去してテキストをクリーニングする"""
        import re
        text = re.sub(r"<[^>]+>", " ", text)
        text = re.sub(r"\s+", " ", text)
        return text.strip()
