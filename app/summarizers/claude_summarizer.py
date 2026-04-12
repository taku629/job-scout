"""Claude API を使った日本語要約生成モジュール"""
import os
from typing import Any

import anthropic

from app.collectors.base import Job
from app.utils.logger import logger

# システムプロンプトはキャッシュ対象として定義（prompt caching で節約）
SYSTEM_PROMPT = """あなたは就職・インターン活動をサポートするAIアシスタントです。
求人情報を読んで、日本語で簡潔かつ有益な要約を生成してください。

要約のルール:
1. 2〜4文で、求人の要点（業務内容・技術スタック・働き方）をまとめる
2. 就活生・転職者が「自分に関係あるか」をすぐ判断できる情報を優先する
3. 不明な点は無理に書かず「詳細はリンクを確認」と記載する
4. 日本語で出力するが、技術用語（Python, AWS等）は英語のままでよい"""


class ClaudeSummarizer:
    """
    Anthropic Claude API を使って求人の日本語要約を生成する。

    - prompt caching を活用してコストを削減
    - エラー時はフォールバック要約を返す（処理を止めない）
    """

    def __init__(self, config: dict[str, Any] | None = None) -> None:
        self.config = config or {}
        self.model = os.getenv(
            "SUMMARIZER_MODEL",
            "claude-haiku-4-5-20251001",
        )
        self.max_length = self.config.get("max_summary_length", 300)
        api_key = os.getenv("ANTHROPIC_API_KEY", "")
        if not api_key:
            logger.warning("ANTHROPIC_API_KEY が設定されていません。要約はスキップされます。")
        self.client = anthropic.Anthropic(api_key=api_key) if api_key else None

    def summarize_bulk(self, jobs: list[Job], filter_config: dict[str, Any]) -> list[Job]:
        """求人リストを一括要約する"""
        if not self.client:
            logger.info("要約をスキップ（API キーなし）")
            return jobs

        keywords = filter_config.get("keywords", [])
        locations = filter_config.get("locations", [])

        for job in jobs:
            try:
                job.summary, job.match_reason = self._summarize_one(job, keywords, locations)
            except Exception as e:
                logger.warning(f"要約失敗 ({job.title}): {e}")
                job.summary = f"【{job.source_name}】{job.title}"
                job.match_reason = "詳細はリンクを確認してください。"
        return jobs

    def _summarize_one(
        self,
        job: Job,
        keywords: list[str],
        locations: list[str],
    ) -> tuple[str, str]:
        """1件の求人を要約して (summary, match_reason) を返す"""
        user_prompt = self._build_user_prompt(job, keywords, locations)

        response = self.client.messages.create(
            model=self.model,
            max_tokens=600,
            system=[
                {
                    "type": "text",
                    "text": SYSTEM_PROMPT,
                    "cache_control": {"type": "ephemeral"},  # prompt caching
                }
            ],
            messages=[{"role": "user", "content": user_prompt}],
        )

        raw_text = response.content[0].text.strip()
        return self._parse_response(raw_text)

    def _build_user_prompt(
        self,
        job: Job,
        keywords: list[str],
        locations: list[str],
    ) -> str:
        kw_str = ", ".join(keywords[:10]) if keywords else "指定なし"
        loc_str = ", ".join(locations[:5]) if locations else "指定なし"

        return f"""以下の求人情報を要約してください。

【求人情報】
タイトル: {job.title}
会社: {job.company or "不明"}
勤務地: {job.location or "不明"}
概要: {job.description[:800] or "情報なし"}
URL: {job.url}
マッチしたキーワード: {", ".join(job.matched_keywords) or "なし"}

【ユーザーの希望条件】
- 興味キーワード: {kw_str}
- 希望勤務地: {loc_str}

以下の形式で出力してください:

要約:
（2〜4文で求人の要点を書く）

マッチ理由:
（この求人がユーザーの条件に合っている理由を1〜2文で書く）"""

    def _parse_response(self, text: str) -> tuple[str, str]:
        """レスポンステキストから要約とマッチ理由を抽出する"""
        summary = ""
        match_reason = ""

        lines = text.split("\n")
        current_section = None

        for line in lines:
            stripped = line.strip()
            if stripped.startswith("要約:") or stripped == "要約:":
                current_section = "summary"
                content = stripped.removeprefix("要約:").strip()
                if content:
                    summary += content + " "
            elif stripped.startswith("マッチ理由:") or stripped == "マッチ理由:":
                current_section = "match_reason"
                content = stripped.removeprefix("マッチ理由:").strip()
                if content:
                    match_reason += content + " "
            elif stripped and current_section == "summary":
                summary += stripped + " "
            elif stripped and current_section == "match_reason":
                match_reason += stripped + " "

        summary = summary.strip()[: self.max_length]
        match_reason = match_reason.strip()[:200]

        # パースに失敗した場合はテキスト全体を要約として扱う
        if not summary:
            summary = text[: self.max_length]

        return summary, match_reason
