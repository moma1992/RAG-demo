# E2E Testing with Playwright

このドキュメントでは、StreamlitベースのRAGアプリケーション用のE2Eテストの実行方法について説明します。

## 概要

Playwrightを使用したE2Eテストスイートを実装しており、以下の機能をカバーしています：

- **PDFアップロード機能**: ファイルアップロード、処理、検証
- **チャットインターフェース**: 質問応答、引用表示、会話履歴
- **文書管理**: 文書一覧、統計情報、削除機能
- **統合ワークフロー**: 完全なユーザージャーニー

## セットアップ

### 1. 環境構築

```bash
# E2E環境の自動セットアップ
./scripts/setup-e2e-environment.sh
```

### 2. 手動セットアップ（必要に応じて）

```bash
# 仮想環境の作成・有効化
python -m venv venv
source venv/bin/activate

# 依存関係のインストール
pip install -r requirements.txt
pip install -r requirements-test.txt

# Playwrightブラウザのインストール
playwright install chromium firefox webkit
```

### 3. 環境変数の設定

`.env`ファイルを作成し、必要な環境変数を設定：

```bash
# API Keys
OPENAI_API_KEY=your_openai_api_key
ANTHROPIC_API_KEY=your_claude_api_key
SUPABASE_URL=your_supabase_url
SUPABASE_ANON_KEY=your_supabase_anon_key

# E2E Test Configuration
E2E_BASE_URL=http://localhost:8501
E2E_HEADLESS=true
E2E_SLOW_MO=0
E2E_TIMEOUT=30000
```

## テスト実行

### 基本的な実行方法

```bash
# Streamlitアプリを起動
streamlit run streamlit_app.py

# 別のターミナルでE2Eテストを実行
./scripts/run-e2e-tests.sh
```

### 詳細なオプション

```bash
# ヘルプを表示
./scripts/run-e2e-tests.sh --help

# デバッグモード（ブラウザ表示、スローモーション）
./scripts/run-e2e-tests.sh --debug

# 特定のテストファイルのみ実行
./scripts/run-e2e-tests.sh test_pdf_upload.py

# 特定のテストケースのみ実行
./scripts/run-e2e-tests.sh test_chat_interface.py::TestChatInterface::test_basic_message_sending

# 異なるブラウザで実行
./scripts/run-e2e-tests.sh --browser firefox

# 並行実行
./scripts/run-e2e-tests.sh --workers 3

# ビデオ録画を有効化
./scripts/run-e2e-tests.sh --video on --screenshot on
```

### pytest直接実行

```bash
# 基本実行
pytest tests/e2e/

# 特定のマーカーでフィルタ
pytest tests/e2e/ -m "smoke"
pytest tests/e2e/ -m "pdf or chat"

# 詳細出力
pytest tests/e2e/ -v -s

# 並行実行
pytest tests/e2e/ -n auto
```

## テスト構成

### ディレクトリ構造

```
tests/e2e/
├── conftest.py                 # 共通フィクスチャ
├── pages/                      # Page Object Pattern
│   ├── base_page.py           # 基底ページクラス
│   ├── pdf_upload_page.py     # PDFアップロードページ
│   ├── chat_page.py           # チャットページ
│   └── document_management_page.py  # 文書管理ページ
├── utils/                      # ユーティリティ
│   └── pdf_generator.py       # テスト用PDFファイル生成
├── fixtures/                   # テストフィクスチャ
│   ├── sample.pdf             # 小さなサンプルPDF
│   └── large_sample.pdf       # 大きなサンプルPDF
├── test_pdf_upload.py         # PDFアップロードテスト
├── test_chat_interface.py     # チャットインターフェーステスト
├── test_document_management.py # 文書管理テスト
└── test_integration_workflow.py # 統合ワークフローテスト
```

### テストカテゴリ

#### 1. PDFアップロードテスト (`test_pdf_upload.py`)

