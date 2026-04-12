"""ロギング設定モジュール"""
import logging
import os
import sys
from pathlib import Path


def setup_logger(name: str = "job-scout") -> logging.Logger:
    """アプリケーション全体で使うロガーを設定して返す"""
    log_level = os.getenv("LOG_LEVEL", "INFO").upper()
    numeric_level = getattr(logging, log_level, logging.INFO)

    logger = logging.getLogger(name)
    logger.setLevel(numeric_level)

    # 既にハンドラが設定されている場合はスキップ
    if logger.handlers:
        return logger

    formatter = logging.Formatter(
        fmt="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # コンソール出力
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(numeric_level)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    # ファイル出力（data/logs/ に保存）
    data_dir = Path(os.getenv("DATA_DIR", "data"))
    log_dir = data_dir / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    log_file = log_dir / "job-scout.log"

    file_handler = logging.FileHandler(log_file, encoding="utf-8")
    file_handler.setLevel(numeric_level)
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    return logger


# デフォルトロガー
logger = setup_logger()
