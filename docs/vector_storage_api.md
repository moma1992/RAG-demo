# VectorStorage API ドキュメント

## 概要

`VectorStorage`クラスは、Supabase + pgvectorを使用したベクトルデータベースへの効率的なチャンク保存・管理機能を提供します。Issue #36の実装として、TDDサイクルで開発されました。

## 主要機能

- **バッチチャンク保存・更新・削除**
- **埋め込みベクトル管理**
- **重複チェック機能**
- **部分的失敗に対応したエラーハンドリング**
- **パフォーマンス統計情報**

## クラス構造

### ChunkData

文書チャンクデータの不変オブジェクト。

```python
@dataclass(frozen=True)
class ChunkData:
    id: str                              # チャンクの一意識別子（UUID）
    document_id: str                     # 親文書のID（UUID）
    content: str                         # チャンクのテキストコンテンツ
    filename: str                        # 元ファイル名
    page_number: int                     # ページ番号（1以上）
    chapter_number: Optional[int]        # 章番号（任意）
    section_name: Optional[str]          # セクション名（任意）
    start_pos: Optional[Dict[str, float]] # 開始座標 {"x": float, "y": float}
    end_pos: Optional[Dict[str, float]]   # 終了座標 {"x": float, "y": float}
    embedding: List[float]               # 1536次元の埋め込みベクトル
    token_count: int                     # トークン数（1以上）
    created_at: datetime                 # 作成日時（自動設定）
```

#### バリデーション

- **UUID形式**: `id`と`document_id`は有効なUUID形式である必要があります
- **コンテンツ制限**: `content`は1-10000文字の範囲
- **埋め込みベクトル**: 1536次元、数値のみ、NaN・無限大値禁止
- **座標データ**: x,yキーを含む辞書形式
- **ベクトルノルム**: ゼロベクトル・異常に大きなベクトル禁止

#### メソッド

```python
def validate(self) -> None:
    """チャンクデータの包括的検証"""

def to_dict(self) -> Dict[str, Any]:
    """辞書形式に変換（データベース挿入用）"""
```

### BatchResult

バッチ処理結果を表すデータクラス。

```python
@dataclass
class BatchResult:
    success_count: int       # 成功件数
    failure_count: int       # 失敗件数
    total_count: int         # 総件数
    failed_ids: List[str]    # 失敗したチャンクIDリスト
    errors: List[str]        # エラーメッセージリスト
```

#### プロパティ

```python
@property
def success_rate(self) -> float:
    """成功率（0.0-1.0）"""

@property
def is_complete_success(self) -> bool:
    """全件成功かどうか"""

@property
def is_complete_failure(self) -> bool:
    """全件失敗かどうか"""
```

### VectorStorage

ベクトルストレージの主要操作クラス。

```python
class VectorStorage:
    def __init__(
        self,
        supabase_url: str,
        supabase_key: str,
        batch_size: int = 100
    ) -> None:
```

## API リファレンス

### チャンクデータ操作

#### save_chunks_batch

```python
def save_chunks_batch(self, chunks: List[ChunkData]) -> BatchResult:
    """
    チャンクデータをバッチで保存
    
    大容量データの効率的な処理のため、指定されたバッチサイズで
    分割して処理し、部分的な失敗があっても継続します。
    
    Args:
        chunks: 保存するチャンクデータのリスト
        
    Returns:
        BatchResult: バッチ処理結果
        
    Raises:
        VectorStorageError: 致命的な保存エラーの場合
    """
```

#### update_embeddings_batch

```python
def update_embeddings_batch(
    self,
    updates: List[Dict[str, Any]]
) -> BatchResult:
    """
    埋め込みベクトルをバッチで更新
    
    Args:
        updates: 更新データのリスト [{"id": str, "embedding": List[float]}, ...]
        
    Returns:
        BatchResult: バッチ処理結果
    """
```

#### delete_chunks_batch

```python
def delete_chunks_batch(self, chunk_ids: List[str]) -> BatchResult:
    """
    チャンクをバッチで削除
    
    Args:
        chunk_ids: 削除対象のチャンクIDリスト
        
    Returns:
        BatchResult: バッチ処理結果
    """
```

### ユーティリティ機能

#### check_duplicates

```python
def check_duplicates(self, chunk_ids: List[str]) -> List[str]:
    """
    重複チャンクIDをチェック
    
    Args:
        chunk_ids: チェック対象のチャンクIDリスト
        
    Returns:
        List[str]: 既存のチャンクIDリスト
    """
```

#### get_storage_stats

```python
def get_storage_stats(self) -> Dict[str, Any]:
    """
    ストレージ統計情報を取得
    
    Returns:
        Dict[str, Any]: 統計情報
        {
            "total_chunks": int,
            "total_documents": int,
            "avg_chunks_per_document": float,
            "batch_size": int,
            "timestamp": str
        }
    """
```

## 使用例

### 基本的な使用方法

