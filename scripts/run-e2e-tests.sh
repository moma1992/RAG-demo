#!/bin/bash
#
# E2E Test Execution Script for Streamlit RAG App
# Usage: ./scripts/run-e2e-tests.sh [options]
#

set -e

# デフォルト設定
BROWSER="chromium"
HEADLESS="true"
SLOW_MO="0"
TIMEOUT="30000"
WORKERS="1"
VIDEO="retain-on-failure"
SCREENSHOT="only-on-failure"
TRACE="retain-on-failure"
OUTPUT_DIR="test-results"
BASE_URL="http://localhost:8501"
VERBOSE="false"
DEBUG="false"

# カラー出力
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# ヘルプ表示
show_help() {
    cat << EOF
E2E Test Runner for Streamlit RAG App

Usage: $0 [OPTIONS] [TEST_PATTERN]

OPTIONS:
    -b, --browser BROWSER       Browser to use (chromium, firefox, webkit) [default: chromium]
    -h, --headless BOOL         Run in headless mode (true/false) [default: true]
    -s, --slow-mo MS            Slow motion delay in milliseconds [default: 0]
    -t, --timeout MS            Test timeout in milliseconds [default: 30000]
    -w, --workers NUM           Number of parallel workers [default: 1]
    -v, --verbose               Enable verbose output
    -d, --debug                 Enable debug mode
    --video MODE                Video recording mode (on, off, retain-on-failure) [default: retain-on-failure]
    --screenshot MODE           Screenshot mode (on, off, only-on-failure) [default: only-on-failure]
    --trace MODE                Trace mode (on, off, retain-on-failure) [default: retain-on-failure]
    --output DIR                Output directory [default: test-results]
    --url URL                   Base URL for testing [default: http://localhost:8501]
    --setup-only                Only setup environment, don't run tests
    --cleanup                   Cleanup test environment after run
    --help                      Show this help message

TEST_PATTERN:
    Optional pytest pattern to run specific tests
    Examples:
        test_pdf_upload.py                  # Run PDF upload tests
        test_chat_interface.py::TestChatInterface::test_basic_message_sending
        tests/e2e/test_*.py                 # Run all E2E tests

EXAMPLES:
    # Run all tests in headless mode
    $0

    # Run tests with visual browser for debugging
    $0 --headless false --slow-mo 1000 --debug

    # Run only PDF upload tests
    $0 test_pdf_upload.py

    # Run tests in parallel with multiple browsers
    $0 --workers 3 --browser chromium

    # Run with video recording for all tests
    $0 --video on --screenshot on

EOF
}

# 引数解析
while [[ $# -gt 0 ]]; do
    case $1 in
        -b|--browser)
            BROWSER="$2"
            shift 2
            ;;
        -h|--headless)
            HEADLESS="$2"
            shift 2
            ;;
        -s|--slow-mo)
            SLOW_MO="$2"
            shift 2
            ;;
        -t|--timeout)
            TIMEOUT="$2"
            shift 2
            ;;
        -w|--workers)
            WORKERS="$2"
            shift 2
            ;;
        -v|--verbose)
            VERBOSE="true"
            shift
            ;;
        -d|--debug)
            DEBUG="true"
            HEADLESS="false"
            SLOW_MO="1000"
            VERBOSE="true"
            shift
            ;;
        --video)
            VIDEO="$2"
            shift 2
            ;;
        --screenshot)
            SCREENSHOT="$2"
            shift 2
            ;;
        --trace)
            TRACE="$2"
            shift 2
            ;;
        --output)
            OUTPUT_DIR="$2"
            shift 2
            ;;
        --url)
            BASE_URL="$2"
            shift 2
            ;;
        --setup-only)
            SETUP_ONLY="true"
            shift
            ;;
        --cleanup)
            CLEANUP="true"
            shift
            ;;
        --help)
            show_help
            exit 0
            ;;
        -*)
            echo "Unknown option $1"
            show_help
            exit 1
            ;;
        *)
            TEST_PATTERN="$1"
            shift
            ;;
    esac
