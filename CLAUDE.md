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

# Supabase MCP設定（Claude Code連携用）
SUPABASE_PROJECT_REF=your_project_ref
SUPABASE_ACCESS_TOKEN=your_personal_access_token
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

## MCP Integration Strategy

### Advanced Code Review Enhancement Framework

Claude Codeでの開発効率を最大化するため、3つのMCPサーバーを戦略的に活用し、特にGitHub ActionsでのPRレビューを大幅に強化します。

#### **Triple MCP Framework for Enhanced Code Review**
- **DeepWiki MCP**: オープンソースプロジェクト分析・アーキテクチャパターン研究・ベストプラクティス発見
- **Supabase MCP**: データベース管理・リアルタイム監視・スキーマ最適化分析
- **Context7 MCP**: 技術的質問・ライブラリ最適化・セキュリティ脆弱性調査・パフォーマンス改善

#### **GitHub Actions MCP-Enhanced Review Workflow**
```yaml
# Advanced Claude Code Review with MCP Intelligence
name: Advanced Claude Code Review with MCP Intelligence

# 3段階のインテリジェント分析プロセス:
# 1. MCP Context Analysis - 技術スタック自動検出・複雑度分析
# 2. Claude Review with MCP Tools - DeepWiki・Context7連携レビュー  
# 3. Learning Insights Generation - 継続改善のための知見蓄積
```

#### **MCP Tools Integration in Code Review**
- **研究フェーズ**: DeepWikiで類似プロジェクト分析（facebook/react, openai/openai-python等）
- **技術検証フェーズ**: Context7でベストプラクティス調査・セキュリティパターン分析
- **品質評価フェーズ**: 研究結果を基にした総合的コードレビュー
- **学習蓄積フェーズ**: レビュー結果の知識ベース化・継続改善

### Python Development Phase Integration

| フェーズ | DeepWiki MCP | Supabase MCP | Context7 MCP | 主要用途 |
|---------|-------------|-------------|-------------|---------|
| **ライブラリ選定** | Python RAGプロジェクト調査 | - | PyMuPDF vs PyPDF2比較 | 最適ライブラリ選択 |
| **実装設計** | Pythonアーキテクチャパターン | スキーマ設計検証 | spaCy/LangChain設計パターン | Pythonic設計 |
| **コーディング** | Python実装例参照 | リアルタイムDB監視 | ライブラリAPI詳細調査 | 実装品質向上 |
| **エラー解決** | 類似エラー事例調査 | データ整合性確認 | Python例外処理ベストプラクティス | 迅速問題解決 |
| **最適化** | Pythonパフォーマンス事例 | クエリ最適化監視 | asyncio/マルチプロセス最適化 | パフォーマンス向上 |

### Python-Specific Use Cases

#### **PDF Processing Libraries**
```python
# Context7での調査例
# "PyMuPDF vs PyPDF2 vs pdfplumber performance comparison"
# "spaCy Japanese text processing best practices"
# "LangChain document chunking strategies"
```

#### **Error Resolution Pattern**
```python
# 1. Python例外発生時の対応フロー
try:
    result = process_pdf_with_pymupdf(file_path)
except Exception as e:
    # Context7: "PyMuPDF common errors and solutions"
    # DeepWiki: 類似エラー実装例調査
    # Supabase: DB接続状態確認
    handle_error_with_mcp_insights(e)
```

#### **Library Selection Workflow**
```python
# 開発フェーズでの情報収集戦略
def select_best_library():
    # 1. Context7: ライブラリ比較・性能調査
    # 2. DeepWiki: 実際のプロジェクトでの使用例
    # 3. Supabase: 実装後のパフォーマンス監視
    pass
```

### MCP Server Configuration

#### 設定ファイル (.claude/mcp.json)
```json
{
  "mcpServers": {
    "context7": {
      "command": "npx",
      "args": ["mcp-remote", "https://mcp.context7.com/sse"]
    },
    "deepwiki": {
      "command": "npx", 
      "args": ["mcp-remote", "https://mcp.deepwiki.com/sse"]
    },
    "supabase": {
      "command": "npx",
      "args": [
        "-y",
        "@supabase/mcp-server-supabase@latest",
        "--read-only",
        "--project-ref=${SUPABASE_PROJECT_REF}"
      ],
      "env": {
        "SUPABASE_ACCESS_TOKEN": "${SUPABASE_ACCESS_TOKEN}"
      }
    }
  }
}
```

#### 必要な環境変数
```bash
# Supabase MCP設定
SUPABASE_PROJECT_REF=your_project_ref
SUPABASE_ACCESS_TOKEN=your_personal_access_token
```

#### セットアップ手順
1. Supabaseダッシュボードでプロジェクト参照IDを確認
2. 個人アクセストークンを生成（Settings > Access Tokens）
3. `.env`ファイルに環境変数を設定
4. Claude Code再起動でMCPサーバー接続確認

### Python Development Workflows

#### **情報収集最適化パターン**
```python
# 1. ライブラリ選定時
# Context7: "streamlit file upload best practices"
# DeepWiki: Streamlit + PDF処理の実装例調査

# 2. 実装時
# Context7: "spaCy Japanese tokenization optimization"  
# Supabase: 実装したテーブル構造の確認

# 3. エラー解決時
# Context7: "LangChain embeddings error handling"
# DeepWiki: 類似エラーの解決事例調査
# Supabase: データベース接続・クエリ実行状況確認
```

#### **品質向上サイクル**
```python
# TDD + MCP統合サイクル
def enhanced_tdd_with_mcp():
    # Red: 失敗テスト作成
    # Context7: テストパターン・ベストプラクティス調査
    
    # Green: 最小実装
    # DeepWiki: 実装例参照
    # Supabase: DB操作確認
    
    # Refactor: 品質向上
    # Context7: リファクタリングパターン調査
    pass
```

