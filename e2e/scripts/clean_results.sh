#!/bin/bash

# E2Eテスト結果クリーンアップスクリプト
# Usage: ./e2e/scripts/clean_results.sh [options]

set -e

# スクリプトのディレクトリを取得
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
E2E_ROOT="$(dirname "$SCRIPT_DIR")"
RESULTS_DIR="$E2E_ROOT/results"

# ヘルプ表示
show_help() {
    cat << EOF
E2Eテスト結果クリーンアップスクリプト

Usage: $0 [options]

Options:
  --all           全ての結果ファイルを削除
  --reports       HTMLレポートのみ削除
  --videos        ビデオファイルのみ削除
  --screenshots   スクリーンショットのみ削除
  --traces        トレースファイルのみ削除
  --old=DAYS      指定日数より古いファイルを削除（デフォルト：7日）
  --dry-run       削除対象ファイルを表示のみ（実際の削除は行わない）
  --help          このヘルプを表示

Examples:
  $0                      # 7日より古いファイルを削除
  $0 --all               # 全ての結果ファイルを削除
  $0 --old=3             # 3日より古いファイルを削除
  $0 --reports --dry-run # 削除対象のレポートファイルを表示
EOF
}

# デフォルト設定
DELETE_ALL=false
DELETE_REPORTS=false
DELETE_VIDEOS=false
DELETE_SCREENSHOTS=false
DELETE_TRACES=false
OLD_DAYS=7
DRY_RUN=false

# 引数解析
while [[ $# -gt 0 ]]; do
    case $1 in
        --help|-h)
            show_help
            exit 0
            ;;
        --all)
            DELETE_ALL=true
            shift
            ;;
        --reports)
            DELETE_REPORTS=true
            shift
            ;;
        --videos)
            DELETE_VIDEOS=true
            shift
            ;;
        --screenshots)
            DELETE_SCREENSHOTS=true
            shift
            ;;
        --traces)
            DELETE_TRACES=true
            shift
            ;;
        --old=*)
            OLD_DAYS="${1#*=}"
            shift
            ;;
        --dry-run)
            DRY_RUN=true
            shift
            ;;
        *)
            echo "Unknown option: $1"
            echo "Use --help for usage information."
            exit 1
            ;;
    esac
done

# 結果ディレクトリの存在確認
if [ ! -d "$RESULTS_DIR" ]; then
    echo "📂 結果ディレクトリが見つかりません: $RESULTS_DIR"
    exit 0
fi

echo "🧹 E2Eテスト結果クリーンアップ開始"
echo "対象ディレクトリ: $RESULTS_DIR"

# ドライランの場合は警告表示
if [ "$DRY_RUN" = true ]; then
    echo "⚠️  ドライランモード: ファイルは実際には削除されません"
fi

echo ""

# ファイル削除関数
delete_files() {
    local pattern=$1
    local description=$2
    
    echo "🔍 $description を検索中..."
    
    if [ "$DELETE_ALL" = true ]; then
        # 全て削除
        local files=$(find "$RESULTS_DIR" -name "$pattern" -type f 2>/dev/null || true)
    else
        # 指定日数より古いファイルを削除
        local files=$(find "$RESULTS_DIR" -name "$pattern" -type f -mtime +$OLD_DAYS 2>/dev/null || true)
    fi
    
    if [ -z "$files" ]; then
        echo "  📭 削除対象の$description はありません"
        return
    fi
    
    local count=$(echo "$files" | wc -l)
    echo "  📋 $count 個の$description が見つかりました"
    
    if [ "$DRY_RUN" = true ]; then
        echo "$files" | while read -r file; do
            echo "    [DRY-RUN] $file"
        done
    else
        echo "$files" | while read -r file; do
            rm -f "$file"
            echo "    🗑️  削除: $(basename "$file")"
        done
    fi
    
    echo ""
}

# ファイル削除実行
if [ "$DELETE_ALL" = true ] || [ "$DELETE_REPORTS" = true ]; then
    delete_files "report-*.html" "HTMLレポート"
fi

if [ "$DELETE_ALL" = true ] || [ "$DELETE_VIDEOS" = true ]; then
    delete_files "*.webm" "ビデオファイル"
    delete_files "*.mp4" "ビデオファイル"
fi

if [ "$DELETE_ALL" = true ] || [ "$DELETE_SCREENSHOTS" = true ]; then
    delete_files "*.png" "スクリーンショット"
    delete_files "*.jpg" "スクリーンショット"
fi

if [ "$DELETE_ALL" = true ] || [ "$DELETE_TRACES" = true ]; then
    delete_files "*.zip" "トレースファイル"
    delete_files "trace-*.json" "トレースファイル"
fi

# デフォルト動作（古いファイルの削除）
if [ "$DELETE_ALL" = false ] && [ "$DELETE_REPORTS" = false ] && [ "$DELETE_VIDEOS" = false ] && [ "$DELETE_SCREENSHOTS" = false ] && [ "$DELETE_TRACES" = false ]; then
    echo "📅 ${OLD_DAYS}日より古いファイルを削除中..."
    echo ""
    
    delete_files "report-*.html" "HTMLレポート"
    delete_files "*.webm" "ビデオファイル"
    delete_files "*.mp4" "ビデオファイル"
    delete_files "*.png" "スクリーンショット"
    delete_files "*.jpg" "スクリーンショット"
    delete_files "*.zip" "トレースファイル"
    delete_files "trace-*.json" "トレースファイル"
fi

# 空ディレクトリの削除
if [ "$DELETE_ALL" = true ] && [ "$DRY_RUN" = false ]; then
    echo "📁 空ディレクトリの削除中..."
    find "$RESULTS_DIR" -type d -empty -delete 2>/dev/null || true
fi

# 結果表示
if [ "$DRY_RUN" = true ]; then
    echo "✅ ドライラン完了"
    echo "実際に削除する場合は --dry-run オプションを外してください"
else
    echo "✅ クリーンアップ完了"
    
    # 残りファイル数の表示
    if [ -d "$RESULTS_DIR" ]; then
        local remaining=$(find "$RESULTS_DIR" -type f | wc -l)
        echo "📊 残りファイル数: $remaining"
    fi
fi