- ✅ 単一PDFファイルのアップロード
- ✅ 複数PDFファイルの同時アップロード
- ✅ 大きなファイルの処理
- ✅ 処理オプション（チャンクサイズ、オーバーラップ率）
- ✅ 無効ファイルのエラーハンドリング
- ✅ 処理進捗の追跡
- ✅ チャットページへの遷移

#### 2. チャットインターフェーステスト (`test_chat_interface.py`)

- ✅ 基本的なメッセージ送信
- ✅ 連続した会話フロー
- ✅ アップロード済み文書との質疑応答
- ✅ 引用機能の詳細テスト
- ✅ 異なるタイプの質問処理
- ✅ 応答時間のパフォーマンステスト
- ✅ エラーハンドリング
- ✅ チャット履歴の永続化

#### 3. 文書管理テスト (`test_document_management.py`)

- ✅ 文書一覧の表示
- ✅ 統計情報の表示と更新
- ✅ 文書削除機能
- ✅ 処理状態の追跡
- ✅ 検索機能（実装依存）
- ✅ ソート・フィルタリング機能（実装依存）
- ✅ リスト更新機能

#### 4. 統合ワークフローテスト (`test_integration_workflow.py`)

- ✅ 完全なユーザージャーニー
- ✅ エラー発生からの回復フロー
- ✅ パフォーマンス要件の検証
- ✅ 複数文書を使用したワークフロー

## Page Object Pattern

テストの保守性を向上させるため、Page Object Patternを採用しています。

### 基本的な使用方法

```python
from tests.e2e.pages.pdf_upload_page import PDFUploadPage

def test_pdf_upload(app_page: Page):
    pdf_page = PDFUploadPage(app_page)
    
    # ページに移動
    pdf_page.navigate_to_upload_page()
    
    # ファイルをアップロード
    pdf_page.upload_pdf_file("path/to/test.pdf")
    
    # 処理を開始
    pdf_page.start_processing()
    
    # 完了を待機
    pdf_page.wait_for_processing_complete()
    
    # 結果を検証
    pdf_page.verify_processing_success()
```

### 主要なPage Objectメソッド

#### BasePage
- `wait_for_app_load()` - アプリケーション読み込み待機
- `navigate_to_page(page_name)` - サイドバーでの画面遷移
- `wait_for_streamlit_refresh()` - Streamlit再実行待機
- `get_success_message()` - 成功メッセージ取得
- `get_error_message()` - エラーメッセージ取得

#### PDFUploadPage
- `upload_pdf_file(file_path)` - PDFファイルアップロード
- `set_chunk_size(size)` - チャンクサイズ設定
- `start_processing()` - 処理開始
- `wait_for_processing_complete()` - 処理完了待機
- `verify_processing_success()` - 処理成功検証

#### ChatPage
- `send_message(message)` - メッセージ送信
- `wait_for_ai_response()` - AI応答待機
- `get_latest_ai_message()` - 最新AI応答取得
- `expand_citations()` - 引用元展開
- `verify_citations_visible()` - 引用表示検証

## 設定とカスタマイズ

### playwright.config.py

主要な設定項目：

```python
# ブラウザ設定
BROWSER_CONFIG = {
    "headless": True,
    "slow_mo": 0,
    "args": ["--no-sandbox", "--disable-dev-shm-usage"]
}

# タイムアウト設定
STREAMLIT_CONFIG = {
    "app_load_timeout": 10000,
    "api_response_timeout": 15000,
    "file_upload_timeout": 30000,
    "chat_response_timeout": 20000,
}

# セレクタ設定
SELECTORS = {
    "app": "[data-testid='stApp']",
    "file_uploader": "[data-testid='stFileUploader']",
    "button": "[data-testid='stButton']",
    "chat_input": "[data-testid='stChatInput']",
    "chat_message": "[data-testid='stChatMessage']",
}
```

### pytest.ini

pytest設定：

```ini
[tool:pytest]
testpaths = tests
markers =
    e2e: End-to-end tests
    smoke: Smoke tests for quick validation
    pdf: PDF processing tests
    chat: Chat interface tests
    performance: Performance tests

# Playwright設定
playwright_browser = chromium
playwright_headless = true
playwright_video = retain-on-failure
```