### 利用可能な機能

#### **DeepWiki MCP**
- GitHubリポジトリの実装例調査
- Python RAGプロジェクトのアーキテクチャ学習
- 類似エラー・問題の解決事例収集

#### **Context7 MCP**  
- Pythonライブラリの詳細調査・比較
- エラーメッセージの解析・解決策提案
- Pythonベストプラクティス・設計パターン学習

#### **Supabase MCP**
- データベース構造の確認・分析
- テーブルデータの読み取り（読み取り専用）
- SQLクエリの実行（SELECT文のみ）
- リアルタイムDB監視・パフォーマンス分析

### 期待される効果

- **開発効率**: 40-60%向上（技術調査時間短縮）
- **コード品質**: 継続的学習とベストプラクティス適用
- **問題解決**: 包括的情報収集による迅速な課題解決
- **学習効果**: 実践的な技術スキル向上

## Issue-Driven Development (IDD) 品質保証ワークフロー

### チケット確認の徹底プロセス

Claude Codeでの開発において、要件の見落としを防ぐための必須プロセス。

#### **Stage 1: チケット内容の多角的確認**
```python
# 必須実行パターン（開発開始前）
def comprehensive_issue_analysis():
    # 1. 初回チケット確認
    WebFetch(issue_url, "Extract complete requirements and functionality")
    
    # 2. 疑問点がある場合の再確認
    WebFetch(issue_url, "Focus on specific implementation details")
    
    # 3. 関連情報の調査
    WebFetch(related_prs_or_commits, "Check similar implementations")
    
    # 4. 既存コードベースの調査
    Glob("**/*{relevant_pattern}*")
    Read(related_files)
```

#### **Stage 2: 要件の構造化・検証**
```python
# TodoWriteで要件整理（必須）
def structure_requirements():
    todos = [
        "チケット要件の完全理解・再確認",
        "実装すべき機能の詳細リスト化",
        "既存システムとの関係性分析", 
        "データクラス・API設計",
        "テストケース設計",
        "実装優先度の決定"
    ]
    TodoWrite(todos)
```

#### **Stage 3: 実装前最終検証**
```python
# 実装開始前チェックリスト
def pre_implementation_verification():
    # 要件再確認（必須）
    WebFetch(issue_url, "Re-verify all requirements before implementation")
    
    # アーキテクチャ検証
    existing_patterns = analyze_codebase_patterns()
    proposed_design = create_implementation_plan()
    validate_consistency(existing_patterns, proposed_design)
    
    # スコープ確認
    confirm_implementation_scope()
```

### PRレビューワークフロー

#### **自動品質チェック（PR作成前必須）**
```bash
# コード品質チェック
python -m black .
python -m flake8 .
python -m mypy .

# テスト実行
python -m pytest tests/ -v --cov=.

# セキュリティチェック
python -m bandit -r .
```

#### **PR作成時チェックリスト**
```markdown
## PR作成前必須確認事項

### チケット要件充足確認
- [ ] 元Issueを再読み、全要件をカバーしているか？
- [ ] 実装した機能がチケットの主要目的と一致しているか？
- [ ] 見落とした要件や機能はないか？

### 実装品質確認  
- [ ] 新規クラス・関数が適切に設計されているか？
- [ ] 既存システムとの整合性は取れているか？
- [ ] エラーハンドリングは十分か？

### テスト品質確認
- [ ] 正常系・異常系テストケースは網羅的か？
- [ ] パフォーマンス要件は満たしているか？
- [ ] テストカバレッジは80%以上か？

### ドキュメント確認
- [ ] 型ヒント・ドックストリングは完備されているか？
- [ ] 複雑な実装にコメントは適切に記載されているか？
```

#### **Claude Code PR Review Process**

```python
# PR レビュー用Claude Code Action
def review_pr_implementation():
    # 1. チケット要件との照合
    original_issue = WebFetch(issue_url)
    implementation_files = [Read(file) for file in changed_files]
    verify_requirements_coverage(original_issue, implementation_files)
    
    # 2. コード品質レビュー
    run_quality_checks()
    
    # 3. テストレビュー
    test_files = [Read(file) for file in test_files]
    verify_test_coverage(test_files)
    
    # 4. アーキテクチャレビュー
    verify_design_consistency()
```

### 品質ゲート設定

#### **必須通過条件**
1. **要件充足率**: 100%（チケット要件完全実装）
2. **テストカバレッジ**: 80%以上
3. **コード品質**: Black、Flake8、mypy全て通過
4. **セキュリティ**: Bandit脆弱性チェック通過
5. **パフォーマンス**: 指定要件（例：500ms以下）充足

#### **失敗時の対応フロー**
```python
if quality_gate_failed():
    # 1. 要件再確認
    re_analyze_requirements()
    
    # 2. 実装ギャップ分析
    gap_analysis = identify_missing_features()
    
    # 3. 修正計画策定
    create_fix_plan(gap_analysis)
    
    # 4. 再実装・再テスト
    implement_fixes()
    re_run_quality_checks()
```

### 防止策の継続改善

#### **定期的なプロセス見直し**
- 月次でのワークフロー効果性レビュー
- 見落とし事例の原因分析・対策策定
- Claude Code使用パターンの最適化

#### **チーム学習の促進**
- 要件見落とし事例の共有
- 効果的なClaude Code活用パターンの文書化
- 品質向上のベストプラクティス蓄積

このワークフローにより、チケット要件の見落としやPR品質問題を大幅に削減し、Claude Codeを活用した高品質な開発を実現します。