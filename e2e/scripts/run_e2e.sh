#!/bin/bash

# E2Eテスト統合実行スクリプト
# Usage: ./e2e/scripts/run_e2e.sh [mode] [browser]
# Modes: full, quick, basic, single
# Browsers: chromium, firefox, webkit

set -e

# スクリプトのディレクトリを取得
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
E2E_ROOT="$(dirname "$SCRIPT_DIR")"
PROJECT_ROOT="$(dirname "$E2E_ROOT")"

# デフォルト設定
MODE="${1:-quick}"
BROWSER="${2:-chromium}"
BASE_URL="http://localhost:8501"
TEST_RESULTS_DIR="$E2E_ROOT/results"

# ヘルプ表示
show_help() {
    cat << EOF
E2Eテスト統合実行スクリプト

使用方法:
    ./e2e/scripts/run_e2e.sh [mode] [browser]

モード:
    full    - 全テストを実行（スクリーンショット・動画録画あり）
    quick   - 全テストを高速実行（録画なし）【デフォルト】
    basic   - 基本的なテストのみ実行（録画なし）
    single  - 単一テストを指定して実行
    help    - このヘルプを表示

ブラウザ:
    chromium - Chromiumブラウザ【デフォルト】
    firefox  - Firefoxブラウザ
    webkit   - WebKitブラウザ

例:
    ./e2e/scripts/run_e2e.sh                    # クイックモード、Chromium
    ./e2e/scripts/run_e2e.sh full chromium      # フルモード、Chromium
    ./e2e/scripts/run_e2e.sh basic firefox      # 基本モード、Firefox
    ./e2e/scripts/run_e2e.sh single             # 単一テスト選択モード

環境変数:
    E2E_BASE_URL       - ベースURL（デフォルト: http://localhost:8501）
    E2E_RECORD_VIDEO   - 動画録画（true/false、デフォルト: false）
    E2E_TIMEOUT        - テストタイムアウト（秒、デフォルト: 60）

EOF
}

# ヘルプ表示チェック
if [[ "$MODE" == "help" || "$MODE" == "-h" || "$MODE" == "--help" ]]; then
    show_help
    exit 0
fi

# カラー出力設定
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo_color() {
    local color=$1
    shift
    echo -e "${color}$@${NC}"
}

# 設定表示
echo_color $BLUE "🚀 E2Eテスト実行開始"
echo_color $YELLOW "モード: $MODE"
echo_color $YELLOW "ブラウザ: $BROWSER"
echo_color $YELLOW "ベースURL: $BASE_URL"
echo ""

# プロジェクトディレクトリに移動
cd "$PROJECT_ROOT"

# 仮想環境をアクティベート
if [[ -f "venv/bin/activate" ]]; then
    source venv/bin/activate
    echo_color $GREEN "✅ 仮想環境をアクティベート"
else
    echo_color $RED "❌ 仮想環境が見つかりません"
    exit 1
fi

# テストディレクトリ作成
mkdir -p "$TEST_RESULTS_DIR"

# Streamlitアプリ起動チェック
echo_color $BLUE "🌐 Streamlitアプリ起動チェック..."
if ! curl -s "$BASE_URL/healthz" > /dev/null 2>&1; then
    echo_color $YELLOW "⚠️  Streamlitアプリが起動していません"
    echo "別ターミナルで以下のコマンドを実行してください："
    echo "   streamlit run streamlit_app.py"
    echo ""
    read -p "起動後、Enterキーを押してください..." -r
fi

# 共通のpytestオプション
COMMON_PYTEST_ARGS=(
    --browser="$BROWSER"
    --output="$TEST_RESULTS_DIR"
    --self-contained-html
    --tb=short
    -v
)

# 環境変数設定
export E2E_BASE_URL="$BASE_URL"
export E2E_TIMEOUT="${E2E_TIMEOUT:-60}"

