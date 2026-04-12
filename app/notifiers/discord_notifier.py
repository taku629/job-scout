"""Discord Webhook 通知モジュール"""
import os
import time
from typing import Any

import requests

from app.collectors.base import Job
from app.notifiers.base import BaseNotifier
from app.utils.logger import logger

# Discord の1メッセージあたりの最大文字数
DISCORD_MAX_CHARS = 2000


class DiscordNotifier(BaseNotifier):
    """
    Discord Webhook を使って求人情報を通知する。

    - embed（カード形式）で見やすく表示
    - 文字数超過時は自動的にメッセージを分割
    - レート制限（429）時はリトライ
    """

    def __init__(self, config: dict[str, Any] | None = None) -> None:
        self.config = config or {}
        self.webhook_url = os.getenv("DISCORD_WEBHOOK_URL", "")
        self.max_per_message: int = self.config.get("notification", {}).get(
            "max_jobs_per_message", 5
        )

    def notify(self, jobs: list[Job]) -> bool:
        if not self.webhook_url:
            logger.warning("DISCORD_WEBHOOK_URL が設定されていません。通知をスキップします。")
            return False
        if not jobs:
            logger.info("通知する求人がありません。")
            return True

        # バッチに分けて送信
        success = True
        batches = [jobs[i : i + self.max_per_message] for i in range(0, len(jobs), self.max_per_message)]

        header_sent = False
        for batch in batches:
            if not header_sent:
                self._send_header(len(jobs))
                header_sent = True
                time.sleep(0.5)

            for i, job in enumerate(batch):
                ok = self._send_embed(job)
                if not ok:
                    success = False
                time.sleep(0.5)  # レート制限回避

        return success

    def _send_header(self, total: int) -> bool:
        """ヘッダーメッセージを送信する"""
        payload: dict[str, Any] = {
            "embeds": [
                {
                    "title": f"🔍 job-scout: 新着求人 {total} 件",
                    "description": "条件に合致する新着求人が見つかりました。",
                    "color": 0x5865F2,  # Discord blurple
                }
            ]
        }
        return self._post(payload)

    def _send_embed(self, job: Job) -> bool:
        """1件の求人を embed で送信する"""
        fields: list[dict[str, Any]] = []

        if job.company:
            fields.append({"name": "🏢 会社", "value": job.company[:100], "inline": True})
        if job.location:
            fields.append({"name": "📍 勤務地", "value": job.location[:100], "inline": True})
        if job.matched_keywords:
            kw_str = ", ".join(job.matched_keywords[:8])
            fields.append({"name": "🏷️ マッチキーワード", "value": kw_str[:200], "inline": False})

        description_parts = []
        if job.summary:
            description_parts.append(job.summary[:500])
        if job.match_reason:
            description_parts.append(f"\n**💡 マッチ理由:**\n{job.match_reason[:200]}")

        description = "\n".join(description_parts) if description_parts else job.description[:300]

        embed: dict[str, Any] = {
            "title": job.title[:256],
            "url": job.url,
            "description": description[:2048],
            "color": 0x57F287,  # green
            "fields": fields,
            "footer": {"text": f"via {job.source_name}"},
        }

        payload: dict[str, Any] = {"embeds": [embed]}
        return self._post(payload)

    def _post(self, payload: dict[str, Any], retry: int = 3) -> bool:
        """Webhook にPOSTする（レート制限時はリトライ）"""
        for attempt in range(retry):
            try:
                response = requests.post(
                    self.webhook_url,
                    json=payload,
                    timeout=10,
                )
                if response.status_code == 204:
                    return True
                elif response.status_code == 429:
                    retry_after = response.json().get("retry_after", 5)
                    logger.warning(f"Discord レート制限: {retry_after}秒後にリトライ")
                    time.sleep(float(retry_after))
                    continue
                else:
                    logger.error(
                        f"Discord 通知失敗: HTTP {response.status_code} - {response.text[:200]}"
                    )
                    return False
            except requests.RequestException as e:
                logger.error(f"Discord 送信エラー (試行 {attempt + 1}/{retry}): {e}")
                time.sleep(2**attempt)

        return False
