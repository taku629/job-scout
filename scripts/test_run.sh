#!/usr/bin/env bash
# ============================================================
# job-scout ローカルテスト用スクリプト
# ============================================================
# 使い方:
#   chmod +x scripts/test_run.sh
#   ./scripts/test_run.sh              # dry-run（通知なし）
#   ./scripts/test_run.sh --notify     # 実際に通知を送る
#   ./scripts/test_run.sh --source rss # RSS ソースのみ
# ============================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$PROJECT_DIR"

NOTIFY=false
SOURCE=""
EXTRA_ARGS=""

# 引数解析
while [[ $# -gt 0 ]]; do
  case $1 in
    --notify)
      NOTIFY=true
      shift
      ;;
    --source)
      SOURCE="$2"
      shift 2
      ;;
    --no-summary)
      EXTRA_ARGS="$EXTRA_ARGS --no-summary"
      shift
      ;;
    *)
      echo "未知のオプション: $1"
      exit 1
      ;;
  esac
done

# 仮想環境チェック
if [ ! -d ".venv" ]; then
  echo "仮想環境が見つかりません。作成します..."
  python3 -m venv .venv
fi

source .venv/bin/activate

# 依存パッケージのインストール
pip install -q -r requirements.txt

# .env の確認
if [ ! -f ".env" ]; then
  echo ".env ファイルが見つかりません。.env.example をコピーして設定してください。"
  echo "  cp .env.example .env"
  exit 1
fi

# 実行
CMD="python run.py"

if [ "$NOTIFY" = false ]; then
  CMD="$CMD --dry-run"
  echo ">>> DRY RUN モード（通知なし）"
fi

if [ -n "$SOURCE" ]; then
  CMD="$CMD --source $SOURCE"
fi

CMD="$CMD $EXTRA_ARGS"

echo ">>> 実行: $CMD"
echo "---"
eval "$CMD"
