# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

新入社員向け社内文書検索RAGアプリケーション - StreamlitとSupabaseを使用したMVP実装

### 要件概要
- **用途**: 新入社員向け社内文書検索システム
- **データ**: PDF文書（最大10GB、段階的追加）
- **UI**: シンプルなQ&A形式のチャットインターフェース
- **デプロイ**: Streamlit Cloud Community（無料版）
- **言語**: 日本語対応、エラーメッセージも日本語

## Environment Setup

### Python Environment (Streamlit Cloud Community推奨)
```bash
# Python 3.11.x (Streamlit Cloud Community推奨版)
python --version  # 3.11.x を確認

# 仮想環境作成
python -m venv venv
source venv/bin/activate  # Linux/Mac
# venv\Scripts\activate   # Windows

# 依存関係インストール
pip install -r requirements.txt

# ローカル開発サーバー起動
streamlit run streamlit_app.py
```

### Environment Variables
```bash
# .env ファイル作成（本番環境はStreamlit Secrets使用）
OPENAI_API_KEY=your_openai_api_key
ANTHROPIC_API_KEY=your_claude_api_key
SUPABASE_URL=your_supabase_url
SUPABASE_ANON_KEY=your_supabase_anon_key
```

## Technology Stack

### Core Technologies
- **Frontend**: Streamlit
- **Vector Database**: Supabase (PostgreSQL + pgvector)
- **PDF Processing**: PyMuPDF (fitz) + spaCy (日本語NLP)
- **Text Chunking**: spaCy + 日本語境界検出（意味的分割）
- **Embeddings**: OpenAI text-embedding-3-small
- **LLM**: Claude API (Anthropic)
- **Framework**: LangChain

### Dependencies (requirements.txt)
```
streamlit>=1.28.0
langchain>=0.1.0
langchain-openai>=0.0.5
langchain-anthropic>=0.1.0
supabase>=2.0.0
pymupdf>=1.23.0
spacy>=3.7.0
openai>=1.0.0
anthropic>=0.8.0
python-dotenv>=1.0.0
```

## Architecture

### Application Structure
```
streamlit_app.py                 # メインアプリケーション
├── components/
│   ├── pdf_uploader.py         # PDF アップロード UI
│   ├── chat_interface.py       # チャット UI
│   └── document_manager.py     # 文書管理 UI
├── services/
│   ├── pdf_processor.py        # PyMuPDF + spaCy 処理
│   ├── text_chunker.py         # 意味的チャンク分割
│   ├── vector_store.py         # Supabase Vector操作
│   ├── embeddings.py           # OpenAI Embeddings
│   └── claude_llm.py           # Claude API統合
├── utils/
│   ├── config.py              # 設定管理
│   └── error_handler.py       # エラーハンドリング
└── requirements.txt
```

### Database Schema (Supabase)
```sql
-- 文書管理テーブル
CREATE TABLE documents (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    filename TEXT NOT NULL,
    original_filename TEXT NOT NULL,
    upload_date TIMESTAMP DEFAULT NOW(),
    file_size BIGINT,
    total_pages INTEGER,
    processing_status TEXT DEFAULT 'processing',
    created_at TIMESTAMP DEFAULT NOW()
);

-- チャンクテーブル (ベクトル検索用)
CREATE TABLE document_chunks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    document_id UUID REFERENCES documents(id) ON DELETE CASCADE,
    content TEXT NOT NULL,
    filename TEXT NOT NULL,
    page_number INTEGER,
    chapter_number INTEGER,
    section_name TEXT,
    start_pos JSONB,        -- {x, y} 座標
    end_pos JSONB,          -- {x, y} 座標
    embedding VECTOR(1536), -- OpenAI embedding dimension
    token_count INTEGER,
    created_at TIMESTAMP DEFAULT NOW()
);

-- ベクトル検索用インデックス
CREATE INDEX ON document_chunks USING ivfflat (embedding vector_cosine_ops);
```

### Data Processing Flow
1. **PDF Upload** → PyMuPDF抽出 → spaCy文書構造解析
2. **章・セクション検出** → 意味的チャンク分割(512トークン, 10%オーバーラップ)
3. **OpenAI Embeddings生成** → Supabase保存
4. **Query処理** → 類似検索 → Claude API → 回答生成 + 引用情報

### Key Features
- **PDF処理**: 日本語対応、レイアウト保持、座標情報取得
- **チャンクメタデータ**: ファイル名、ページ番号、章番号、セクション名
- **引用表示**: PDFファイル名、ページ番号、関連箇所ハイライト
- **インデックス管理**: PDFアップロード都度、インデックス再構築
- **エラーハンドリング**: 新入社員向け日本語エラーメッセージ

## Development Commands

