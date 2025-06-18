#!/bin/bash

# Epic to Feature Issues Generator Script
# Usage: ./create-features.sh <epic_number> <epic_title>

set -e

EPIC_NUMBER=$1
EPIC_TITLE=$2

if [ -z "$EPIC_NUMBER" ] || [ -z "$GITHUB_TOKEN" ]; then
    echo "Error: EPIC_NUMBER and GITHUB_TOKEN are required"
    exit 1
fi

echo "🚀 Creating Feature Issues from Epic #$EPIC_NUMBER..."

# Epic #2: CI/CD環境とプロジェクト基盤整備
if [ "$EPIC_NUMBER" = "2" ]; then
    echo "📋 Creating CI/CD Epic Features..."
    
    # CI/CDパイプライン設定
    ISSUE1=$(gh issue create \
        --title "[FEAT] CI/CDパイプライン設定" \
        --assignee "@me" \
        --body-file <(cat << 'EOF'
## 🎯 背景・目的
RAGアプリケーション開発のためのGitHub Actions CI/CDパイプラインを設定し、自動化されたテスト・品質チェック・デプロイメント環境を構築する。

## 📋 要件
### 機能要件
- [ ] GitHub Actions ワークフロー設定 (.github/workflows/ci.yml)
- [ ] Python 3.11環境でのテスト実行
- [ ] 複数ジョブでの並列処理 (test, security, quality)
- [ ] プルリクエスト・プッシュ時の自動実行
- [ ] テスト結果とカバレッジの可視化

### 非機能要件
- [ ] 実行時間5分以内での完了
- [ ] 依存関係キャッシュによる高速化
- [ ] セキュリティスキャンの統合
- [ ] 失敗時の適切なエラー通知

## 🏗️ 技術仕様
- **使用技術**: GitHub Actions, pytest, flake8, black, mypy, bandit
- **トリガー**: push (main, develop), pull_request (main)
- **Python版**: 3.11.x (Streamlit Cloud Community対応)

```yaml
# 想定するワークフロー構造
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
    # テスト実行・カバレッジ測定
  
  quality:
    # コード品質チェック (Black, Flake8, mypy)
    
  security:
    # セキュリティスキャン (Bandit, Safety)
```

## 🎪 成功基準
- [ ] CI/CDパイプラインが正常動作
- [ ] 全品質チェック項目がPass
- [ ] テストカバレッジレポート自動生成
- [ ] PRマージ前の自動品質ゲート機能
- [ ] 失敗時の分かりやすいフィードバック

## 🧪 テストケース
### 正常系
- [ ] 正常なコードでのCI実行成功確認
- [ ] 依存関係キャッシュ機能の動作確認
- [ ] 並列ジョブ実行の確認
- [ ] アーティファクト生成確認

### 異常系
- [ ] テスト失敗時のワークフロー適切停止
- [ ] セキュリティ問題検出時の処理確認
- [ ] 品質チェック失敗時の詳細レポート
- [ ] タイムアウト処理の確認

## 🔗 関連Issue
- Part of Epic: #2 - CI/CD環境とプロジェクト基盤整備
- Blocks: 他の全Feature Issues (CI/CDが前提)

## 💡 実装メモ
- CLAUDE.mdのCI/CD設定を参考に実装
- 外部サービスAPIキーはmock値で設定
- Codecov連携でカバレッジ可視化

---
**Claude Code Action使用**: ✅ TDDサイクルでライブコーディング実装予定
**想定工数**: 4-6時間
EOF
))
    
    echo "✅ Created Issue: $ISSUE1"
    
    # プロジェクト基本構造構築
    ISSUE2=$(gh issue create \
        --title "[FEAT] プロジェクト基本構造構築" \
        --assignee "@me" \
        --body-file <(cat << 'EOF'
## 🎯 背景・目的
RAGアプリケーションの基本ディレクトリ構造を構築し、Streamlit Cloud Community対応の設定ファイルを整備する。

## 📋 要件
### 機能要件
- [ ] アプリケーションディレクトリ構造作成
- [ ] 設定ファイル群の配置 (pyproject.toml, .env.example等)
- [ ] テストディレクトリ構造整備
- [ ] ドキュメント基盤構築
- [ ] Streamlit設定ファイル作成

### 非機能要件
- [ ] 拡張性を考慮した構造設計
- [ ] チーム開発に適した整理
- [ ] Streamlit Cloud Community制約対応

## 🏗️ 技術仕様
```
# 構築予定ディレクトリ構造
RAG-demo/
├── streamlit_app.py              # メインアプリケーション
├── components/
│   ├── __init__.py
│   ├── pdf_uploader.py          # PDF アップロード UI
│   ├── chat_interface.py        # チャット UI
│   └── document_manager.py      # 文書管理 UI
├── services/
│   ├── __init__.py
│   ├── pdf_processor.py         # PyMuPDF + spaCy 処理
│   ├── text_chunker.py          # 意味的チャンク分割
│   ├── vector_store.py          # Supabase Vector操作
│   ├── embeddings.py            # OpenAI Embeddings
│   └── claude_llm.py            # Claude API統合
├── utils/
│   ├── __init__.py
│   ├── config.py               # 設定管理
│   └── error_handler.py        # エラーハンドリング
├── models/
│   ├── __init__.py
│   ├── document.py             # 文書データモデル
│   └── chat.py                 # チャットデータモデル
├── tests/
│   ├── __init__.py
│   ├── conftest.py             # テスト共通設定
│   ├── fixtures/               # テストデータ
│   ├── unit/                   # 単体テスト
│   └── integration/            # 統合テスト
├── docs/
│   └── README.md
├── .streamlit/
│   └── config.toml             # Streamlit設定
├── .env.example                # 環境変数テンプレート
├── pyproject.toml              # プロジェクト設定
└── pytest.ini                 # pytest設定
```

## 🎪 成功基準
- [ ] 完全なディレクトリ構造作成
- [ ] 設定ファイル群の動作確認
- [ ] streamlit run での基本起動確認
- [ ] 開発環境セットアップガイド完成

## 🧪 テストケース
### 正常系
- [ ] ディレクトリ構造の正確性確認
- [ ] 設定ファイル読み込み確認
- [ ] 基本的なimport動作確認
- [ ] Streamlit起動確認

### 異常系
- [ ] 不正な設定ファイル処理
- [ ] 不足ディレクトリの自動作成
- [ ] 権限エラー処理

## 🔗 関連Issue
- Part of Epic: #2 - CI/CD環境とプロジェクト基盤整備
- Depends on: None (最初に実装)
- Blocks: 依存関係設定、テストフレームワーク

---
**Claude Code Action使用**: ✅ ライブコーディング実装予定
**想定工数**: 2-3時間
EOF
))
    
    echo "✅ Created Issue: $ISSUE2"
    
    # 依存関係とコード品質設定
    ISSUE3=$(gh issue create \
        --title "[FEAT] 依存関係とコード品質設定" \
        --body-file <(cat << 'EOF'
## 🎯 背景・目的
プロジェクトの依存関係管理とコード品質保証ツールを設定し、一貫した開発標準を確立する。

## 📋 要件
### 機能要件
- [ ] requirements.txt (本番依存関係)
- [ ] requirements-dev.txt (開発依存関係)
- [ ] pyproject.toml設定 (品質ツール設定含む)
- [ ] コード品質ツール設定 (Black, Flake8, mypy)
- [ ] Pre-commit hooks設定

### 非機能要件
- [ ] 依存関係の最小化とセキュリティ
- [ ] バージョン固定による再現性確保
- [ ] Streamlit Cloud Community対応

## 🏗️ 技術仕様
```python
# requirements.txt (主要依存関係)
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

# requirements-dev.txt (開発依存関係)  
pytest>=7.4.0
pytest-cov>=4.1.0
pytest-mock>=3.11.0
black>=23.7.0
flake8>=6.0.0
mypy>=1.5.0
bandit>=1.7.5
pre-commit>=3.3.0
```

## 🎪 成功基準
- [ ] 依存関係インストール成功
- [ ] コード品質チェック動作確認
- [ ] Pre-commit hooks正常機能
- [ ] CI/CD統合確認

## 🧪 テストケース
### 正常系
- [ ] 依存関係解決・インストール確認
- [ ] 品質チェック実行確認
- [ ] Pre-commit動作確認
- [ ] 型チェック実行確認

### 異常系
- [ ] 依存関係競合エラー処理
- [ ] 品質チェック失敗時の対応
- [ ] 古いPythonバージョンでの警告

## 🔗 関連Issue
- Part of Epic: #2 - CI/CD環境とプロジェクト基盤整備
- Depends on: プロジェクト基本構造構築

---
**Claude Code Action使用**: ✅ ライブコーディング実装予定
EOF
))
    
    echo "✅ Created Issue: $ISSUE3"
    
    # 残りのFeature Issuesも同様に作成...
    echo "📝 Epic #2 のFeature Issues作成完了"
    
elif [ "$EPIC_NUMBER" = "3" ]; then
    echo "📋 Creating RAG Implementation Epic Features..."
    # Epic #3用のFeature Issues作成
    echo "📝 Epic #3 のFeature Issues作成は別途実装"
    
else
    echo "⚠️  Unknown Epic number: $EPIC_NUMBER"
    exit 1
fi

echo "🎉 Feature Issues creation completed for Epic #$EPIC_NUMBER"