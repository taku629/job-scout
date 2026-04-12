"""Slack Incoming Webhook 通知モジュール（オプション）

セットアップ:
  1. Slack App を作成: https://api.slack.com/apps
  2. Incoming Webhooks を有効化
  3. Webhook URL を取得
  4. .env に設定:
     SLACK_WEBHOOK_URL=https://hooks.slack.com/services/...
"""
import os
import time
from typing import Any

import requests

from app.collectors.base import Job
from app.notifiers.base import BaseNotifier
from app.utils.logger import logger


class SlackNotifier(BaseNotifier):
    """Slack Incoming Webhook を使って求人情報を通知する"""

    def __init__(self, config: dict[str, Any] | None = None) -> None:
        self.config = config or {}
        self.webhook_url = os.getenv("SLACK_WEBHOOK_URL", "")
        self.max_per_message: int = self.config.get("notification", {}).get(
            "max_jobs_per_message", 5
        )

    def notify(self, jobs: list[Job]) -> bool:
        if not self.webhook_url:
            logger.warning("SLACK_WEBHOOK_URL が設定されていません。")
            return False
        if not jobs:
            return True

        success = True
        for i, job in enumerate(jobs, 1):
            payload = self._build_payload(job, i, len(jobs))
            ok = self._post(payload)
            if not ok:
                success = False
            time.sleep(1)  # Slack のレート制限対策

        return success

    def _build_payload(self, job: Job, index: int, total: int) -> dict[str, Any]:
        header = f"🔍 job-scout 新着求人 ({index}/{total})"
        text_parts = [f"*{job.title}*"]
        if job.company:
            text_parts.append(f"🏢 {job.company}")
        if job.location:
            text_parts.append(f"📍 {job.location}")
        if job.summary:
            text_parts.append(f"\n{job.summary}")
        if job.match_reason:
            text_parts.append(f"\n💡 {job.match_reason}")

        blocks: list[dict[str, Any]] = [
            {"type": "header", "text": {"type": "plain_text", "text": header}},
            {
                "type": "section",
                "text": {"type": "mrkdwn", "text": "\n".join(text_parts)[:3000]},
            },
            {
                "type": "actions",
                "elements": [
                    {
                        "type": "button",
                        "text": {"type": "plain_text", "text": "詳細を見る"},
                        "url": job.url,
                        "action_id": f"view_job_{job.id}",
                    }
                ],
            },
            {"type": "divider"},
        ]

        return {"blocks": blocks}

    def _post(self, payload: dict[str, Any]) -> bool:
        try:
            response = requests.post(self.webhook_url, json=payload, timeout=10)
            if response.status_code == 200:
                return True
            else:
                logger.error(f"Slack 送信失敗: {response.status_code} - {response.text[:200]}")
                return False
        except requests.RequestException as e:
            logger.error(f"Slack 送信エラー: {e}")
            return False
