"""通知器のファクトリー関数

新しい通知チャンネルの追加手順:
  1. app/notifiers/xxx_notifier.py を作成し BaseNotifier を継承
  2. 下記 _CHANNEL_REGISTRY に1行追加するだけで自動で有効化される

  例:
    {
        "name": "LINE",
        "env_keys": ["LINE_CHANNEL_TOKEN", "LINE_USER_ID"],
        "factory": lambda cfg: LineNotifier(cfg),
    },
"""
import os
from collections.abc import Callable
from typing import Any

from app.notifiers.base import BaseNotifier
from app.notifiers.discord_notifier import DiscordNotifier
from app.notifiers.email_notifier import EmailNotifier
from app.notifiers.slack_notifier import SlackNotifier
from app.notifiers.telegram_notifier import TelegramNotifier
from app.utils.logger import logger

# ------------------------------------------------------------------
# チャンネルレジストリ
#   name      : ログ表示名
#   env_keys  : すべてのキーが非空のとき有効化する環境変数
#   factory   : config を受け取り BaseNotifier を返す callable
# ------------------------------------------------------------------
_CHANNEL_REGISTRY: list[dict[str, Any]] = [
    {
        "name": "Email",
        "env_keys": ["SMTP_USER", "SMTP_PASSWORD"],
        "factory": lambda cfg: EmailNotifier(cfg),
    },
    {
        "name": "Discord",
        "env_keys": ["DISCORD_WEBHOOK_URL"],
        "factory": lambda cfg: DiscordNotifier(cfg),
    },
    {
        "name": "Telegram",
        "env_keys": ["TELEGRAM_BOT_TOKEN", "TELEGRAM_CHAT_ID"],
        "factory": lambda cfg: TelegramNotifier(cfg),
    },
    {
        "name": "Slack",
        "env_keys": ["SLACK_WEBHOOK_URL"],
        "factory": lambda cfg: SlackNotifier(cfg),
    },
    # 将来の追加例:
    # {
    #     "name": "LINE",
    #     "env_keys": ["LINE_CHANNEL_TOKEN", "LINE_USER_ID"],
    #     "factory": lambda cfg: LineNotifier(cfg),
    # },
]


def create_notifiers(config: dict[str, Any]) -> list[BaseNotifier]:
    """
    _CHANNEL_REGISTRY を走査し、必要な環境変数がすべて設定されている
    チャンネルのノティファイアを返す。
    複数チャンネルを同時に有効化した場合は全チャンネルに通知する。
    """
    notifiers: list[BaseNotifier] = []

    for channel in _CHANNEL_REGISTRY:
        if all(os.getenv(key) for key in channel["env_keys"]):
            notifier: BaseNotifier = channel["factory"](config)
            notifiers.append(notifier)
            logger.info(f"{channel['name']} 通知を有効化")

    if not notifiers:
        logger.warning(
            "通知チャンネルが設定されていません。"
            " .env に SMTP_USER+SMTP_PASSWORD / DISCORD_WEBHOOK_URL /"
            " TELEGRAM_BOT_TOKEN+TELEGRAM_CHAT_ID / SLACK_WEBHOOK_URL"
            " のいずれかを設定してください。"
        )

    return notifiers
