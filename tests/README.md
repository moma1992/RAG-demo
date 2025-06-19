# テストディレクトリ構造

新入社員向け社内文書検索RAGアプリケーションのテストスイート

## 📁 ディレクトリ構造

```
tests/
├── __init__.py
├── conftest.py              # 共通フィクスチャ・モック設定
├── README.md                # このファイル
├── unit/                    # 単体テスト
│   ├── __init__.py
│   ├── test_pdf_processor.py      # PDF処理の単体テスト
│   ├── test_vector_store.py       # ベクトルストアの単体テスト
│   ├── test_embeddings.py         # 埋め込み生成の単体テスト
│   └── test_claude_llm.py         # Claude LLMの単体テスト
├── integration/             # 統合テスト
│   ├── __init__.py
│   ├── test_full_pipeline.py      # 完全パイプライン統合テスト
│   └── test_api_integration.py    # 外部API統合テスト
├── performance/             # パフォーマンステスト
│   ├── __init__.py
│   └── test_load_performance.py   # 負荷・性能テスト
├── fixtures/                # テストデータ・フィクスチャ
│   ├── __init__.py
│   ├── sample_data.py             # サンプルテストデータ
│   ├── sample_pdfs/               # テスト用PDFファイル
│   └── mock_responses/            # モックAPIレスポンス
└── utils/                   # テストユーティリティ
    ├── __init__.py
    └── test_helpers.py            # テスト用ヘルパー関数
```

## 🧪 テストカテゴリ

### 単体テスト (Unit Tests)
個別のモジュール・クラス・関数の動作を検証

- **PDF処理**: PyMuPDF統合、テキスト抽出、チャンク分割
- **ベクトルストア**: Supabase操作、検索機能、データ管理
- **埋め込み生成**: OpenAI API統合、ベクトル生成
- **Claude LLM**: Claude API統合、回答生成

### 統合テスト (Integration Tests)
複数コンポーネント間の連携を検証

- **完全パイプライン**: PDF処理→埋め込み生成→ベクトル保存→検索→回答生成
- **外部API統合**: OpenAI、Claude、Supabase APIとの統合

### パフォーマンステスト (Performance Tests)
システムの性能とスケーラビリティを検証

- **負荷テスト**: 大量データ処理、同時アクセス
- **性能測定**: 応答時間、スループット、メモリ使用量
- **スケーラビリティ**: データ量増加時の性能変化

## 🛠️ テスト実行方法

### 全テスト実行
```bash
pytest tests/
```

### カテゴリ別実行
```bash
# 単体テスト
pytest tests/unit/

# 統合テスト
pytest tests/integration/

# パフォーマンステスト
pytest tests/performance/
```

### 特定テストファイル実行
```bash
pytest tests/unit/test_pdf_processor.py
```

### カバレッジ付き実行
```bash
pytest tests/ --cov=. --cov-report=html
```

### 詳細実行
```bash
pytest tests/ -v --tb=short
```

## 🎭 モック・フィクスチャ

### 外部API自動モック
`conftest.py`で全外部API呼び出しを自動モック化:

- **OpenAI API**: 埋め込み生成レスポンス
- **Claude API**: テキスト生成レスポンス  
- **Supabase API**: データベース操作レスポンス

### 共通フィクスチャ
- `sample_pdf_bytes`: テスト用PDFバイトデータ
- `temp_dir`: 一時ディレクトリ
- `test_config`: テスト用設定
- `mock_streamlit_session`: Streamlitセッション状態

## 📊 テストデータ

### サンプルデータ
`fixtures/sample_data.py`に定義:

- **PDF texts**: 日本語テキストサンプル
- **チャンクデータ**: 文書チャンクサンプル
- **検索結果**: 検索結果サンプル
- **Q&Aペア**: 質問・回答サンプル

### エラーケース
- 無効PDFファイル
- 空ファイル
- 破損データ
- 大容量ファイル

## 🔧 テストユーティリティ

### ヘルパークラス
`utils/test_helpers.py`で提供:

- **MockPDFGenerator**: テスト用PDF生成
- **MockDataFactory**: テストデータファクトリー
- **TestFileManager**: 一時ファイル管理
- **AssertionHelpers**: カスタムアサーション

### カスタムアサーション
```python
# UUID形式検証
AssertionHelpers.assert_valid_uuid(uuid_string)

# 埋め込みベクトル検証
AssertionHelpers.assert_valid_embedding(embedding)

# 日本語テキスト検証
AssertionHelpers.assert_japanese_text(text)

# 処理時間検証
AssertionHelpers.assert_processing_time_reasonable(time)
```

## 🚀 CI/CD統合

### GitHub Actions
`.github/workflows/ci.yml`でテスト自動実行:

1. **コード品質チェック**
   - flake8 (リンティング)
   - black (フォーマット)
   - mypy (型チェック)
   - bandit (セキュリティ)

2. **テスト実行**
   - 単体テスト
   - 統合テスト
   - カバレッジ測定

3. **パフォーマンス監視**
   - 応答時間監視
   - メモリ使用量チェック

### 品質ゲート
- テストカバレッジ ≥ 90%
- 単体テスト実行時間 < 30秒
- 統合テスト実行時間 < 2分

## 📝 テスト作成ガイドライン

### TDD原則
1. **Red**: 失敗するテストを先に作成
2. **Green**: 最小実装でテストを通す
3. **Refactor**: コードを改善・リファクタリング

### 命名規則
- テストクラス: `Test{ClassName}`
- テストメソッド: `test_{what_it_tests}`
- フィクスチャ: `{description}_{type}`

### テスト構造
```python
def test_method_name(self, fixtures):
    """テストの説明"""
    # Arrange: テストデータ準備
    
    # Act: テスト対象実行
    
    # Assert: 結果検証
```

### 日本語対応
- エラーメッセージは日本語
- テストデータに日本語文字列使用
- 日本語境界処理テスト実装

## 🛡️ セキュリティテスト

### 入力検証
- SQLインジェクション対策
- XSS対策
- ファイルアップロード制限

### データ保護
- 機密情報マスキング
- ログ出力制限
- API キー保護

## 📈 パフォーマンス要件

### 応答時間目標
- PDF処理: < 30秒
- ベクトル検索: < 2秒
- 回答生成: < 10秒

### リソース制限
- メモリ使用量: < 1GB (Streamlit Cloud制約)
- ディスク使用量: < 1GB
- CPU使用率: < 80%

---

## 🔗 関連ドキュメント

- [CLAUDE.md](../CLAUDE.md): プロジェクト全体概要
- [DEVELOPMENT.md](../DEVELOPMENT.md): 開発ガイドライン
- [requirements-dev.txt](../requirements-dev.txt): 開発依存関係