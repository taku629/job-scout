"""求人データの永続化ストレージモジュール"""
import json
import os
from datetime import datetime
from pathlib import Path
from typing import Any

from app.utils.logger import logger


class JobStorage:
    """
    取得済み求人と送信済みIDをJSONファイルで管理する。

    ファイル:
      - seen_ids.json   : 送信済み求人IDのセット（新着判定用）
      - jobs_history.json : 取得した求人の詳細履歴
    """

    def __init__(self, data_dir: str | None = None) -> None:
        self.data_dir = Path(data_dir or os.getenv("DATA_DIR", "data"))
        self.data_dir.mkdir(parents=True, exist_ok=True)

        self.seen_ids_path = self.data_dir / "seen_ids.json"
        self.history_path = self.data_dir / "jobs_history.json"

        self._seen_ids: set[str] = self._load_seen_ids()

    # ------------------------------------------------------------------
    # 送信済みID管理
    # ------------------------------------------------------------------

    def _load_seen_ids(self) -> set[str]:
        if not self.seen_ids_path.exists():
            return set()
        try:
            with open(self.seen_ids_path, encoding="utf-8") as f:
                data = json.load(f)
            return set(data.get("ids", []))
        except (json.JSONDecodeError, KeyError) as e:
            logger.warning(f"seen_ids.json の読み込みに失敗しました: {e}")
            return set()

    def _save_seen_ids(self) -> None:
        payload = {
            "updated_at": datetime.utcnow().isoformat(),
            "count": len(self._seen_ids),
            "ids": list(self._seen_ids),
        }
        self._atomic_write(self.seen_ids_path, payload)

    def is_seen(self, job_id: str) -> bool:
        """既に処理済みの求人IDかどうかを返す"""
        return job_id in self._seen_ids

    def mark_seen(self, job_id: str) -> None:
        """求人IDを送信済みとしてマークする"""
        self._seen_ids.add(job_id)
        self._save_seen_ids()

    def mark_seen_bulk(self, job_ids: list[str]) -> None:
        """複数の求人IDを一括で送信済みにする"""
        self._seen_ids.update(job_ids)
        self._save_seen_ids()

    # ------------------------------------------------------------------
    # 求人履歴管理
    # ------------------------------------------------------------------

    def save_jobs(self, jobs: list[dict[str, Any]]) -> None:
        """求人リストを履歴ファイルに追記する"""
        history = self._load_history()
        history.extend(jobs)
        self._atomic_write(self.history_path, history)

    def _load_history(self) -> list[dict[str, Any]]:
        if not self.history_path.exists():
            return []
        try:
            with open(self.history_path, encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, ValueError) as e:
            logger.warning(f"jobs_history.json の読み込みに失敗しました: {e}")
            return []

    # ------------------------------------------------------------------
    # ユーティリティ
    # ------------------------------------------------------------------

    def _atomic_write(self, path: Path, data: Any) -> None:
        """書き込み中のクラッシュを防ぐため、一時ファイル経由で書き込む"""
        tmp_path = path.with_suffix(".tmp")
        try:
            with open(tmp_path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            tmp_path.replace(path)
        except Exception as e:
            logger.error(f"ファイル書き込みエラー ({path}): {e}")
            if tmp_path.exists():
                tmp_path.unlink(missing_ok=True)
            raise

    @property
    def seen_count(self) -> int:
        return len(self._seen_ids)
