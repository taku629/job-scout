"""求人フィルタリングモジュール

config.yaml の filters セクションに基づいて求人をスコアリングし、
条件に合致する求人だけを抽出する。
"""
import re
from typing import Any

from app.collectors.base import Job
from app.utils.logger import logger


class JobFilter:
    """
    求人にスコアを付け、min_score 以上のものだけを返す。

    スコア計算:
      +2 点  : title にキーワードマッチ
      +1 点  : description にキーワードマッチ
      +1 点  : location にマッチ
      +1 点  : job_type にマッチ
      -999 点: 除外キーワードが含まれる → 強制除外
    """

    def __init__(self, filter_config: dict[str, Any]) -> None:
        self.keywords: list[str] = [k.lower() for k in filter_config.get("keywords", [])]
        self.locations: list[str] = [l.lower() for l in filter_config.get("locations", [])]
        self.job_types: list[str] = [j.lower() for j in filter_config.get("job_types", [])]
        self.exclude_keywords: list[str] = [e.lower() for e in filter_config.get("exclude_keywords", [])]
        self.min_score: int = filter_config.get("min_score", 1)

    def filter(self, jobs: list[Job]) -> list[Job]:
        """条件に合致する求人だけを返す"""
        result: list[Job] = []
        for job in jobs:
            scored = self._score(job)
            if scored.score >= self.min_score:
                result.append(scored)
        logger.info(f"フィルタ結果: {len(jobs)} 件 → {len(result)} 件通過")
        return result

    def _score(self, job: Job) -> Job:
        title_lower = job.title.lower()
        desc_lower = job.description.lower()
        loc_lower = job.location.lower()

        # --- 除外キーワードチェック ---
        combined = f"{title_lower} {desc_lower}"
        for excl in self.exclude_keywords:
            if self._word_in(excl, combined):
                job.score = -999
                return job

        score = 0
        matched: list[str] = []

        # --- キーワードマッチ ---
        for kw in self.keywords:
            if self._word_in(kw, title_lower):
                score += 2
                matched.append(kw)
            elif self._word_in(kw, desc_lower):
                score += 1
                matched.append(kw)

        # --- 勤務地マッチ ---
        if self.locations:
            for loc in self.locations:
                if loc in loc_lower or loc in desc_lower:
                    score += 1
                    break

        # --- 雇用形態マッチ ---
        if self.job_types:
            for jt in self.job_types:
                if self._word_in(jt, combined):
                    score += 1
                    break

        job.score = score
        job.matched_keywords = list(dict.fromkeys(matched))  # 重複除去
        return job

    def _word_in(self, word: str, text: str) -> bool:
        """単語が文中に含まれるか（部分一致）"""
        return word in text
