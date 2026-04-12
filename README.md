# job-scout — 求人・インターン監視エージェント

条件に合う求人・インターン募集を定期収集して、AI要約付きで Discord / Telegram / Slack に通知するツールです。

## 特徴

- **RSS & HTML 収集**: RemoteOK・We Work Remotely・Python.org・Hacker News Hiring など公開フィードに対応
- **条件フィルタ**: キーワード / 勤務地 / 雇用形態 / 除外キーワードで絞り込み
- **新着判定**: 送信済みIDを JSON で管理し、重複通知を防止
- **日本語 AI 要約**: Claude API（Haiku）で求人を2〜4文に要約 + マッチ理由を添付
- **マルチ通知**: Discord（必須）/ Telegram / Slack に対応、拡張しやすい設計
- **GitHub Actions**: スケジュール実行 + 手動実行に対応
- **ローカル実行**: `--dry-run` で通知なしで動作確認可能

---

## セットアップ

### 1. リポジトリのクローン

```bash
git clone https://github.com/taku629/job-scout.git
cd job-scout
```

### 2. 仮想環境の作成と依存パッケージのインストール

```bash
python3 -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

### 3. 環境変数の設定

```bash
cp .env.example .env
```

`.env` を開いて以下を設定します:

| 変数名 | 必須 | 説明 |
|--------|------|------|
| `DISCORD_WEBHOOK_URL` | ◎ | Discord の Webhook URL |
| `ANTHROPIC_API_KEY` | △ | AI要約を使う場合 |
| `TELEGRAM_BOT_TOKEN` | - | Telegram 通知（オプション） |
| `TELEGRAM_CHAT_ID` | - | Telegram 通知（オプション） |
| `SLACK_WEBHOOK_URL` | - | Slack 通知（オプション） |

#### Discord Webhook の取得手順
1. Discord サーバー → チャンネル設定 → 連携サービス → ウェブフックを作成
2. Webhook URL をコピーして `DISCORD_WEBHOOK_URL` に設定

### 4. 監視条件の設定

`config/config.yaml` を編集:

```yaml
filters:
  keywords:
    - software engineer
    - backend
    - AI engineer
  locations:
    - Tokyo
    - Remote
  exclude_keywords:
    - senior
    - manager
```

---

## ローカルでのテスト手順

### 通知なしで動作確認（推奨）

```bash
python run.py --dry-run
```

### 特定ソースのみテスト

```bash
python run.py --dry-run --source "RemoteOK"
python run.py --dry-run --source "Python"
```

### 要約なしで高速テスト

```bash
python run.py --dry-run --no-summary
```

### テストスクリプトを使う

```bash
chmod +x scripts/test_run.sh
./scripts/test_run.sh              # dry-run
./scripts/test_run.sh --notify     # 実際に通知を送る
./scripts/test_run.sh --source rss
```

---

## GitHub Actions での定期実行

### Secrets の設定

GitHub リポジトリ → Settings → Secrets and variables → Actions → **New repository secret**

| Secret 名 | 値 |
|-----------|-----|
| `DISCORD_WEBHOOK_URL` | Discord の Webhook URL |
| `ANTHROPIC_API_KEY` | Anthropic API キー |
| `TELEGRAM_BOT_TOKEN` | Telegram Bot トークン（任意） |
| `TELEGRAM_CHAT_ID` | Telegram Chat ID（任意） |
| `SLACK_WEBHOOK_URL` | Slack Webhook URL（任意） |

### 実行スケジュール

デフォルトは毎日 **9:00 JST** に自動実行されます。
変更する場合は `.github/workflows/job_scout.yml` の cron 式を編集:

```yaml
schedule:
  - cron: "0 0 * * *"  # UTC 0:00 = JST 9:00
  # - cron: "0 0 * * 1-5"  # 平日のみ
  # - cron: "0 0,12 * * *"  # 1日2回
