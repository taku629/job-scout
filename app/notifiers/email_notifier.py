"""Email (SMTP) 通知モジュール

セットアップ (Gmail):
  1. Googleアカウントで2段階認証を有効にする
  2. https://myaccount.google.com/apppasswords でアプリパスワードを発行
  3. .env に以下を設定:
     SMTP_HOST=smtp.gmail.com
     SMTP_PORT=587
     SMTP_USER=your-email@gmail.com
     SMTP_PASSWORD=your-app-password   # 通常のパスワードではなくアプリパスワード
     NOTIFY_TO=destination@gmail.com
"""
import os
import smtplib
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Any

from app.collectors.base import Job
from app.notifiers.base import BaseNotifier
from app.utils.logger import logger


class EmailNotifier(BaseNotifier):
    """SMTP経由でHTMLメールとテキストメールを送信する通知器"""

    def __init__(self, config: dict[str, Any] | None = None) -> None:
        self.config = config or {}
        self.host = os.getenv("SMTP_HOST", "smtp.gmail.com")
        self.port = int(os.getenv("SMTP_PORT", "587"))
        self.user = os.getenv("SMTP_USER", "")
        self.password = os.getenv("SMTP_PASSWORD", "")
        self.to_addr = os.getenv("NOTIFY_TO", self.user)

    def notify(self, jobs: list[Job]) -> bool:
        if not self.user or not self.password:
            logger.warning("SMTP_USER または SMTP_PASSWORD が設定されていません。メール通知をスキップします。")
            return False
        if not self.to_addr:
            logger.warning("NOTIFY_TO が設定されていません。メール通知をスキップします。")
            return False
        if not jobs:
            logger.info("通知する求人がありません。")
            return True

        subject = self._build_subject(len(jobs))
        text_body = self._build_text(jobs)
        html_body = self._build_html(jobs)

        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = self.user
        msg["To"] = self.to_addr
        msg.attach(MIMEText(text_body, "plain", "utf-8"))
        msg.attach(MIMEText(html_body, "html", "utf-8"))

        try:
            with smtplib.SMTP(self.host, self.port, timeout=30) as smtp:
                smtp.ehlo()
                smtp.starttls()
                smtp.login(self.user, self.password)
                smtp.sendmail(self.user, self.to_addr, msg.as_bytes())
            logger.info(f"メール送信完了: {self.to_addr} 宛に {len(jobs)} 件")
            return True
        except smtplib.SMTPAuthenticationError:
            logger.error("SMTP認証失敗: SMTP_USER / SMTP_PASSWORD を確認してください（Gmailはアプリパスワードを使用）")
            return False
        except smtplib.SMTPException as e:
            logger.error(f"SMTP送信エラー: {e}")
            return False
        except OSError as e:
            logger.error(f"SMTPサーバー接続エラー ({self.host}:{self.port}): {e}")
            return False

    # ------------------------------------------------------------------
    # 件名
    # ------------------------------------------------------------------
    def _build_subject(self, count: int) -> str:
        date_str = datetime.now().strftime("%Y/%m/%d")
        return f"【job-scout】新着求人 {count}件 - {date_str}"

    # ------------------------------------------------------------------
    # テキスト本文
    # ------------------------------------------------------------------
    def _build_text(self, jobs: list[Job]) -> str:
        date_str = datetime.now().strftime("%Y/%m/%d %H:%M")
        lines = [
            f"job-scout: 新着求人 {len(jobs)} 件",
            f"収集日時: {date_str}",
            "=" * 60,
            "",
        ]
        for i, job in enumerate(jobs, 1):
            lines.append(f"[{i}] {job.title}")
            if job.company:
                lines.append(f"    会社: {job.company}")
            if job.location:
                lines.append(f"    勤務地: {job.location}")
            if job.matched_keywords:
                lines.append(f"    キーワード: {', '.join(job.matched_keywords[:6])}")
            if job.summary:
                lines.append(f"    要約: {job.summary[:200]}")
            if job.match_reason:
                lines.append(f"    マッチ理由: {job.match_reason[:150]}")
            lines.append(f"    URL: {job.url}")
            lines.append("")
        lines += [
            "=" * 60,
            "このメールは job-scout によって自動送信されました。",
        ]
        return "\n".join(lines)

    # ------------------------------------------------------------------
    # HTML本文
    # ------------------------------------------------------------------
    def _build_html(self, jobs: list[Job]) -> str:
        date_str = datetime.now().strftime("%Y/%m/%d %H:%M")
        cards = "\n".join(self._job_card_html(i, job) for i, job in enumerate(jobs, 1))

        return f"""<!DOCTYPE html>
<html lang="ja">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<style>
  body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
         background: #f5f5f5; margin: 0; padding: 20px; color: #333; }}
  .container {{ max-width: 640px; margin: 0 auto; }}
  .header {{ background: #1a1a2e; color: white; padding: 24px;
             border-radius: 8px 8px 0 0; text-align: center; }}
  .header h1 {{ margin: 0; font-size: 20px; }}
  .header p  {{ margin: 6px 0 0; opacity: 0.7; font-size: 13px; }}
  .card {{ background: white; border: 1px solid #e0e0e0; border-radius: 8px;
           padding: 20px; margin: 12px 0; }}
  .card-title {{ font-size: 16px; font-weight: bold; margin: 0 0 8px; color: #1a1a2e; }}
  .meta {{ font-size: 13px; color: #666; margin: 4px 0; }}
  .keywords {{ margin: 10px 0; }}
  .kw-badge {{ display: inline-block; background: #e8f0fe; color: #1a73e8;
               font-size: 12px; padding: 2px 8px; border-radius: 12px; margin: 2px; }}
  .summary {{ font-size: 14px; background: #f9f9f9; padding: 10px;
              border-left: 3px solid #1a73e8; margin: 10px 0; border-radius: 0 4px 4px 0; }}
  .match-reason {{ font-size: 13px; color: #555; margin: 8px 0; }}
  .btn {{ display: inline-block; background: #1a73e8; color: white;
          padding: 8px 20px; border-radius: 4px; text-decoration: none;
          font-size: 14px; margin-top: 10px; }}
  .footer {{ text-align: center; font-size: 12px; color: #999; padding: 20px; }}
</style>
</head>
<body>
<div class="container">
  <div class="header">
    <h1>🔍 job-scout — 新着求人 {len(jobs)} 件</h1>
    <p>収集日時: {date_str}</p>
  </div>
  {cards}
  <div class="footer">このメールは job-scout によって自動送信されました。</div>
</div>
</body>
</html>"""

    def _job_card_html(self, index: int, job: Job) -> str:
        company_html = f'<p class="meta">🏢 {self._esc(job.company)}</p>' if job.company else ""
        location_html = f'<p class="meta">📍 {self._esc(job.location)}</p>' if job.location else ""

        kw_badges = "".join(
            f'<span class="kw-badge">{self._esc(k)}</span>'
            for k in job.matched_keywords[:8]
        )
        keywords_html = f'<div class="keywords">{kw_badges}</div>' if kw_badges else ""

        summary_html = (
            f'<div class="summary">{self._esc(job.summary[:300])}</div>'
            if job.summary else ""
        )
        reason_html = (
            f'<p class="match-reason">💡 {self._esc(job.match_reason[:200])}</p>'
            if job.match_reason else ""
        )

        return f"""
<div class="card">
  <p class="meta" style="color:#999;font-size:12px">#{index} · {self._esc(job.source_name)}</p>
  <p class="card-title">{self._esc(job.title)}</p>
  {company_html}
  {location_html}
  {keywords_html}
  {summary_html}
  {reason_html}
  <a class="btn" href="{self._esc(job.url)}" target="_blank">求人を見る →</a>
</div>"""

    @staticmethod
    def _esc(text: str) -> str:
        """HTMLエスケープ"""
        return (
            text
            .replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
            .replace('"', "&quot;")
        )
