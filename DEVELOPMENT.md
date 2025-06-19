# 開発環境ガイド - RAG Demo Project

新入社員向け社内文書検索RAGアプリケーションの開発環境設定と使用方法について説明します。

## 🚀 クイックスタート

### 1. 環境セットアップ

```bash
# リポジトリクローン
git clone https://github.com/moma1992/RAG-demo.git
cd RAG-demo

# 仮想環境作成・有効化
python -m venv venv
source venv/bin/activate  # Linux/Mac
# venv\Scripts\activate   # Windows

# 開発環境インストール
make setup
# または
pip install -r requirements.txt
pip install -r requirements-dev.txt
pre-commit install
```

### 2. アプリケーション起動

```bash
# 通常起動
make run
# または
streamlit run streamlit_app.py

# デバッグモード
make run-debug
```

## 🛠️ 開発ツール

### コード品質管理

| ツール | 用途 | コマンド |
|--------|------|----------|
| **Black** | コードフォーマット | `make format` |
| **isort** | インポート整理 | `make format` |
| **Flake8** | 静的解析・リント | `make lint` |
| **mypy** | 型チェック | `make type-check` |
| **Bandit** | セキュリティスキャン | `make security` |
| **pre-commit** | コミット前チェック | `make pre-commit` |

### テスト

```bash
# 全テスト実行
make test

# カバレッジ付きテスト
make test-cov

# 高速テスト（slowマーカー除く）
make test-fast

# 特定テスト実行
pytest tests/test_pdf_processor.py
```

### 品質保証

```bash
# 全品質チェック実行
make qa

# CI/CDシミュレーション
make ci

# 本番準備チェック
make prod-check
```

## 📁 プロジェクト構造

```
RAG-demo/
├── streamlit_app.py           # メインアプリケーション
├── components/                # UI コンポーネント
│   ├── chat_interface.py
│   ├── document_manager.py
│   └── pdf_uploader.py
├── services/                  # ビジネスロジック
│   ├── claude_llm.py
│   ├── embeddings.py
│   ├── pdf_processor.py
│   ├── text_chunker.py
│   └── vector_store.py
├── models/                    # データモデル
│   ├── chat.py
│   └── document.py
├── utils/                     # ユーティリティ
│   ├── config.py
│   └── error_handler.py
├── tests/                     # テストコード
├── docs/                      # ドキュメント
├── requirements.txt           # 本番依存関係
├── requirements-dev.txt       # 開発依存関係
├── pyproject.toml            # プロジェクト設定
├── setup.cfg                 # レガシー設定サポート
├── .pre-commit-config.yaml   # pre-commit設定
├── Makefile                  # 開発コマンド
└── CLAUDE.md                 # Claude Code指示書
```

## 🔧 設定ファイル

### 環境変数 (.env)

```bash
# OpenAI
OPENAI_API_KEY=your_openai_api_key

# Anthropic
ANTHROPIC_API_KEY=your_claude_api_key  

# Supabase
SUPABASE_URL=your_supabase_url
SUPABASE_ANON_KEY=your_supabase_anon_key
```

### Streamlit設定 (.streamlit/secrets.toml)

```toml
# 本番環境用（Streamlit Cloud）
OPENAI_API_KEY = "your_key"
ANTHROPIC_API_KEY = "your_key"
SUPABASE_URL = "your_url"
SUPABASE_ANON_KEY = "your_key"
```

## 📋 開発ワークフロー

### 1. 機能開発

```bash
# 新機能ブランチ作成
git checkout -b feature/new-feature

# 開発サイクル
make dev  # format + lint + type-check + test-fast

# コミット前チェック
make pre-commit

# コミット
git add .
git commit -m "feat: 新機能追加"
```

### 2. テスト駆動開発 (TDD)

```bash
# 1. テスト作成 (Red)
pytest tests/test_new_feature.py  # 失敗確認

# 2. 最小実装 (Green) 
# コード実装...
pytest tests/test_new_feature.py  # 成功確認

# 3. リファクタリング (Refactor)
make qa  # 品質チェック
```

### 3. プルリクエスト

```bash
# 最終チェック
make ci

# プッシュ
git push origin feature/new-feature

# GitHub上でPR作成
```

## 🧪 テスト戦略

### テスト分類

- **Unit Tests**: 個別関数・クラスのテスト
- **Integration Tests**: サービス間連携テスト  
- **Slow Tests**: 外部API呼び出しを含む重いテスト

### モック対象

```python
# 外部API呼び出しは必ずモック化
@pytest.fixture
def mock_openai_client():
    with patch('openai.OpenAI') as mock:
        yield mock

@pytest.fixture  
def mock_claude_client():
    with patch('anthropic.Anthropic') as mock:
        yield mock

@pytest.fixture
def mock_supabase_client():
    with patch('supabase.create_client') as mock:
        yield mock
```

## 🔍 トラブルシューティング

### 一般的な問題

```bash
# 依存関係の問題
make clean
make install-dev

# キャッシュクリア
make clean

# pre-commit hooks更新
make pre-commit-update

# 依存関係確認
make deps-check
make deps-tree
```

### パフォーマンス問題

```bash
# メモリ使用量確認
memory_profiler: @profile デコレータ使用

# 実行時間確認  
line_profiler: kernprof -l -v script.py
```

## 📚 参考資料

- [Streamlit Documentation](https://docs.streamlit.io/)
- [LangChain Documentation](https://python.langchain.com/)
- [Supabase Documentation](https://supabase.com/docs)
- [Black Code Style](https://black.readthedocs.io/)
- [pytest Documentation](https://docs.pytest.org/)

## 💡 ベストプラクティス

### コード品質
- 型ヒント必須
- Googleスタイル ドックストリング
- 日本語エラーメッセージ
- セキュリティベストプラクティス準拠

### Git
- コミットメッセージ: [Conventional Commits](https://www.conventionalcommits.org/)
- ブランチ命名: `feature/`, `fix/`, `docs/`, `refactor/`
- PR前に`make ci`実行

### Streamlit制約
- メモリ制限: 1GB (Community版)
- CPU制限考慮
- 外部永続化必須 (Supabase)