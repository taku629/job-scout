"""収集器の基底クラスと求人データモデル"""
import hashlib
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class Job(BaseModel):
    """収集した求人1件を表すデータモデル"""

    id: str = Field(description="求人の一意ID（URLまたは内容から生成）")
    title: str = Field(default="", description="求人タイトル")
    company: str = Field(default="", description="会社名")
    location: str = Field(default="", description="勤務地")
    job_type: str = Field(default="", description="雇用形態")
    description: str = Field(default="", description="求人概要テキスト")
    url: str = Field(default="", description="求人詳細URL")
    source_name: str = Field(default="", description="収集元ソース名")
    tags: list[str] = Field(default_factory=list, description="ソースのタグ")
    collected_at: str = Field(
        default_factory=lambda: datetime.utcnow().isoformat(),
        description="収集日時（ISO形式）",
    )
    raw: dict[str, Any] = Field(
        default_factory=dict,
        description="元データ（デバッグ用）",
        exclude=True,
    )
    # フィルタ・要約結果（後工程で付与）
    score: int = Field(default=0, description="マッチスコア")
    matched_keywords: list[str] = Field(default_factory=list, description="マッチしたキーワード")
    summary: str = Field(default="", description="AI生成の日本語要約")
    match_reason: str = Field(default="", description="条件一致理由")

    @classmethod
    def make_id(cls, url: str, title: str = "") -> str:
        """URLとタイトルからIDを生成する"""
        raw = f"{url}|{title}"
        return hashlib.sha256(raw.encode()).hexdigest()[:16]

    def to_dict(self) -> dict[str, Any]:
        return self.model_dump(exclude={"raw"})


class BaseCollector(ABC):
    """すべての収集器が継承する基底クラス"""

    def __init__(self, source: dict[str, Any], config: dict[str, Any]) -> None:
        self.source = source
        self.config = config
        self.name: str = source.get("name", "unknown")
        self.url: str = source.get("url", "")
        self.tags: list[str] = source.get("tags", [])

    @abstractmethod
    def collect(self) -> list[Job]:
        """求人リストを収集して返す。エラー時は空リストを返す。"""
        ...
