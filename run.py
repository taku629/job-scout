#!/usr/bin/env python3
"""
job-scout メインエントリーポイント

実行方法:
  python run.py                    # 通常実行
  python run.py --dry-run          # 通知を送らずに結果を確認
  python run.py --source remoteok  # 特定ソースのみ実行
  python run.py --no-summary       # 要約をスキップ
"""
import argparse
import os
import sys
from pathlib import Path

from dotenv import load_dotenv

# プロジェクトルートを sys.path に追加
sys.path.insert(0, str(Path(__file__).parent))
load_dotenv()

import yaml

from app.collectors.base import Job
from app.collectors.factory import create_collector
from app.filters.job_filter import JobFilter
from app.notifiers.factory import create_notifiers
from app.summarizers.claude_summarizer import ClaudeSummarizer
from app.utils.logger import logger, setup_logger
from app.utils.storage import JobStorage


def load_yaml(path: str) -> dict:
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f)


def run(
    dry_run: bool = False,
    source_filter: str | None = None,
    skip_summary: bool = False,
) -> None:
    logger.info("=" * 60)
    logger.info("job-scout 起動")
    if dry_run:
        logger.info("[DRY RUN] 通知は送信しません")
    logger.info("=" * 60)

    # --- 設定読み込み ---
    config = load_yaml("config/config.yaml")
    sources_cfg = load_yaml("config/sources.yaml")
    sources = sources_cfg.get("sources", [])
    filter_config = config.get("filters", {})

    # --- ストレージ初期化 ---
    storage = JobStorage()
    logger.info(f"送信済みID数: {storage.seen_count}")

    # --- 収集 ---
    all_jobs: list[Job] = []
    enabled_sources = [
        s for s in sources
        if s.get("enabled", True)
        and (source_filter is None or source_filter.lower() in s.get("name", "").lower())
    ]
    logger.info(f"有効ソース数: {len(enabled_sources)}")

    for source in enabled_sources:
        collector = create_collector(source, config)
        if collector is None:
            continue
        jobs = collector.collect()
        all_jobs.extend(jobs)

    logger.info(f"総収集件数: {len(all_jobs)}")

    # --- 新着判定 ---
    new_jobs = [j for j in all_jobs if not storage.is_seen(j.id)]
    logger.info(f"新着件数: {len(new_jobs)}")

    if not new_jobs:
        logger.info("新着求人はありませんでした。終了します。")
        return

    # --- フィルタリング ---
    job_filter = JobFilter(filter_config)
    matched_jobs = job_filter.filter(new_jobs)

    if not matched_jobs:
        logger.info("条件に合致する求人はありませんでした。")
        # 新着IDは記録する（次回の重複チェックのため）
        storage.mark_seen_bulk([j.id for j in new_jobs])
        return

    # --- 要約生成 ---
    enable_summarizer = os.getenv("ENABLE_SUMMARIZER", "true").lower() == "true"
    if not skip_summary and enable_summarizer:
        summarizer_config = config.get("summarizer", {})
        summarizer = ClaudeSummarizer(summarizer_config)
        matched_jobs = summarizer.summarize_bulk(matched_jobs, filter_config)
        logger.info("要約生成完了")
    else:
        logger.info("要約をスキップ")

    # --- 通知 ---
    enable_notifications = os.getenv("ENABLE_NOTIFICATIONS", "true").lower() == "true"
    if not dry_run and enable_notifications:
        notifiers = create_notifiers(config)
        for notifier in notifiers:
            notifier_name = type(notifier).__name__
            try:
                ok = notifier.notify(matched_jobs)
                if ok:
                    logger.info(f"{notifier_name}: 通知成功")
                else:
                    logger.warning(f"{notifier_name}: 通知失敗")
            except Exception as e:
                logger.error(f"{notifier_name}: 通知エラー: {e}", exc_info=True)
    else:
        logger.info("通知をスキップ（dry-run または ENABLE_NOTIFICATIONS=false）")
        for i, job in enumerate(matched_jobs, 1):
            print(f"\n--- 求人 {i} ---")
            print(f"タイトル : {job.title}")
            print(f"会社     : {job.company}")
            print(f"勤務地   : {job.location}")
            print(f"スコア   : {job.score}")
            print(f"キーワード: {', '.join(job.matched_keywords)}")
            if job.summary:
                print(f"要約     : {job.summary}")
            print(f"URL      : {job.url}")

    # --- 送信済みとして記録 ---
    if not dry_run:
        all_new_ids = [j.id for j in new_jobs]
        storage.mark_seen_bulk(all_new_ids)
        storage.save_jobs([j.to_dict() for j in matched_jobs])
        logger.info(f"{len(all_new_ids)} 件のIDを記録しました")

    logger.info("=" * 60)
    logger.info(f"完了: {len(matched_jobs)} 件の求人を処理しました")
    logger.info("=" * 60)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="job-scout: 求人・インターン監視エージェント"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="通知を送らずに結果を標準出力に表示する",
    )
    parser.add_argument(
        "--source",
        type=str,
        default=None,
        help="特定のソース名でフィルタリング（部分一致）",
    )
    parser.add_argument(
        "--no-summary",
        action="store_true",
        help="AI要約をスキップする",
    )
    args = parser.parse_args()

    try:
        run(
            dry_run=args.dry_run,
            source_filter=args.source,
            skip_summary=args.no_summary,
        )
    except KeyboardInterrupt:
        logger.info("中断されました")
        sys.exit(0)
    except Exception as e:
        logger.error(f"予期しないエラー: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