### Local Development
```bash
# アプリケーション起動
streamlit run streamlit_app.py

# デバッグモード
streamlit run streamlit_app.py --logger.level=debug

# 特定ポートで起動
streamlit run streamlit_app.py --server.port=8502
```

### Testing & Quality
```bash
# テスト実行（テストフレームワーク導入後）
# pytest tests/

# コード品質チェック（導入後）
# flake8 .
# black .
```

### Deployment (Streamlit Cloud Community)
1. GitHubリポジトリにpush
2. Streamlit Cloudでアプリ作成
3. 環境変数をStreamlit Secretsで設定
4. 自動デプロイメント

## Performance Considerations

### Streamlit Cloud Community制約
- **メモリ制限**: 1GB（大きなPDFの分割処理対応）
- **CPU制限**: 非同期処理でUX改善
- **永続化**: 全てSupabaseで外部永続化
- **ネットワーク**: 適切なタイムアウト設定

### Optimization Strategy
- ストリーミング処理による段階的表示
- PDF処理進捗バー
- キャッシュ機能でAPI呼び出し最適化
- 意味的チャンク分割による検索精度向上

## Live Coding Strategy with Claude Code Action

### Issue-Driven Development (IDD) Framework

#### Issue Structure Template
```markdown
## 背景・目的
[機能の必要性と期待される効果]

## 要件
- [ ] 具体的な機能要件1
- [ ] 具体的な機能要件2
- [ ] 非機能要件（パフォーマンス、セキュリティ等）

## 技術仕様
- 使用技術: [具体的なライブラリ、API]
- インターフェース: [関数シグネチャ、クラス設計]
- データ構造: [入出力形式]

## 成功基準
- [ ] 機能動作確認
- [ ] テストケース全件Pass
- [ ] CI/CD品質チェック通過
- [ ] コードレビュー承認

## テストケース
### 正常系
- [ ] [期待する動作1]
- [ ] [期待する動作2]
### 異常系
- [ ] [エラーハンドリング1]
- [ ] [エラーハンドリング2]
```

#### Issue Classification
- **Epic**: 大機能 (例: PDF処理システム全体)
- **Feature**: 個別機能 (例: テキスト抽出機能)
- **Task**: 具体作業 (例: PyMuPDF統合)
- **Bug**: 不具合修正
- **Refactor**: コード改善
- **Test**: テスト追加・改善

### Test-Driven Development (TDD) Strategy

#### TDD Cycle for Live Coding
```python
# Phase 1: Red (失敗テスト作成)
def test_pdf_text_extraction():
    """PDFテキスト抽出のテストケース"""
    # Arrange
    mock_pdf_path = "tests/fixtures/sample.pdf"
    expected_text = "期待されるテキスト内容"
    
    # Act & Assert
    with pytest.raises(NotImplementedError):
        result = extract_text_from_pdf(mock_pdf_path)
        assert expected_text in result

# Phase 2: Green (最小実装)
def extract_text_from_pdf(pdf_path: str) -> str:
    """PDF from text extraction - minimal implementation"""
    raise NotImplementedError("実装予定")

# Phase 3: Refactor (品質向上)
# - 型ヒント追加
# - ドックストリング完備  
# - エラーハンドリング強化
```

#### Mock Testing Strategy for External Services
```python
# OpenAI API Mock
@pytest.fixture
def mock_openai_client():
    with patch('openai.OpenAI') as mock:
        mock.return_value.embeddings.create.return_value.data = [
            Mock(embedding=[0.1] * 1536)
        ]
        yield mock

# Claude API Mock  
@pytest.fixture
def mock_claude_client():
    with patch('anthropic.Anthropic') as mock:
        mock.return_value.messages.create.return_value.content = [
            Mock(text="モックされた回答")
        ]
        yield mock

# Supabase Mock
@pytest.fixture
def mock_supabase_client():
    with patch('supabase.create_client') as mock:
        mock.return_value.table.return_value.insert.return_value.execute.return_value = Mock()
        yield mock
```

### CI/CD Pipeline Configuration

