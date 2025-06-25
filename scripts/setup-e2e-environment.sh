#!/bin/bash
#
# E2E Test Environment Setup Script
# 

set -e

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

log_info "Setting up E2E test environment..."

# Python仮想環境の確認
if [[ ! -d "venv" ]]; then
    log_info "Creating Python virtual environment..."
    python3 -m venv venv
fi

log_info "Activating virtual environment..."
source venv/bin/activate

# 依存関係のインストール
log_info "Installing Python dependencies..."
pip install --upgrade pip

if [[ -f "requirements.txt" ]]; then
    pip install -r requirements.txt
else
    log_warn "requirements.txt not found"
fi

if [[ -f "requirements-test.txt" ]]; then
    pip install -r requirements-test.txt
else
    log_warn "requirements-test.txt not found, installing basic test dependencies..."
    pip install pytest pytest-playwright playwright pytest-html pytest-xdist
fi

# Playwrightブラウザのインストール
log_info "Installing Playwright browsers..."
playwright install chromium firefox webkit
playwright install-deps

# テストディレクトリの作成
log_info "Creating test directories..."
mkdir -p test-results/{screenshots,videos,traces,reports}
mkdir -p tests/e2e/fixtures

# テストフィクスチャの作成
log_info "Creating test fixtures..."
if [[ -f "tests/e2e/utils/pdf_generator.py" ]]; then
    python tests/e2e/utils/pdf_generator.py
    log_info "Test PDF fixtures created"
else
    log_warn "PDF generator not found, creating minimal fixtures..."
    mkdir -p tests/e2e/fixtures
fi

# 環境変数テンプレート作成
if [[ ! -f ".env.test" ]]; then
    log_info "Creating test environment template..."
    cat > .env.test << 'EOF'
# Test Environment Variables
# Copy to .env and fill in actual values

# API Keys (use test/mock values for E2E tests)
OPENAI_API_KEY=sk-test-key-for-e2e
ANTHROPIC_API_KEY=test-claude-key
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_ANON_KEY=your-anon-key

# E2E Test Configuration
E2E_BASE_URL=http://localhost:8501
E2E_HEADLESS=true
E2E_SLOW_MO=0
E2E_TIMEOUT=30000
E2E_DEBUG=false

# Browser Configuration
PLAYWRIGHT_BROWSER=chromium
PLAYWRIGHT_HEADLESS=true
PLAYWRIGHT_SLOW_MO=0
EOF
    log_info "Test environment template created: .env.test"
    log_warn "Please copy .env.test to .env and configure your actual API keys"
fi

# 権限設定
chmod +x scripts/*.sh 2>/dev/null || true

log_info "E2E test environment setup completed! ✅"
echo
echo "Next steps:"
echo "1. Configure your environment variables in .env file"
echo "2. Start your Streamlit app: streamlit run streamlit_app.py"
echo "3. Run E2E tests: ./scripts/run-e2e-tests.sh"
echo
echo "Available test commands:"
echo "  ./scripts/run-e2e-tests.sh --help                 # Show help"
echo "  ./scripts/run-e2e-tests.sh                        # Run all tests"
echo "  ./scripts/run-e2e-tests.sh --debug               # Debug mode"
echo "  ./scripts/run-e2e-tests.sh test_pdf_upload.py    # Run specific test"