```python
from services.vector_storage import VectorStorage, ChunkData
import uuid

# VectorStorageの初期化
storage = VectorStorage(
    supabase_url="https://your-project.supabase.co",
    supabase_key="your-anon-key",
    batch_size=100
)

# チャンクデータの作成
chunks = [
    ChunkData(
        id=str(uuid.uuid4()),
        document_id=str(uuid.uuid4()),
        content="サンプルコンテンツ",
        filename="sample.pdf",
        page_number=1,
        chapter_number=1,
        section_name="はじめに",
        start_pos={"x": 0, "y": 0},
        end_pos={"x": 100, "y": 20},
        embedding=[0.1] * 1536,
        token_count=15
    )
]

# バッチ保存
result = storage.save_chunks_batch(chunks)
print(f"保存結果: 成功{result.success_count}件, 失敗{result.failure_count}件")
```

### 大容量データの処理

```python
# 1000件のチャンクを効率的に処理
large_chunks = create_large_chunk_list(1000)  # ユーザー定義関数

# バッチサイズ100で自動分割処理
result = storage.save_chunks_batch(large_chunks)

if result.is_complete_success:
    print("全件保存成功")
else:
    print(f"部分的成功: {result.success_rate:.2%}")
    for error in result.errors:
        print(f"エラー: {error}")
```

### 埋め込みベクトルの更新

```python
# 既存チャンクの埋め込みベクトルを更新
updates = [
    {"id": "chunk-id-1", "embedding": [0.2] * 1536},
    {"id": "chunk-id-2", "embedding": [0.3] * 1536}
]

update_result = storage.update_embeddings_batch(updates)
print(f"更新完了: {update_result.success_count}件")
```

### 重複チェックと削除

```python
# 重複チェック
chunk_ids = ["id1", "id2", "id3"]
existing_ids = storage.check_duplicates(chunk_ids)
print(f"既存チャンク: {len(existing_ids)}件")

# 不要なチャンクを削除
delete_result = storage.delete_chunks_batch(existing_ids)
print(f"削除完了: {delete_result.success_count}件")
```

## エラーハンドリング

### VectorStorageError

すべてのVectorStorage関連のエラーは`VectorStorageError`として発生します。

```python
from services.vector_storage import VectorStorageError

try:
    result = storage.save_chunks_batch(invalid_chunks)
except VectorStorageError as e:
    print(f"ベクトルストレージエラー: {e}")
    # 適切なエラー処理
```

### 部分的失敗の処理

```python
result = storage.save_chunks_batch(mixed_chunks)

if not result.is_complete_success:
    print(f"部分的失敗: {result.failure_count}件")
    
    # 失敗したチャンクの詳細
    for i, error in enumerate(result.errors):
        failed_id = result.failed_ids[i] if i < len(result.failed_ids) else "unknown"
        print(f"失敗ID {failed_id}: {error}")
    
    # 成功したデータは既に保存済み
    print(f"成功分: {result.success_count}件は正常に保存されました")
```

## パフォーマンス考慮事項

### バッチサイズの最適化

- **小さなバッチ（50-100）**: レスポンスが早く、メモリ使用量が少ない
- **大きなバッチ（200-500）**: スループットが高いが、メモリ使用量が多い
- **推奨**: 100-200件で開始し、環境に応じて調整

### メモリ使用量

- **1チャンク**: 約6KB（1536次元ベクトル + メタデータ）
- **バッチサイズ100**: 約600KB
- **バッチサイズ500**: 約3MB

### パフォーマンス目標

- **小規模バッチ（<100件）**: 1-2秒以内
- **中規模バッチ（100-500件）**: 5-10秒以内
- **大規模バッチ（500-1000件）**: 15-30秒以内
- **スループット**: 最低10件/秒

## テスト

### ユニットテスト

```bash
# 基本機能のテスト
pytest tests/unit/test_vector_storage.py -v

# パフォーマンステスト
pytest tests/unit/test_vector_storage.py::TestVectorStoragePerformance -v
```

### 統合テスト

```bash
# 環境変数を設定
export RUN_INTEGRATION_TESTS=true
export SUPABASE_URL=your_supabase_url
export SUPABASE_ANON_KEY=your_supabase_anon_key

# 統合テスト実行
pytest tests/integration/test_vector_storage_integration.py -v

# パフォーマンステスト
pytest tests/integration/test_vector_storage_integration.py -v -m slow
```

## 開発・保守

### TDDサイクル

1. **Red**: 失敗テストを書く
2. **Green**: 最小限の実装でテストを通す
3. **Refactor**: コード品質を向上させる

### コード品質基準

- **型ヒント**: すべての関数・メソッドに必須
- **ドキュメント**: docstringによる詳細説明
- **テストカバレッジ**: 90%以上
- **エラーハンドリング**: 適切な例外処理とログ出力

### 今後の拡張予定

- **並列処理**: asyncio対応
- **キャッシュ機能**: Redis統合
- **メトリクス**: Prometheus対応
- **バックアップ**: 自動バックアップ機能