done

# ログ関数
log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

log_debug() {
    if [[ "$DEBUG" == "true" ]]; then
        echo -e "${BLUE}[DEBUG]${NC} $1"
    fi
}

# 環境確認
check_environment() {
    log_info "Checking environment..."
    
    # Python仮想環境の確認
    if [[ -z "$VIRTUAL_ENV" ]]; then
        if [[ -d "venv" ]]; then
            log_info "Activating virtual environment..."
            source venv/bin/activate
        else
            log_error "No virtual environment found. Please create one with: python -m venv venv"
            exit 1
        fi
    fi
    
    # 必要なパッケージの確認
    if ! python -c "import playwright" 2>/dev/null; then
        log_error "Playwright not installed. Run: pip install -r requirements-test.txt"
        exit 1
    fi
    
    # Playwright browserの確認
    if ! playwright list | grep -q "$BROWSER"; then
        log_warn "Browser $BROWSER not installed. Installing..."
        playwright install "$BROWSER"
    fi
}

# 環境変数設定
setup_environment() {
    log_info "Setting up environment variables..."
    
    export E2E_BASE_URL="$BASE_URL"
    export E2E_HEADLESS="$HEADLESS"
    export E2E_SLOW_MO="$SLOW_MO"
    export E2E_TIMEOUT="$TIMEOUT"
    export E2E_DEBUG="$DEBUG"
    
    # テスト用の環境変数
    export OPENAI_API_KEY="${OPENAI_API_KEY:-sk-test-key-$(date +%s)}"
    export ANTHROPIC_API_KEY="${ANTHROPIC_API_KEY:-test-claude-key-$(date +%s)}"
    export SUPABASE_URL="${SUPABASE_URL:-https://test.supabase.co}"
    export SUPABASE_ANON_KEY="${SUPABASE_ANON_KEY:-test-anon-key}"
    
    log_debug "Environment variables set:"
    log_debug "  E2E_BASE_URL=$E2E_BASE_URL"
    log_debug "  E2E_HEADLESS=$E2E_HEADLESS"
    log_debug "  E2E_SLOW_MO=$E2E_SLOW_MO"
    log_debug "  E2E_TIMEOUT=$E2E_TIMEOUT"
}

# テストフィクスチャ準備
prepare_fixtures() {
    log_info "Preparing test fixtures..."
    
    # テスト用PDFファイルを作成
    if [[ -f "tests/e2e/utils/pdf_generator.py" ]]; then
        python tests/e2e/utils/pdf_generator.py
        log_info "Test PDF fixtures created"
    else
        log_warn "PDF generator not found, tests may fail without fixtures"
    fi
    
    # 出力ディレクトリを作成
    mkdir -p "$OUTPUT_DIR"/{screenshots,videos,traces,reports}
}

# Streamlitアプリの起動確認
check_streamlit_app() {
    log_info "Checking if Streamlit app is running..."
    
    if curl -s "$BASE_URL" > /dev/null 2>&1; then
        log_info "Streamlit app is already running at $BASE_URL"
        return 0
    else
        log_warn "Streamlit app is not running at $BASE_URL"
        log_warn "Please start the app manually: streamlit run streamlit_app.py"
        return 1
    fi
}

