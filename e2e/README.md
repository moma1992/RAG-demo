# E2E テストスイート

StreamlitアプリケーションのためのEnd-to-Endテストスイート（ローカル実行専用）

## 📁 ディレクトリ構造

```
e2e/
├── README.md              # このファイル
├── .gitignore            # E2Eテスト結果の除外設定
├── scripts/              # 実行スクリプト
│   ├── run_e2e.sh        # 統合テスト実行スクリプト
│   ├── setup_e2e.sh      # 環境セットアップスクリプト
│   └── clean_results.sh  # 結果クリーンアップスクリプト
├── docs/                 # ドキュメント
│   └── E2E_TEST_GUIDE.md # 詳細テストガイド
├── results/              # テスト結果（自動生成）
│   ├── report-*.html     # HTMLテストレポート
│   ├── videos/           # 失敗時の録画ビデオ
│   ├── screenshots/      # スクリーンショット
│   └── traces/           # Playwrightトレース
├── fixtures/             # テスト用フィクスチャ
│   └── generate_sample.py # サンプルPDF生成スクリプト
└── configs/              # 設定ファイル
```

## 🚀 クイックスタート

### 1. 環境セットアップ

```bash
# E2E環境の初期セットアップ
./e2e/scripts/setup_e2e.sh

# 全ブラウザをインストール
./e2e/scripts/setup_e2e.sh --browsers=all
```

### 2. テスト実行

```bash
# クイック実行（推奨）
./e2e/scripts/run_e2e.sh

# 基本テストのみ実行
./e2e/scripts/run_e2e.sh basic

# フル機能テスト（録画あり）
./e2e/scripts/run_e2e.sh full

# ブラウザ指定
./e2e/scripts/run_e2e.sh quick firefox

# 単一テスト実行
./e2e/scripts/run_e2e.sh single

# ヘルプ表示
./e2e/scripts/run_e2e.sh help
```

### 3. 結果確認

```bash
# HTMLレポートを開く
open e2e/results/report-chromium.html

# 結果フォルダを確認
ls -la e2e/results/
```

## 🛠️ スクリプト詳細

### run_e2e.sh

統合テスト実行スクリプト（全機能を1つに統合）

```bash
# 使用例
./e2e/scripts/run_e2e.sh [mode] [browser]

# モード
quick                   # 全テスト高速実行（録画なし）【デフォルト】
basic                   # 基本テストのみ実行
full                    # 全テスト実行（録画あり）
single                  # 単一テスト選択実行
help                    # ヘルプ表示

# ブラウザ
chromium                # Chromiumブラウザ【デフォルト】
firefox                 # Firefoxブラウザ
webkit                  # WebKitブラウザ

# 環境変数
E2E_BASE_URL            # ベースURL（デフォルト: http://localhost:8501）
E2E_RECORD_VIDEO        # 動画録画（true/false、デフォルト: false）
E2E_TIMEOUT             # テストタイムアウト（秒、デフォルト: 60）
```

### setup_e2e.sh

E2E環境の初期セットアップスクリプト

```bash
# 使用例
./e2e/scripts/setup_e2e.sh [options]

# オプション
--browsers=LIST         # インストールするブラウザ
--force                 # 既存設定を上書き
--skip-venv            # 仮想環境作成をスキップ
--skip-deps            # 依存関係インストールをスキップ
--skip-browsers        # ブラウザインストールをスキップ
```

### clean_results.sh

テスト結果のクリーンアップスクリプト

```bash
# 使用例
./e2e/scripts/clean_results.sh [options]

# オプション
--all                  # 全ファイル削除
--reports              # HTMLレポートのみ削除
--videos               # ビデオファイルのみ削除
--screenshots          # スクリーンショットのみ削除
--traces               # トレースファイルのみ削除
--old=DAYS             # 指定日数より古いファイルを削除
--dry-run              # 削除対象を表示のみ
```

## 📊 テスト結果

### 自動生成される結果ファイル

- **HTMLレポート**: `results/report-{browser}.html`
- **ビデオ録画**: `results/videos/` (失敗時)
- **スクリーンショット**: `results/screenshots/` (失敗時)
- **トレース**: `results/traces/` (デバッグ用)

### 結果の管理

```bash
# 古い結果を削除（7日より古い）
./e2e/scripts/clean_results.sh

# 全結果を削除
./e2e/scripts/clean_results.sh --all

# 削除対象を確認（実際には削除しない）
./e2e/scripts/clean_results.sh --dry-run
```

## 🔧 設定とカスタマイズ

### 環境変数

```bash
# E2E実行時の設定
export E2E_HEADLESS=true
export E2E_BASE_URL=http://localhost:8501
export E2E_TIMEOUT=30000
```

### ブラウザ設定

- **Chromium**: 高速、安定
- **Firefox**: 互換性テスト
- **WebKit**: Safari互換性

### 録画・スクリーンショット設定

- **on**: 常に記録
- **off**: 記録しない
- **retain-on-failure**: 失敗時のみ（推奨）
- **only-on-failure**: 失敗時のみ

## 📚 ドキュメント

詳細な使用方法とトラブルシューティングは以下を参照：

- [E2E_TEST_GUIDE.md](docs/E2E_TEST_GUIDE.md) - 完全なテストガイド

## 🚫 CI/CDでの実行

E2EテストはCIから除外されており、ローカル実行専用です。

### 手動GitHub Actions実行

1. GitHubリポジトリのActionsタブに移動
2. "E2E Tests with Playwright (Manual Only)" を選択
3. "Run workflow" で手動実行

## 🧹 メンテナンス

### 定期的なクリーンアップ

```bash
# 週次実行推奨
./e2e/scripts/clean_results.sh --old=7

# 月次実行推奨
./e2e/scripts/clean_results.sh --old=30
```

### アップデート

```bash
# Playwrightブラウザ更新
./e2e/scripts/setup_e2e.sh --browsers=all --force

# 依存関係更新
./e2e/scripts/setup_e2e.sh --skip-browsers --force
```

## 🆘 トラブルシューティング

### よくある問題

1. **ブラウザが見つからない**
   ```bash
   ./e2e/scripts/setup_e2e.sh --browsers=all
   ```

2. **Streamlitアプリが起動していない**
   ```bash
   streamlit run streamlit_app.py
   ```

3. **依存関係エラー**
   ```bash
   ./e2e/scripts/setup_e2e.sh --force
   ```

4. **ディスク容量不足**
   ```bash
   ./e2e/scripts/clean_results.sh --all
   ```

### デバッグ

```bash
# 詳細ログ出力
pytest tests/e2e/ --browser=chromium --headed -v -s

# トレース再生
playwright show-trace e2e/results/traces/test-trace.zip
```

## 📈 パフォーマンス最適化

```bash
# 高速実行設定
./e2e/scripts/run_e2e.sh quick chromium
```

---

**Note**: E2Eテストはローカル開発環境でのみ実行され、CI/CDパイプラインには含まれません。