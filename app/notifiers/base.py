"""通知器の基底クラス"""
from abc import ABC, abstractmethod

from app.collectors.base import Job


class BaseNotifier(ABC):
    """すべての通知器が継承する基底クラス"""

    @abstractmethod
    def notify(self, jobs: list[Job]) -> bool:
        """
        求人リストを通知する。

        Returns:
            True: 通知成功
            False: 通知失敗（エラー）
        """
        ...

    def _format_job(self, job: Job, index: int) -> str:
        """求人を通知テキストに変換する（サブクラスでオーバーライド可）"""
        lines = [f"**{index}. {job.title}**"]
        if job.company:
            lines.append(f"🏢 {job.company}")
        if job.location:
            lines.append(f"📍 {job.location}")
        if job.summary:
            lines.append(f"\n{job.summary}")
        if job.match_reason:
            lines.append(f"\n💡 {job.match_reason}")
        lines.append(f"\n🔗 {job.url}")
        return "\n".join(lines)