#### GitHub Actions Workflow (.github/workflows/ci.yml)
```yaml
name: CI/CD Pipeline

on:
  push:
    branches: [ main, develop ]
  pull_request:
    branches: [ main ]

jobs:
  test:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        python-version: [3.11]

    steps:
    - uses: actions/checkout@v4
    
    - name: Set up Python
      uses: actions/setup-python@v4
      with:
        python-version: ${{ matrix.python-version }}
    
    - name: Cache pip dependencies
      uses: actions/cache@v3
      with:
        path: ~/.cache/pip
        key: ${{ runner.os }}-pip-${{ hashFiles('**/requirements*.txt') }}
    
    - name: Install dependencies
      run: |
        python -m pip install --upgrade pip
        pip install -r requirements.txt
        pip install -r requirements-dev.txt
    
    - name: Lint with flake8
      run: |
        flake8 . --count --select=E9,F63,F7,F82 --show-source --statistics
        flake8 . --count --exit-zero --max-complexity=10 --max-line-length=88 --statistics
    
    - name: Format check with black
      run: black --check --diff .
    
    - name: Type check with mypy
      run: mypy .
    
    - name: Security check with bandit
      run: bandit -r . -x tests/
    
    - name: Test with pytest
      run: |
        pytest tests/ --cov=. --cov-report=xml --cov-report=html
      env:
        # Mock environment variables for testing
        OPENAI_API_KEY: "mock-key"
        ANTHROPIC_API_KEY: "mock-key"
        SUPABASE_URL: "https://mock.supabase.co"
        SUPABASE_ANON_KEY: "mock-key"
    
    - name: Upload coverage to Codecov
      uses: codecov/codecov-action@v3
      with:
        file: ./coverage.xml

  security:
    runs-on: ubuntu-latest
    steps:
    - uses: actions/checkout@v4
    - name: Run Trivy vulnerability scanner
      uses: aquasecurity/trivy-action@master
      with:
        scan-type: 'fs'
        scan-ref: '.'
```

#### Development Dependencies (requirements-dev.txt)
```
# Testing
pytest>=7.4.0
pytest-cov>=4.1.0
pytest-mock>=3.11.0
pytest-asyncio>=0.21.0

# Code Quality
black>=23.7.0
flake8>=6.0.0
mypy>=1.5.0
isort>=5.12.0

# Security
bandit>=1.7.5
safety>=2.3.0

# Documentation
sphinx>=7.1.0
sphinx-rtd-theme>=1.3.0
```

### Live Coding Best Practices

#### Code Quality Standards
```python
# 1. Type Hints Required
def process_pdf(file_path: Path) -> ProcessingResult:
    """PDF処理のメイン関数
    
    Args:
        file_path: 処理対象PDFファイルのパス
        
    Returns:
        ProcessingResult: 処理結果と メタデータ
        
    Raises:
        FileNotFoundError: ファイルが存在しない場合
        PDFProcessingError: PDF処理エラーの場合
    """
    pass

# 2. Error Handling Required  
try:
    result = risky_operation()
except SpecificException as e:
    logger.error(f"処理エラー: {str(e)}")
    raise ProcessingError(f"適切なエラーメッセージ: {str(e)}") from e

# 3. Logging Required
import logging
logger = logging.getLogger(__name__)

def important_function():
    logger.info("重要な処理を開始")
    # 処理内容
    logger.info("重要な処理を完了")
```

#### PR Template (.github/pull_request_template.md)
```markdown
## 変更内容
- [ ] 新機能追加
- [ ] バグ修正  
- [ ] リファクタリング
- [ ] ドキュメント更新

## 関連Issue
Closes #[issue_number]

## テスト
- [ ] 既存テスト全件Pass
- [ ] 新規テスト追加済み
- [ ] 手動テスト実施済み

## チェックリスト
- [ ] コードレビュー依頼済み
- [ ] CI/CD全件Pass
- [ ] 型ヒント追加済み
- [ ] ドックストリング追加済み
- [ ] エラーハンドリング実装済み

## Claude Code Action使用
- [ ] 自然言語による指示で実装
- [ ] TDDサイクルで開発
- [ ] モックテスト実装済み
```

### Live Coding Workflow

#### Step-by-Step Process
1. **Issue作成**: 詳細なテンプレートで要件明確化
2. **Branch作成**: `feature/issue-number-brief-description`
3. **TDD開始**: Red → Green → Refactor
4. **Claude Code Action**: 自然言語指示で効率実装
5. **CI実行**: 自動品質チェック
6. **PR作成**: テンプレート使用で情報整理
7. **コードレビュー**: 品質確保とナレッジ共有
8. **マージ**: 品質基準クリア後

#### Quality Gates
- **コミット前**: pre-commit hooks実行
- **PR作成時**: CI/CD全件通過必須
- **マージ前**: コードレビュー承認必須
- **デプロイ前**: E2Eテスト実行

### Mock Testing Configuration

#### External Service Mocking
```python
# conftest.py - テスト共通設定
import pytest
from unittest.mock import Mock, patch

@pytest.fixture(autouse=True)  
def mock_external_apis():
    """全テストで外部API呼び出しをモック化"""
    with patch.multiple(
        'services.embeddings',
        OpenAI=Mock(),
        spec=True
    ), patch.multiple(
        'services.claude_llm',
        Anthropic=Mock(),
        spec=True  
    ), patch.multiple(
        'services.vector_store',
        create_client=Mock(),
        spec=True
    ):
        yield
```

This comprehensive live coding strategy ensures high-quality development while maintaining the efficiency of natural language-driven coding with Claude Code Action.