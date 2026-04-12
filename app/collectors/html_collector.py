"""HTMLページから求人情報をスクレイピングするコレクター

重要な注意事項:
  - このコレクターはサイトの robots.txt を事前に確認した上でのみ使用してください。
  - アクセス間隔は必ず設けてください（request_delay_seconds）。
  - 個人利用の範囲で、過剰なアクセスは行わないでください。
"""
import time
from typing import Any
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup

from app.collectors.base import BaseCollector, Job
from app.utils.logger import logger


class HTMLCollector(BaseCollector):
    """
    BeautifulSoup を使って静的HTMLページから求人を収集する。

    sources.yaml の parser セクションで CSS セレクタを設定する。
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
        self.parser_config: dict[str, str] = source.get("parser", {})

    def collect(self) -> list[Job]:
        logger.info(f"[HTML] 収集開始: {self.name} ({self.url})")
        try:
            html = self._fetch_page(self.url)
            if html is None:
                return []
            jobs = self._parse_html(html)
            logger.info(f"[HTML] {self.name}: {len(jobs)} 件取得")
            return jobs
        except Exception as e:
            logger.error(f"[HTML] {self.name} 収集エラー: {e}", exc_info=True)
            return []
        finally:
            time.sleep(self.request_delay)

    def _fetch_page(self, url: str) -> str | None:
        headers = {
            "User-Agent": self.user_agent,
            "Accept": "text/html,application/xhtml+xml",
            "Accept-Language": "en-US,en;q=0.9,ja;q=0.8",
        }
        try:
            response = requests.get(url, headers=headers, timeout=self.timeout)
            response.raise_for_status()
            return response.text
        except requests.RequestException as e:
            logger.warning(f"[HTML] {self.name} フェッチ失敗: {e}")
            return None

    def _parse_html(self, html: str) -> list[Job]:
        soup = BeautifulSoup(html, "lxml")
        jobs: list[Job] = []

        job_selector = self.parser_config.get("job_selector", "article")
        cards = soup.select(job_selector)[: self.max_jobs]

        if not cards:
            logger.warning(
                f"[HTML] {self.name}: セレクタ '{job_selector}' でカードが見つかりません。"
                " sources.yaml の parser 設定を確認してください。"
            )
            return []

        for card in cards:
            try:
                job = self._card_to_job(card)
                if job:
                    jobs.append(job)
            except Exception as e:
                logger.debug(f"[HTML] カードのパース失敗: {e}")

        return jobs

    def _card_to_job(self, card: BeautifulSoup) -> Job | None:
        title = self._select_text(card, "title_selector")
        company = self._select_text(card, "company_selector")
        location = self._select_text(card, "location_selector")
        description = self._select_text(card, "description_selector")
        url = self._select_link(card, "link_selector")

        if not title and not url:
            return None

        return Job(
            id=Job.make_id(url, title),
            title=title,
            company=company,
            location=location,
            description=description[:2000],
            url=url,
            source_name=self.name,
            tags=self.tags,
        )

    def _select_text(self, card: BeautifulSoup, selector_key: str) -> str:
        selector = self.parser_config.get(selector_key, "")
        if not selector:
            return ""
        el = card.select_one(selector)
        return el.get_text(strip=True) if el else ""

    def _select_link(self, card: BeautifulSoup, selector_key: str) -> str:
        selector = self.parser_config.get(selector_key, "a")
        el = card.select_one(selector)
        if el:
            href = el.get("href", "")
            if href:
                # 相対URLを絶対URLに変換
                return urljoin(self.url, str(href))
        # セレクタで見つからない場合は card 内最初の <a> を使う
        first_a = card.find("a")
        if first_a:
            return urljoin(self.url, str(first_a.get("href", "")))
        return self.url