## CI/CD統合

### GitHub Actions

`.github/workflows/e2e-tests.yml`で自動テストを実行：

```yaml
- name: Run E2E tests
  run: |
    pytest tests/e2e/ \
      --browser=chromium \
      --headed=false \
      --video=retain-on-failure \
      --screenshot=only-on-failure
```

### 並行実行

複数ブラウザでの並行テスト：

```yaml
strategy:
  matrix:
    browser: [chromium, firefox, webkit]
```

## トラブルシューティング

### よくある問題と解決方法

#### 1. Streamlitアプリが起動しない

```bash
# ポートを確認
lsof -i :8501

# 異なるポートで起動
streamlit run streamlit_app.py --server.port 8502

# テストのベースURLを更新
export E2E_BASE_URL=http://localhost:8502
```

#### 2. ブラウザのインストールエラー

```bash
# ブラウザを再インストール
playwright install chromium --force

# システム依存関係をインストール
playwright install-deps
```

#### 3. テストの失敗

```bash
# デバッグモードで実行
./scripts/run-e2e-tests.sh --debug

# 詳細ログを有効化
pytest tests/e2e/ -v -s --log-cli-level=DEBUG

# スクリーンショットとビデオを確認
ls test-results/screenshots/
ls test-results/videos/
```

#### 4. タイムアウトエラー

```bash
# タイムアウトを延長
./scripts/run-e2e-tests.sh --timeout 60000

# 個別テストのタイムアウト調整
pytest tests/e2e/ --timeout=300
```

### ログとデバッグ

#### テスト結果の確認

```bash
# HTMLレポートを開く
open test-results/report.html

# JUnitレポートを確認
cat test-results/junit-results.xml

# ログファイルを確認
cat test-results/pytest.log
```

#### ビデオとスクリーンショット

失敗したテストの詳細は以下で確認できます：

- `test-results/videos/` - テスト実行のビデオ
- `test-results/screenshots/` - 失敗時のスクリーンショット
- `test-results/traces/` - 詳細なトレース情報

## パフォーマンス監視

### 応答時間の測定

```python
def test_response_time_performance(self, app_page: Page):
    chat_page = ChatPage(app_page)
    
    response_time = chat_page.measure_response_time("質問")
    assert response_time < 15.0, "Response should be under 15 seconds"
```

### ベンチマーク

```bash
# パフォーマンステストのみ実行
pytest tests/e2e/ -m performance

# ベンチマーク結果の保存
pytest tests/e2e/ --benchmark-only --benchmark-json=benchmark.json
```

## テストデータ管理

### テスト用PDFの生成

```python
from tests.e2e.utils.pdf_generator import create_simple_test_pdf

# カスタムコンテンツでPDF作成
pdf_path = create_simple_test_pdf(
    content="テスト用コンテンツ\n新入社員向け資料",
    pages=2
)
```

### フィクスチャ管理

```bash
# テストフィクスチャを再生成
python tests/e2e/utils/pdf_generator.py

# 特定のフィクスチャを確認
ls -la tests/e2e/fixtures/
```

## 拡張とカスタマイズ

### 新しいテストの追加

1. **Page Objectの作成**: `tests/e2e/pages/`にページクラスを追加
2. **テストケースの実装**: `tests/e2e/test_*.py`にテストを追加
3. **マーカーの設定**: `pytest.ini`に新しいマーカーを追加

### カスタムフィクスチャ

```python
# conftest.pyに追加
@pytest.fixture
def custom_test_data():
    # テストデータの準備
    yield test_data
    # クリーンアップ
```

### 新しいブラウザのサポート

```python
# playwright.config.pyに追加
SUPPORTED_BROWSERS = ["chromium", "firefox", "webkit", "edge"]
```

このE2Eテストスイートにより、StreamlitアプリケーションのUIからAPIレスポンスまで、エンドツーエンドでの動作を確実に検証できます。