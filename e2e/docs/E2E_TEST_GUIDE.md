# E2Eテストガイド（ローカル実行専用）

E2EテストはCI/CDパイプラインから除外され、ローカル開発環境での手動実行専用になりました。

## 🎯 概要

- **目的**: StreamlitアプリケーションのUIと機能の統合テスト
- **実行環境**: ローカル開発環境のみ
- **対象ブラウザ**: Chromium、Firefox、WebKit
- **テストフレームワーク**: Playwright + pytest

## 🚀 クイックスタート

### 1. 環境セットアップ

```bash
# 1. 仮想環境作成・アクティベート
python -m venv venv
source venv/bin/activate  # Linux/Mac
# venv\Scripts\activate   # Windows

# 2. 依存関係インストール
pip install -r requirements.txt
pip install -r requirements-test.txt

# 3. Playwrightブラウザインストール
playwright install
```

### 2. アプリケーション起動

```bash
# Streamlitアプリを起動（別ターミナル）
streamlit run streamlit_app.py
```

### 3. テスト実行

```bash
# 基本実行（Chromiumでヘッドありモード）
./scripts/run_e2e_tests.sh

# 特定ブラウザで実行
./scripts/run_e2e_tests.sh firefox

# ヘッドレスモードで実行
./scripts/run_e2e_tests.sh chromium --headless

# 全ブラウザで実行
./scripts/run_e2e_tests.sh all
```

## 📖 詳細な使用方法

### 実行オプション

#### ブラウザ選択
```bash
./scripts/run_e2e_tests.sh chromium    # Chromium
./scripts/run_e2e_tests.sh firefox     # Firefox  
./scripts/run_e2e_tests.sh webkit      # WebKit
./scripts/run_e2e_tests.sh all         # 全ブラウザ
```

#### 表示モード
```bash
# ヘッドありモード（デフォルト、ブラウザウィンドウが表示される）
./scripts/run_e2e_tests.sh --headed

# ヘッドレスモード（ブラウザウィンドウなし、高速実行）
./scripts/run_e2e_tests.sh --headless
```

#### 録画・スクリーンショット設定
```bash
# ビデオ録画設定
./scripts/run_e2e_tests.sh --video=on                    # 常に録画
./scripts/run_e2e_tests.sh --video=off                   # 録画しない
./scripts/run_e2e_tests.sh --video=retain-on-failure     # 失敗時のみ（デフォルト）

# スクリーンショット設定
./scripts/run_e2e_tests.sh --screenshot=on               # 常に撮影
./scripts/run_e2e_tests.sh --screenshot=off              # 撮影しない
./scripts/run_e2e_tests.sh --screenshot=only-on-failure  # 失敗時のみ（デフォルト）
```

#### その他の設定
```bash
# 別ポートで起動したアプリをテスト
./scripts/run_e2e_tests.sh --base-url=http://localhost:8502

# タイムアウト時間変更（ミリ秒）
./scripts/run_e2e_tests.sh --timeout=60000
```

### 環境変数での設定

```bash
# 環境変数で設定（スクリプトオプションより優先度低）
export E2E_HEADLESS=true
export E2E_BASE_URL=http://localhost:8501
export E2E_TIMEOUT=30000

./scripts/run_e2e_tests.sh
```

## 📋 テスト内容

### テストスイート一覧

#### 1. PDF アップロードテスト
- **ファイル**: `tests/e2e/test_pdf_upload.py`
- **内容**: 
  - PDFファイルの選択とアップロード
  - 処理進捗の確認
  - エラーハンドリング

#### 2. チャットインターフェーステスト
- **ファイル**: `tests/e2e/test_chat_interface.py`
- **内容**:
  - 質問の入力と送信
  - AI回答の表示確認
  - 引用情報の表示
  - レスポンス時間測定

#### 3. 文書管理テスト
- **ファイル**: `tests/e2e/test_document_manager.py`
- **内容**:
  - アップロード済み文書の一覧表示
  - 文書の削除機能
  - 文書詳細情報の表示

#### 4. ナビゲーションテスト
- **ファイル**: `tests/e2e/test_navigation.py`
- **内容**:
  - ページ間の移動
  - サイドバーナビゲーション
  - URLルーティング

## 📊 結果の確認

### テスト結果ファイル

```bash
test-results/
├── report-chromium.html     # HTMLレポート（ブラウザ別）
├── report-firefox.html
├── report-webkit.html
├── videos/                  # 失敗時の録画ビデオ
├── screenshots/             # 失敗時のスクリーンショット
└── traces/                  # 詳細トレース情報
```

### HTMLレポートの確認

```bash
# ブラウザでレポートを開く
open test-results/report-chromium.html    # Mac
xdg-open test-results/report-chromium.html # Linux
start test-results/report-chromium.html   # Windows
```

## 🔧 開発・デバッグ

### 個別テストの実行

```bash
# 特定のテストファイルのみ実行
pytest tests/e2e/test_chat_interface.py --browser=chromium --headed

# 特定のテストメソッドのみ実行
pytest tests/e2e/test_chat_interface.py::TestChatInterface::test_basic_question_answer --browser=chromium --headed
```

### デバッグモード

```bash
# テスト内でブレークポイント設定
pytest tests/e2e/test_chat_interface.py --browser=chromium --headed --pdb

# 詳細ログ出力
pytest tests/e2e/ --browser=chromium --headed -v -s
```

### トレース再生

```bash
# 失敗時のトレースを再生（詳細なデバッグ情報）
playwright show-trace test-results/traces/test-trace.zip
```

## 🛠️ トラブルシューティング

### よくある問題と解決方法

#### 1. Streamlitアプリが起動していない
```bash
エラー: Connection refused to http://localhost:8501

解決方法:
1. 別ターミナルでStreamlitアプリを起動
   streamlit run streamlit_app.py
2. アプリが正常に起動するまで待機
3. http://localhost:8501 にアクセスして確認
```

#### 2. Playwrightブラウザが見つからない
```bash
エラー: Browser executable not found

解決方法:
playwright install chromium firefox webkit
```

#### 3. 仮想環境の問題
```bash
エラー: ModuleNotFoundError: No module named 'playwright'

解決方法:
source venv/bin/activate
pip install -r requirements-test.txt
```

#### 4. テストタイムアウト
```bash
エラー: Test timeout

解決方法:
# タイムアウト時間を延長
./scripts/run_e2e_tests.sh --timeout=60000
```

### パフォーマンス最適化

```bash
# 高速実行のための推奨設定
./scripts/run_e2e_tests.sh chromium --headless --video=off --screenshot=off
```

## 📝 CI/CDでの実行（手動トリガー）

GitHub Actionsでは手動トリガーのみ有効：

1. GitHubリポジトリのActionsタブへ移動
2. "E2E Tests with Playwright (Manual Only)" ワークフローを選択
3. "Run workflow" ボタンをクリック
4. ブラウザと環境を選択して実行

## 🔄 定期的なメンテナンス

### 月次チェック項目

- [ ] Playwrightバージョンの更新確認
- [ ] テストの実行時間の測定
- [ ] 失敗したテストケースの分析
- [ ] 新機能に対するテストケースの追加

### テストケースの追加

新機能実装時は対応するE2Eテストの追加を推奨：

1. `tests/e2e/` 配下に新しいテストファイル作成
2. Page Objectパターンで実装
3. `scripts/run_e2e_tests.sh` で動作確認
4. CI設定は更新不要（ローカル実行のみ）