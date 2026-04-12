"""Telegram Bot API 通知モジュール（オプション）

セットアップ:
  1. @BotFather で Bot を作成し、BOT_TOKEN を取得
  2. Bot をチャンネル/グループに追加
  3. Chat ID を確認: https://api.telegram.org/bot<TOKEN>/getUpdates
  4. .env に設定:
     TELEGRAM_BOT_TOKEN=xxxx
     TELEGRAM_CHAT_ID=xxxx
"""
import os
import time
from typing import Any

import requests

from app.collectors.base import Job
from app.notifiers.base import BaseNotifier
from app.utils.logger import logger

TELEGRAM_API_BASE = "https://api.telegram.org/bot{token}"


class TelegramNotifier(BaseNotifier):
    """Telegram Bot API を使って求人情報を通知する"""

    def __init__(self, config: dict[str, Any] | None = None) -> None:
        self.config = config or {}
        self.bot_token = os.getenv("TELEGRAM_BOT_TOKEN", "")
        self.chat_id = os.getenv("TELEGRAM_CHAT_ID", "")
        self.max_per_message: int = self.config.get("notification", {}).get(
            "max_jobs_per_message", 5
        )

    def notify(self, jobs: list[Job]) -> bool:
        if not self.bot_token or not self.chat_id:
            logger.warning("TELEGRAM_BOT_TOKEN / TELEGRAM_CHAT_ID が設定されていません。")
            return False
        if not jobs:
            return True

        success = True
        # ヘッダー送信
        self._send_text(f"🔍 *job-scout: 新着求人 {len(jobs)} 件*\n条件に合致する求人が見つかりました。")
        time.sleep(0.5)

        for i, job in enumerate(jobs, 1):
            text = self._format_job_markdown(job, i)
            ok = self._send_text(text)
            if not ok:
                success = False
            time.sleep(0.5)

        return success

    def _format_job_markdown(self, job: Job, index: int) -> str:
        lines = [f"*{index}. {self._escape(job.title)}*"]
        if job.company:
            lines.append(f"🏢 {self._escape(job.company)}")
        if job.location:
            lines.append(f"📍 {self._escape(job.location)}")
        if job.summary:
            lines.append(f"\n{self._escape(job.summary)}")
        if job.match_reason:
            lines.append(f"\n💡 {self._escape(job.match_reason)}")
        lines.append(f"\n🔗 {job.url}")
        return "\n".join(lines)

    def _escape(self, text: str) -> str:
        """Markdown の特殊文字をエスケープ"""
        for ch in ["_", "*", "[", "]", "(", ")", "~", "`", ">", "#", "+", "-", "=", "|", "{", "}", ".", "!"]:
            text = text.replace(ch, f"\\{ch}")
        return text

    def _send_text(self, text: str) -> bool:
        api_url = f"https://api.telegram.org/bot{self.bot_token}/sendMessage"
        payload = {
            "chat_id": self.chat_id,
            "text": text[:4096],
            "parse_mode": "MarkdownV2",
            "disable_web_page_preview": True,
        }
        try:
            response = requests.post(api_url, json=payload, timeout=10)
            if response.status_code == 200:
                return True
            else:
                logger.error(f"Telegram 送信失敗: {response.status_code} - {response.text[:200]}")
                return False
        except requests.RequestException as e:
            logger.error(f"Telegram 送信エラー: {e}")
            return False
