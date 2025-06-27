# 新入社員向け社内文書検索RAGアプリケーション

StreamlitとSupabaseを使用したMVP実装

## 🎯 プロジェクト概要

新入社員が社内文書を効率的に検索・参照できるRAG（Retrieval-Augmented Generation）システムです。PDF文書をアップロードし、自然言語で質問することで、関連する情報を素早く見つけることができます。

**✨ 2025年最新版**: 強化された429エラー対策により、より安定したAIコードレビューを提供

### 🔧 AI Code Review Workflow
本プロジェクトには2段階のAIコードレビューシステムが導入されています：

#### 🥇 Primary Review: Gemini AI (Enhanced with 429 Error Handling)
- すべてのPull Requestに対してGemini AIによる包括的なコード分析が自動実行
- 基本的なコード品質、バグ検出、ベストプラクティスチェック
- **429エラー対策**: 3回リトライ機能（30s/60s/90s指数バックオフ）
- **同時実行制限**: 複数PRでのAPI制限衝突を回避
- **.github/REVIEW_TEMPLATE.md形式**: 統一されたレビュー出力

#### 🥈 Secondary Review: Claude (Manual Trigger)
- Gemini reviewの品質保証とダブルチェック
- **トリガー**: PRコメントに `@claudereview` と記載
- MCP（Memory Control Protocol）を活用した高度な技術分析
- 業界ベストプラクティスとの比較、セキュリティ分析

#### 🔧 レビューシステムの信頼性向上
- **Gemini APIの制限対応**: Google公式Issue対応済み（[#1502](https://github.com/google-gemini/gemini-cli/issues/1502)）
- **自動復旧機能**: 一時的なAPI制限でも自動的にリトライ
- **詳細なエラー報告**: 問題特定と解決策の自動提示

## ✨ 主な機能

- 📁 **PDF文書アップロード**: 複数のPDFファイルを同時にアップロード
- 🔍 **自然言語検索**: 日本語での質問に対する文書検索
- 💬 **チャットインターフェース**: 直感的なQ&A形式
- 📚 **引用表示**: 回答の根拠となる文書とページ番号を表示
- 📊 **文書管理**: アップロード済み文書の管理機能

## 🏗️ 技術スタック

- **Frontend**: Streamlit
- **Vector Database**: Supabase (PostgreSQL + pgvector)
- **PDF Processing**: PyMuPDF (fitz) + spaCy
- **Embeddings**: OpenAI text-embedding-3-small
- **LLM**: Claude API (Anthropic)
- **Deployment**: Streamlit Cloud Community

## 🚀 クイックスタート

### 前提条件

- Python 3.11以上
- OpenAI APIキー
- Anthropic Claude APIキー  
- Supabaseプロジェクト

### 1. リポジトリクローン

```bash
git clone https://github.com/moma1992/RAG-demo.git
cd RAG-demo
```

### 2. 仮想環境セットアップ

```bash
python -m venv venv
source venv/bin/activate  # Linux/Mac
# venv\Scripts\activate   # Windows
```

### 3. 依存関係インストール

```bash
pip install -r requirements.txt
```

### 4. 環境変数設定

```bash
cp .env.example .env
# .env ファイルを編集してAPIキーを設定
```

### 5. Streamlit Secrets設定（本番環境）

```bash
cp .streamlit/secrets.toml.example .streamlit/secrets.toml
# secrets.toml ファイルを編集してAPIキーを設定
```

### 6. アプリケーション起動

```bash
streamlit run streamlit_app.py
```

## 🔧 開発環境セットアップ

### 開発用依存関係インストール

```bash
pip install -r requirements-dev.txt
```

### コード品質チェック

```bash
# フォーマット
black .
isort .

# 型チェック
mypy .

# 静的解析
flake8 .

# セキュリティチェック
bandit -r .
```

### テスト実行

#### 単体テスト
```bash
# 全テスト実行
pytest

# カバレッジ付きテスト
pytest --cov=. --cov-report=html

# 特定のテストファイル実行
pytest tests/test_pdf_processor.py
```

#### E2Eテスト（ローカルのみ）
```bash
# E2E環境セットアップ
./e2e/scripts/setup_e2e.sh

# E2Eテスト実行（要：Streamlitアプリ起動）
./e2e/scripts/run_e2e_tests.sh

# 特定ブラウザで実行
./e2e/scripts/run_e2e_tests.sh firefox

# 詳細は e2e/README.md を参照
```

## 📋 必要な環境変数

| 変数名 | 説明 | 必須 |
|--------|------|------|
| `OPENAI_API_KEY` | OpenAI APIキー | ✅ |
| `ANTHROPIC_API_KEY` | Claude APIキー | ✅ |
| `SUPABASE_URL` | Supabase プロジェクトURL | ✅ |
| `SUPABASE_ANON_KEY` | Supabase Anonymous キー | ✅ |
| `MAX_FILE_SIZE_MB` | 最大ファイルサイズ（MB） | ⚪ |
| `CHUNK_SIZE` | チャンクサイズ（トークン） | ⚪ |

## 🗄️ データベーススキーマ

```sql
-- 文書管理テーブル
CREATE TABLE documents (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    filename TEXT NOT NULL,
    original_filename TEXT NOT NULL,
    upload_date TIMESTAMP DEFAULT NOW(),
    file_size BIGINT,
    total_pages INTEGER,
    processing_status TEXT DEFAULT 'processing'
);

-- チャンクテーブル
CREATE TABLE document_chunks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    document_id UUID REFERENCES documents(id) ON DELETE CASCADE,
    content TEXT NOT NULL,
    filename TEXT NOT NULL,
    page_number INTEGER,
    embedding VECTOR(1536),
    token_count INTEGER
);

-- ベクトル検索用インデックス
CREATE INDEX ON document_chunks USING ivfflat (embedding vector_cosine_ops);
```

## 📁 プロジェクト構造

```
RAG-demo/
├── streamlit_app.py           # メインアプリケーション
├── components/                # UI コンポーネント
│   ├── pdf_uploader.py       # PDF アップロード
│   ├── chat_interface.py     # チャット UI
│   └── document_manager.py   # 文書管理
├── services/                  # ビジネスロジック
│   ├── pdf_processor.py      # PDF 処理
│   ├── text_chunker.py       # テキスト分割
│   ├── vector_store.py       # ベクトル操作
│   ├── embeddings.py         # 埋め込み生成
│   └── claude_llm.py         # Claude API
├── utils/                     # ユーティリティ
│   ├── config.py             # 設定管理
│   └── error_handler.py      # エラー処理
├── models/                    # データモデル
├── tests/                     # テストコード
├── docs/                      # ドキュメント
└── .streamlit/               # Streamlit 設定
```

## 🚀 デプロイメント

### Streamlit Cloud Community

1. GitHubリポジトリにプッシュ
2. [Streamlit Cloud](https://streamlit.io/cloud) でアプリ作成
3. 環境変数をStreamlit Secretsで設定
4. 自動デプロイメント

## 🤝 コントリビューション

1. このリポジトリをフォーク
2. フィーチャーブランチを作成 (`git checkout -b feature/amazing-feature`)
3. 変更をコミット (`git commit -m 'Add some amazing feature'`)
4. ブランチにプッシュ (`git push origin feature/amazing-feature`)
5. Pull Requestを作成

## 📄 ライセンス

このプロジェクトは MIT ライセンスの下で公開されています。

## 🙋‍♂️ サポート

質問や問題がある場合は、Issueを作成してください。

---

**🤖 Generated with [Claude Code](https://claude.ai/code)**