# モード別実行
case "$MODE" in
    "full")
        echo_color $BLUE "🧪 フルE2Eテスト実行中（全機能・録画あり）..."
        export E2E_RECORD_VIDEO="true"
        
        pytest tests/e2e/ \
            "${COMMON_PYTEST_ARGS[@]}" \
            --html="$TEST_RESULTS_DIR/report-full-$BROWSER.html" \
            --screenshot=on \
            --video=on \
            --tracing=on
        
        echo_color $GREEN "📊 レポート: $TEST_RESULTS_DIR/report-full-$BROWSER.html"
        echo_color $GREEN "📹 動画: $TEST_RESULTS_DIR/videos/"
        echo_color $GREEN "📸 スクリーンショット: $TEST_RESULTS_DIR/screenshots/"
        ;;
        
    "quick")
        echo_color $BLUE "🧪 クイックE2Eテスト実行中（全機能・録画なし）..."
        export E2E_RECORD_VIDEO="false"
        
        pytest tests/e2e/ \
            "${COMMON_PYTEST_ARGS[@]}" \
            --html="$TEST_RESULTS_DIR/report-quick-$BROWSER.html" \
            --screenshot=off \
            --video=off \
            --tracing=off \
            --maxfail=5
        
        echo_color $GREEN "📊 レポート: $TEST_RESULTS_DIR/report-quick-$BROWSER.html"
        ;;
        
    "basic")
        echo_color $BLUE "🧪 基本E2Eテスト実行中（主要機能のみ）..."
        export E2E_RECORD_VIDEO="false"
        
        pytest \
            tests/e2e/test_chat_interface.py::TestChatInterface::test_chat_page_navigation \
            tests/e2e/test_chat_interface.py::TestChatInterface::test_basic_message_sending \
            tests/e2e/test_chat_interface.py::TestChatInterface::test_response_time_performance \
            tests/e2e/test_chat_interface.py::TestChatInterface::test_error_handling_in_chat \
            tests/e2e/test_chat_interface.py::TestChatInterface::test_empty_message_handling \
            tests/e2e/test_document_management.py::TestDocumentManagement::test_empty_document_list_display \
            tests/e2e/test_pdf_upload.py::TestPDFUpload::test_upload_page_navigation \
            "${COMMON_PYTEST_ARGS[@]}" \
            --html="$TEST_RESULTS_DIR/report-basic-$BROWSER.html" \
            --screenshot=off \
            --video=off \
            --tracing=off
        
        echo_color $GREEN "📊 レポート: $TEST_RESULTS_DIR/report-basic-$BROWSER.html"
        
        echo ""
        echo_color $GREEN "🔍 実行されたテスト："
        echo "  - ページナビゲーション"
        echo "  - 基本メッセージ送信"
        echo "  - パフォーマンステスト"
        echo "  - エラーハンドリング"
        echo "  - 空メッセージ処理"
        echo "  - 文書管理UI"
        echo "  - PDFアップロードページ"
        ;;
        
    "single")
        echo_color $BLUE "🧪 単一テスト選択モード..."
        export E2E_RECORD_VIDEO="false"
        
        # 利用可能なテストを表示
        echo_color $YELLOW "利用可能なテスト："
        echo "1. test_chat_page_navigation - チャットページナビゲーション"
        echo "2. test_basic_message_sending - 基本メッセージ送信"
        echo "3. test_response_time_performance - レスポンス時間パフォーマンス"  
        echo "4. test_error_handling_in_chat - エラーハンドリング"
        echo "5. test_empty_message_handling - 空メッセージ処理"
        echo "6. test_upload_page_navigation - PDFアップロードページ"
        echo "7. test_empty_document_list_display - 空文書リスト表示"
        echo "8. all_chat - 全チャットテスト"
        echo "9. all_upload - 全アップロードテスト"
        echo "10. all_document - 全文書管理テスト"
        echo ""
        
        read -p "テスト番号を選択してください (1-10): " -r test_choice
        
        case "$test_choice" in
            "1")
                TEST_PATH="tests/e2e/test_chat_interface.py::TestChatInterface::test_chat_page_navigation"
                ;;
            "2")
                TEST_PATH="tests/e2e/test_chat_interface.py::TestChatInterface::test_basic_message_sending"
                ;;
            "3")
                TEST_PATH="tests/e2e/test_chat_interface.py::TestChatInterface::test_response_time_performance"
                ;;
            "4")
                TEST_PATH="tests/e2e/test_chat_interface.py::TestChatInterface::test_error_handling_in_chat"
                ;;
            "5")
                TEST_PATH="tests/e2e/test_chat_interface.py::TestChatInterface::test_empty_message_handling"
                ;;
            "6")
                TEST_PATH="tests/e2e/test_pdf_upload.py::TestPDFUpload::test_upload_page_navigation"
                ;;
            "7")
                TEST_PATH="tests/e2e/test_document_management.py::TestDocumentManagement::test_empty_document_list_display"
                ;;
            "8")
                TEST_PATH="tests/e2e/test_chat_interface.py"
                ;;
            "9")
                TEST_PATH="tests/e2e/test_pdf_upload.py"
                ;;
            "10")
                TEST_PATH="tests/e2e/test_document_management.py"
                ;;
            *)
                echo_color $RED "❌ 無効な選択です"
                exit 1
                ;;
        esac
        
        echo_color $BLUE "実行中: $TEST_PATH"
        
        pytest "$TEST_PATH" \
            "${COMMON_PYTEST_ARGS[@]}" \
            --html="$TEST_RESULTS_DIR/report-single-$BROWSER.html" \
            --screenshot=off \
            --video=off \
            --tracing=off
        
        echo_color $GREEN "📊 レポート: $TEST_RESULTS_DIR/report-single-$BROWSER.html"
        ;;
        
    *)
        echo_color $RED "❌ 無効なモード: $MODE"
        echo_color $YELLOW "利用可能なモード: full, quick, basic, single"
        echo_color $YELLOW "ヘルプ: ./e2e/scripts/run_e2e.sh help"
        exit 1
        ;;
esac

echo ""
echo_color $GREEN "✅ E2Eテスト完了"

# 結果サマリー表示
if [[ -f "$TEST_RESULTS_DIR/report-$MODE-$BROWSER.html" ]]; then
    echo_color $BLUE "📊 詳細レポート: $TEST_RESULTS_DIR/report-$MODE-$BROWSER.html"
fi

# クリーンアップオプション
echo ""
read -p "テスト結果をクリーンアップしますか？ (y/N): " -r cleanup_choice
if [[ "$cleanup_choice" =~ ^[Yy]$ ]]; then
    echo_color $YELLOW "🧹 古いテスト結果をクリーンアップ中..."
    find "$TEST_RESULTS_DIR" -type f -mtime +7 -delete 2>/dev/null || true
    echo_color $GREEN "✅ クリーンアップ完了"
fi

echo_color $GREEN "🎉 すべての処理が完了しました！"