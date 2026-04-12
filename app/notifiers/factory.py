"""通知器のファクトリー関数"""
import os
from typing import Any

from app.notifiers.base import BaseNotifier
from app.notifiers.discord_notifier import DiscordNotifier
from app.notifiers.slack_notifier import SlackNotifier
from app.notifiers.telegram_notifier import TelegramNotifier
from app.utils.logger import logger


def create_notifiers(config: dict[str, Any]) -> list[BaseNotifier]:
    """
    環境変数に設定されている通知チャンネルのノティファイアを返す。
    複数チャンネルに同時通知したい場合は複数の環境変数を設定する。
    """
    notifiers: list[BaseNotifier] = []

    if os.getenv("DISCORD_WEBHOOK_URL"):
        notifiers.append(DiscordNotifier(config))
        logger.info("Discord 通知を有効化")

    if os.getenv("TELEGRAM_BOT_TOKEN") and os.getenv("TELEGRAM_CHAT_ID"):
        notifiers.append(TelegramNotifier(config))
        logger.info("Telegram 通知を有効化")

    if os.getenv("SLACK_WEBHOOK_URL"):
        notifiers.append(SlackNotifier(config))
        logger.info("Slack 通知を有効化")

    if not notifiers:
        logger.warning(
            "通知チャンネルが設定されていません。"
            " .env に DISCORD_WEBHOOK_URL / TELEGRAM_BOT_TOKEN / SLACK_WEBHOOK_URL を設定してください。"
        )

    return notifiers