# テスト実行
run_tests() {
    log_info "Running E2E tests..."
    
    # pytest引数を構築
    local pytest_args=(
        "tests/e2e/"
        "--browser=$BROWSER"
        "--headed=$([ "$HEADLESS" = "false" ] && echo "true" || echo "false")"
        "--video=$VIDEO"
        "--screenshot=$SCREENSHOT"
        "--tracing=$TRACE"
        "--output=$OUTPUT_DIR"
        "--junit-xml=$OUTPUT_DIR/junit-results.xml"
        "--html=$OUTPUT_DIR/report.html"
        "--self-contained-html"
    )
    
    # テストパターンが指定されている場合
    if [[ -n "$TEST_PATTERN" ]]; then
        pytest_args[0]="tests/e2e/$TEST_PATTERN"
    fi
    
    # 並行実行
    if [[ "$WORKERS" -gt 1 ]]; then
        pytest_args+=("-n" "$WORKERS")
    fi
    
    # 詳細出力
    if [[ "$VERBOSE" == "true" ]]; then
        pytest_args+=("-v" "-s")
    fi
    
    log_debug "Running: pytest ${pytest_args[*]}"
    
    # テスト実行
    if pytest "${pytest_args[@]}"; then
        log_info "All tests passed! ✅"
        return 0
    else
        log_error "Some tests failed! ❌"
        return 1
    fi
}

# 結果レポート
generate_report() {
    log_info "Generating test report..."
    
    local report_file="$OUTPUT_DIR/test-summary.md"
    
    cat > "$report_file" << EOF
# E2E Test Results

**Date:** $(date)
**Browser:** $BROWSER
**Configuration:**
- Headless: $HEADLESS
- Slow Motion: ${SLOW_MO}ms
- Timeout: ${TIMEOUT}ms
- Workers: $WORKERS

## Test Artifacts

- [HTML Report]($OUTPUT_DIR/report.html)
- [JUnit XML]($OUTPUT_DIR/junit-results.xml)
- [Screenshots]($OUTPUT_DIR/screenshots/)
- [Videos]($OUTPUT_DIR/videos/)
- [Traces]($OUTPUT_DIR/traces/)

## Quick Links

- Videos: $(find "$OUTPUT_DIR/videos" -name "*.webm" 2>/dev/null | wc -l) files
- Screenshots: $(find "$OUTPUT_DIR/screenshots" -name "*.png" 2>/dev/null | wc -l) files
- Traces: $(find "$OUTPUT_DIR/traces" -name "*.zip" 2>/dev/null | wc -l) files

EOF

    log_info "Test summary saved to: $report_file"
}

# クリーンアップ
cleanup() {
    if [[ "$CLEANUP" == "true" ]]; then
        log_info "Cleaning up test environment..."
        
        # 古いテスト結果を削除
        if [[ -d "$OUTPUT_DIR" ]]; then
            find "$OUTPUT_DIR" -type f -mtime +7 -delete 2>/dev/null || true
        fi
        
        # 一時ファイルを削除
        find /tmp -name "tmp*test*.pdf" -mtime +1 -delete 2>/dev/null || true
        
        log_info "Cleanup completed"
    fi
}

# メイン実行
main() {
    log_info "Starting E2E test execution..."
    log_info "Browser: $BROWSER, Headless: $HEADLESS, Workers: $WORKERS"
    
    # 環境確認
    check_environment
    
    # 環境変数設定
    setup_environment
    
    # フィクスチャ準備
    prepare_fixtures
    
    # Streamlitアプリ確認
    if ! check_streamlit_app; then
        log_error "Cannot proceed without running Streamlit app"
        exit 1
    fi
    
    # セットアップのみの場合
    if [[ "$SETUP_ONLY" == "true" ]]; then
        log_info "Setup completed. Use --help for run options."
        exit 0
    fi
    
    # テスト実行
    local test_exit_code=0
    if ! run_tests; then
        test_exit_code=1
    fi
    
    # レポート生成
    generate_report
    
    # クリーンアップ
    cleanup
    
    if [[ $test_exit_code -eq 0 ]]; then
        log_info "E2E tests completed successfully! 🎉"
    else
        log_error "E2E tests completed with failures! 💥"
        log_info "Check the reports in $OUTPUT_DIR for details"
    fi
    
    exit $test_exit_code
}

# スクリプト実行
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main "$@"
fi