```

### 手動実行（workflow_dispatch）

GitHub Actions タブ → job-scout → **Run workflow** で任意のタイミングで実行できます。
`dry_run: true` を選択すると通知なしで確認できます。

### データのキャッシュ

`data/seen_ids.json` は GitHub Actions の **cache** を使って実行をまたいで保持されます。
キャッシュが消えると既読情報がリセットされ、全件が「新着」として通知されます。

---

## ディレクトリ構成

```
job-scout/
├── app/
│   ├── collectors/          # 収集器
│   │   ├── base.py          # Job モデル・基底クラス
│   │   ├── rss_collector.py # RSS/Atom フィード収集
│   │   ├── html_collector.py# HTML スクレイピング
│   │   └── factory.py       # コレクターファクトリー
│   ├── filters/
│   │   └── job_filter.py    # キーワード・条件フィルタ
│   ├── summarizers/
│   │   └── claude_summarizer.py  # Claude API 要約
│   ├── notifiers/
│   │   ├── base.py          # 基底クラス
│   │   ├── discord_notifier.py
│   │   ├── telegram_notifier.py
│   │   ├── slack_notifier.py
│   │   └── factory.py       # 通知器ファクトリー
│   └── utils/
│       ├── logger.py        # ロギング設定
│       └── storage.py       # JSON ストレージ
├── config/
│   ├── config.yaml          # 監視条件設定
│   └── sources.yaml         # 収集ソース一覧
├── data/                    # 実行データ（.gitignore 済み）
│   ├── seen_ids.json        # 送信済みID
│   ├── jobs_history.json    # 求人履歴
│   └── logs/                # ログファイル
├── scripts/
│   └── test_run.sh          # テスト実行スクリプト
├── .github/workflows/
│   └── job_scout.yml        # GitHub Actions
├── run.py                   # メインエントリーポイント
├── requirements.txt
├── .env.example
└── README.md
```

---

## 新しいソースの追加方法

### RSS フィード

`config/sources.yaml` に追記:

```yaml
- name: "My Feed"
  type: rss
  url: "https://example.com/jobs.rss"
  enabled: true
  tags: ["custom"]
```

### HTML スクレイピング

robots.txt を確認の上、CSS セレクタを設定:

```yaml
- name: "Custom Site"
  type: html
  url: "https://example.com/jobs"
  enabled: true
  parser:
    job_selector: ".job-card"
    title_selector: "h2.title"
    company_selector: ".company"
    location_selector: ".location"
    link_selector: "a.job-link"
    description_selector: ".excerpt"
```

---

## 法的・倫理的な注意事項

- このツールは **robots.txt を尊重** し、許可されていないページへのアクセスは行いません
- リクエスト間には待機時間（デフォルト 2 秒）を設けています
- 過剰なアクセスは行わないでください（`max_jobs_per_source` で上限を設定）
- スクレイピング対象サイトの利用規約を必ず確認してください
- 収集したデータは個人利用の範囲で使用してください

---

## 今後のマネタイズ案

### 1. SaaS 化（月額サブスクリプション）
- Web UI でキーワード・通知先を GUI から設定できるようにする
- ユーザーごとに条件を分離し、クラウドで定期実行（AWS Lambda / Cloudflare Workers）
- 無料プラン（1条件・1通知先）、Pro（複数条件・複数通知先）で段階的な課金
- 月額 $5〜$15 程度の設定で就活生・転職者向けにマーケティング

### 2. 求人レコメンド API の提供（B2B）
- 収集・フィルタ・要約のコアロジックを API として切り出す
- 採用サイト・就活アプリに OEM 提供
- 求人情報のリアルタイム検索・要約機能を API として月額課金

### 3. 求人情報の分析レポートサービス
- 収集した求人データからトレンド分析（注目キーワード、給与相場、採用増加企業）
- 週次・月次レポートを PDF / Slack で配信する有料サービス
- 就職支援機関・大学キャリアセンターへの B2B 販売

---

## トラブルシューティング

### 通知が来ない
1. `python run.py --dry-run` で求人が取得できているか確認
2. `.env` の `DISCORD_WEBHOOK_URL` が正しいか確認
3. `data/logs/job-scout.log` でエラーログを確認

### 求人が1件も取得できない
1. ネットワーク接続を確認
2. `--source` オプションで個別ソースをテスト
3. `LOG_LEVEL=DEBUG` に設定してデバッグログを確認

### 要約が生成されない
1. `ANTHROPIC_API_KEY` が正しいか確認
2. `ENABLE_SUMMARIZER=false` または `--no-summary` で要約をスキップして動作確認

### GitHub Actions で seen_ids が保持されない
- Actions cache は一定期間（7日間アクセスなし）で削除されます
- 重要なデータは Artifact または外部ストレージ（S3 等）での永続化を検討してください
