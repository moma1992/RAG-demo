"""
ベクトルストアサービス

Supabase + pgvectorを使用したベクトル検索機能
"""

from typing import List, Dict, Any, Optional
import logging
from dataclasses import dataclass
import uuid
import math
import asyncio
import time
from functools import wraps
from typing import Union
import weakref

logger = logging.getLogger(__name__)

# セキュリティ関連の定数
EMBEDDING_DIMENSION = 1536
MAX_EMBEDDING_VALUE = 1000.0
MAX_CONTENT_LENGTH = 10000
MAX_SEARCH_LIMIT = 100
MAX_FILENAME_LENGTH = 255

# 接続プール設定
DEFAULT_POOL_SIZE = 10
MAX_POOL_SIZE = 20
CONNECTION_TIMEOUT = 30.0
RETRY_ATTEMPTS = 3
RETRY_DELAY = 1.0


def async_retry(max_attempts: int = RETRY_ATTEMPTS, delay: float = RETRY_DELAY):
    """
    非同期操作用リトライデコレータ
    
    Args:
        max_attempts: 最大試行回数
        delay: 初期遅延時間（秒）
    """
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            last_exception = None
            
            for attempt in range(max_attempts):
                try:
                    return await func(*args, **kwargs)
                except Exception as e:
                    last_exception = e
                    
                    if attempt < max_attempts - 1:
                        # 指数バックオフ
                        sleep_time = delay * (2 ** attempt)
                        logger.warning(
                            f"リトライ {attempt + 1}/{max_attempts}: {str(e)} "
                            f"({sleep_time}秒後に再試行)"
                        )
                        await asyncio.sleep(sleep_time)
                    else:
                        logger.error(f"最大試行回数に達しました: {str(e)}")
            
            raise last_exception
        
        return wrapper
    return decorator


def sync_retry(max_attempts: int = RETRY_ATTEMPTS, delay: float = RETRY_DELAY):
    """
    同期操作用リトライデコレータ
    
    Args:
        max_attempts: 最大試行回数
        delay: 初期遅延時間（秒）
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            last_exception = None
            
            for attempt in range(max_attempts):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    last_exception = e
                    
                    if attempt < max_attempts - 1:
                        # 指数バックオフ
                        sleep_time = delay * (2 ** attempt)
                        logger.warning(
                            f"同期リトライ {attempt + 1}/{max_attempts}: {str(e)} "
                            f"({sleep_time}秒後に再試行)"
                        )
                        time.sleep(sleep_time)
                    else:
                        logger.error(f"同期操作最大試行回数に達しました: {str(e)}")
            
            raise last_exception
        
        return wrapper
    return decorator


class SupabaseConnectionPool:
    """
    Supabase接続プール管理クラス
    複数の接続を効率的に管理し、コネクション再利用によるパフォーマンス向上
    """
    
    def __init__(self, supabase_url: str, supabase_key: str, pool_size: int = DEFAULT_POOL_SIZE):
        """
        接続プール初期化
        
        Args:
            supabase_url: Supabase URL
            supabase_key: Supabase APIキー
            pool_size: プールサイズ
        """
        self.supabase_url = supabase_url
        self.supabase_key = supabase_key
        self.pool_size = min(pool_size, MAX_POOL_SIZE)
        
        # 接続プール（弱参照を使用してメモリリークを防止）
        self._connections: List[Union[object, None]] = [None] * self.pool_size
        self._async_connections: List[Union[object, None]] = [None] * self.pool_size
        self._available_indices = asyncio.Queue(maxsize=self.pool_size)
        
        # プール初期化（インデックスをキューに追加）
        for i in range(self.pool_size):
            self._available_indices.put_nowait(i)
            
        self._lock = asyncio.Lock()
        logger.info(f"接続プール初期化完了: pool_size={self.pool_size}")
    
    async def get_connection(self, async_mode: bool = False) -> tuple[object, int]:
        """
        接続プールから接続を取得
        
        Args:
            async_mode: 非同期クライアントを取得するか
            
        Returns:
            tuple[object, int]: (クライアント, インデックス)
            
        Raises:
            VectorStoreError: 接続取得エラーの場合
        """
        try:
            # 利用可能な接続インデックスを取得（タイムアウト付き）
            index = await asyncio.wait_for(
                self._available_indices.get(), 
                timeout=CONNECTION_TIMEOUT
            )
            
            async with self._lock:
                # 接続が存在しない場合は新規作成
                if async_mode:
                    if self._async_connections[index] is None:
                        self._async_connections[index] = self._create_async_client()
                    client = self._async_connections[index]
                else:
                    if self._connections[index] is None:
                        self._connections[index] = self._create_sync_client()
                    client = self._connections[index]
                
                logger.debug(f"接続取得: index={index}, async={async_mode}")
                return client, index
                
        except asyncio.TimeoutError:
            raise VectorStoreError("接続プール接続取得タイムアウト")
        except Exception as e:
            raise VectorStoreError(f"接続プール接続取得エラー: {str(e)}") from e
    
    async def release_connection(self, index: int) -> None:
        """
        接続をプールに戻す
        
        Args:
            index: 接続インデックス
        """
        try:
            await self._available_indices.put(index)
            logger.debug(f"接続返却: index={index}")
        except Exception as e:
            logger.error(f"接続返却エラー: {str(e)}")
    
    def _create_sync_client(self) -> object:
        """同期Supabaseクライアント作成"""
        try:
            from supabase import create_client
            return create_client(self.supabase_url, self.supabase_key)
        except ImportError:
            return None
    
    def _create_async_client(self) -> object:
        """非同期Supabaseクライアント作成"""
        try:
            from supabase._async.client import create_client as create_async_client
            return create_async_client(self.supabase_url, self.supabase_key)
        except ImportError:
            return None
    
    async def health_check(self) -> Dict[str, Any]:
        """
        接続プール健全性チェック
        
        Returns:
            Dict[str, Any]: 健全性情報
        """
        return {
            "pool_size": self.pool_size,
            "available_connections": self._available_indices.qsize(),
            "total_connections": self.pool_size,
            "utilization_rate": 1.0 - (self._available_indices.qsize() / self.pool_size)
        }


def validate_embedding_vector(embedding: List[float]) -> None:
    """
    埋め込みベクトルの入力検証

    Args:
        embedding: 検証対象の埋め込みベクトル

    Raises:
        VectorStoreError: 無効な埋め込みベクトルの場合
    """
    if not embedding:
        raise VectorStoreError("埋め込みベクトルが空です")

    if not isinstance(embedding, list):
        raise VectorStoreError("埋め込みベクトルはリスト形式である必要があります")

    if len(embedding) != EMBEDDING_DIMENSION:
        raise VectorStoreError(
            f"埋め込みベクトルは{EMBEDDING_DIMENSION}次元である必要があります。現在: {len(embedding)}次元"
        )

    for i, value in enumerate(embedding):
        if not isinstance(value, (int, float)):
            raise VectorStoreError(
                f"インデックス {i} の値が数値ではありません: {type(value)}"
            )

        if math.isnan(value):
            raise VectorStoreError(f"インデックス {i} にNaN値が含まれています")

        if math.isinf(value):
            raise VectorStoreError(f"インデックス {i} に無限大値が含まれています")

        # セキュリティ: 異常に大きな値の検出
        if abs(value) > MAX_EMBEDDING_VALUE:
            raise VectorStoreError(f"インデックス {i} の値が異常に大きいです: {value}")


def validate_search_parameters(k: int, similarity_threshold: float) -> None:
    """
    検索パラメータの入力検証

    Args:
        k: 返す結果数
        similarity_threshold: 類似度閾値

    Raises:
        VectorStoreError: 無効なパラメータの場合
    """
    if not isinstance(k, int) or k <= 0:
        raise VectorStoreError(f"k は正の整数である必要があります: {k}")

    if k > MAX_SEARCH_LIMIT:
        raise VectorStoreError(f"k は{MAX_SEARCH_LIMIT}以下である必要があります: {k}")

    if not isinstance(similarity_threshold, (int, float)):
        raise VectorStoreError(
            f"similarity_threshold は数値である必要があります: {type(similarity_threshold)}"
        )

    if similarity_threshold < 0.0 or similarity_threshold > 1.0:
        raise VectorStoreError(
            f"similarity_threshold は0.0-1.0の範囲である必要があります: {similarity_threshold}"
        )


def validate_chunk_data(chunk: Dict[str, Any]) -> None:
    """
    チャンクデータの入力検証

    Args:
        chunk: 検証対象のチャンクデータ

    Raises:
        VectorStoreError: 無効なチャンクデータの場合
    """
    required_fields = ["content", "filename"]
    for field in required_fields:
        if field not in chunk:
            raise VectorStoreError(f"必須フィールド '{field}' が不足しています")

    content = chunk.get("content", "")
    if not isinstance(content, str):
        raise VectorStoreError("contentは文字列である必要があります")

    if len(content.strip()) == 0:
        raise VectorStoreError("contentは空でない文字列である必要があります")

    if len(content) > MAX_CONTENT_LENGTH:
        raise VectorStoreError(
            f"contentが長すぎます: {len(content)} 文字 (最大{MAX_CONTENT_LENGTH}文字)"
        )

    filename = chunk.get("filename", "")
    if not isinstance(filename, str):
        raise VectorStoreError("filenameは文字列である必要があります")

    if len(filename.strip()) == 0:
        raise VectorStoreError("filenameは空でない文字列である必要があります")

    if len(filename) > MAX_FILENAME_LENGTH:
        raise VectorStoreError(
            f"ファイル名が長すぎます: {len(filename)} 文字 (最大{MAX_FILENAME_LENGTH}文字)"
        )

    # オプショナルフィールドの検証
    page_number = chunk.get("page_number")
    if page_number is not None and (
        not isinstance(page_number, int) or page_number <= 0
    ):
        raise VectorStoreError(
            f"page_numberは正の整数である必要があります: {page_number}"
        )

    chapter_number = chunk.get("chapter_number")
    if chapter_number is not None and (
        not isinstance(chapter_number, int) or chapter_number <= 0
    ):
        raise VectorStoreError(
            f"chapter_numberは正の整数である必要があります: {chapter_number}"
        )

    token_count = chunk.get("token_count")
    if token_count is not None and (
        not isinstance(token_count, int) or token_count <= 0
    ):
        raise VectorStoreError(
            f"token_countは正の整数である必要があります: {token_count}"
        )

    # 埋め込みベクトルの検証
    embedding = chunk.get("embedding")
    if embedding is not None:
        validate_embedding_vector(embedding)


@dataclass
class SearchResult:
    """検索結果データクラス"""

    content: str
    filename: str
    page_number: int
    similarity_score: float
    metadata: Dict[str, Any]


@dataclass
class DocumentRecord:
    """文書レコード"""

    id: str
    filename: str
    original_filename: str
    upload_date: str
    file_size: int
    total_pages: int
    processing_status: str


class VectorStore:
    """ベクトルストアクラス - 高度な接続プール対応"""

    def __init__(
        self, 
        supabase_url: str, 
        supabase_key: str, 
        pool_size: int = DEFAULT_POOL_SIZE,
        enable_async: bool = True
    ) -> None:
        """
        初期化

        Args:
            supabase_url: Supabase URL
            supabase_key: Supabase APIキー
            pool_size: 接続プールサイズ
            enable_async: 非同期モード有効化
        """
        self.supabase_url = supabase_url
        self.supabase_key = supabase_key
        self.pool_size = min(pool_size, MAX_POOL_SIZE)
        self.enable_async = enable_async
        
        # 接続プール管理（新しい実装）
        self._connection_pool = SupabaseConnectionPool(
            supabase_url, supabase_key, self.pool_size
        )
        
        # 後方互換性のための旧セマフォ（段階的移行）
        self._connection_semaphore = asyncio.Semaphore(self.pool_size)
        
        # メトリクス
        self._search_metrics = {
            "total_searches": 0,
            "total_time": 0.0,
            "avg_response_time": 0.0,
            "last_search_time": None
        }

        # 後方互換性のためのフォールバッククライアント
        try:
            from supabase import create_client

            self.client = create_client(supabase_url, supabase_key)
            
            # 非同期クライアントの初期化も試行
            if enable_async:
                try:
                    from supabase._async.client import create_client as create_async_client
                    self.async_client = create_async_client(supabase_url, supabase_key)
                except ImportError:
                    self.async_client = None
                    logger.warning("非同期Supabaseクライアントが利用できません")
            else:
                self.async_client = None
                
        except ImportError:
            self.client = None  # type: ignore
            self.async_client = None

        logger.info(f"VectorStore初期化完了: pool_size={self.pool_size}, async={enable_async}")

    @sync_retry(max_attempts=RETRY_ATTEMPTS)
    def store_document(self, document_data: Dict[str, Any], document_id: Optional[str] = None) -> str:
        """
        文書をデータベースに保存

        Args:
            document_data: 文書データ
            document_id: 指定する文書ID（オプション）

        Returns:
            str: 文書ID

        Raises:
            VectorStoreError: データベースエラーの場合
        """
        logger.info(f"文書保存開始: {document_data.get('filename', 'unknown')}")

        try:
            # 提供されたIDを使用、なければ新規生成
            if document_id is None:
                document_id = str(uuid.uuid4())

            # documentsテーブルに挿入
            if self.client:
                self.client.table("documents").insert(
                    {
                        "id": document_id,
                        "filename": document_data.get("filename"),
                        "original_filename": document_data.get(
                            "original_filename", document_data.get("filename")
                        ),
                        "file_size": document_data.get("file_size", 0),
                        "total_pages": document_data.get("total_pages", 0),
                        "processing_status": "processing",
                    }
                ).execute()

            logger.info(f"文書保存完了: {document_id}")
            return document_id

        except Exception as e:
            logger.error(f"文書保存エラー: {str(e)}", exc_info=True)
            raise VectorStoreError(f"文書保存中にエラーが発生しました: {str(e)}") from e

    @sync_retry(max_attempts=RETRY_ATTEMPTS)
    def store_chunks(self, chunks: List[Dict[str, Any]], document_id: str) -> List[str]:
        """
        チャンクをデータベースに保存

        Args:
            chunks: チャンクリスト
            document_id: 文書ID

        Returns:
            List[str]: 保存されたチャンクIDリスト

        Raises:
            VectorStoreError: データベースエラーの場合
        """
        logger.info(f"チャンク保存開始: {len(chunks)}個")

        try:
            if not self.client:
                raise VectorStoreError("Supabaseクライアントが初期化されていません")

            if not chunks:
                raise VectorStoreError("チャンクリストが空です")

            if not isinstance(document_id, str) or not document_id.strip():
                raise VectorStoreError("document_idが無効です")

            # 各チャンクの入力検証
            for i, chunk in enumerate(chunks):
                try:
                    validate_chunk_data(chunk)
                except VectorStoreError as e:
                    raise VectorStoreError(
                        f"チャンク {i} の検証エラー: {str(e)}"
                    ) from e

            # document_chunksテーブルに一括挿入
            chunk_records = []
            for chunk in chunks:
                chunk_record = {
                    "id": str(uuid.uuid4()),
                    "document_id": document_id,
                    "content": chunk.get("content", ""),
                    "filename": chunk.get("filename", ""),
                    "page_number": chunk.get("page_number"),
                    "chapter_number": chunk.get("chapter_number"),
                    "section_name": chunk.get("section_name"),
                    "start_pos": chunk.get("start_pos"),
                    "end_pos": chunk.get("end_pos"),
                    "embedding": chunk.get("embedding"),
                    "token_count": chunk.get("token_count", 0),
                }
                chunk_records.append(chunk_record)

            # バッチ挿入実行
            result = self.client.table("document_chunks").insert(chunk_records).execute()

            # 保存されたチャンクIDを収集
            chunk_ids = [record["id"] for record in chunk_records]

            logger.info(f"チャンク保存完了: {len(chunk_records)}個")
            return chunk_ids

        except Exception as e:
            logger.error(f"チャンク保存エラー: {str(e)}", exc_info=True)
            raise VectorStoreError(
                f"チャンク保存中にエラーが発生しました: {str(e)}"
            ) from e

    @sync_retry(max_attempts=RETRY_ATTEMPTS)
    def similarity_search(
        self,
        query_embedding: List[float],
        k: int = 5,
        similarity_threshold: float = 0.7,
    ) -> List[SearchResult]:
        """
        ベクトル類似検索

        Args:
            query_embedding: クエリのベクトル表現
            k: 返す結果数
            similarity_threshold: 類似度閾値

        Returns:
            List[SearchResult]: 検索結果リスト

        Raises:
            VectorStoreError: 検索エラーの場合
        """
        logger.info(f"類似検索開始: k={k}, threshold={similarity_threshold}")

        try:
            if not self.client:
                raise VectorStoreError("Supabaseクライアントが初期化されていません")

            # 入力検証
            validate_embedding_vector(query_embedding)
            validate_search_parameters(k, similarity_threshold)

            # pgvectorのコサイン距離検索を実行
            # 距離を類似度スコアに変換: similarity = 1 - distance
            max_distance = 1.0 - similarity_threshold

            # RPC関数を使用したベクトル検索
            result = self.client.rpc(
                "match_documents",
                {
                    "query_embedding": query_embedding,
                    "match_threshold": max_distance,
                    "match_count": k,
                },
            ).execute()

            # 結果をSearchResultオブジェクトに変換
            search_results = []
            if result.data:
                for row in result.data:
                    search_result = SearchResult(
                        content=row.get("content", ""),
                        filename=row.get("filename", ""),
                        page_number=row.get("page_number", 0),
                        similarity_score=1.0
                        - row.get("distance", 1.0),  # 距離を類似度に変換
                        metadata={
                            "section_name": row.get("section_name"),
                            "chapter_number": row.get("chapter_number"),
                            "start_pos": row.get("start_pos"),
                            "end_pos": row.get("end_pos"),
                            "token_count": row.get("token_count", 0),
                        },
                    )
                    search_results.append(search_result)

            logger.info(f"類似検索完了: {len(search_results)}件")
            return search_results

        except Exception as e:
            logger.error(f"類似検索エラー: {str(e)}", exc_info=True)
            raise VectorStoreError(f"類似検索中にエラーが発生しました: {str(e)}") from e

    def get_documents(self) -> List[DocumentRecord]:
        """
        登録済み文書一覧を取得

        Returns:
            List[DocumentRecord]: 文書レコードリスト

        Raises:
            VectorStoreError: データベースエラーの場合
        """
        logger.info("文書一覧取得開始")

        try:
            if not self.client:
                raise VectorStoreError("Supabaseクライアントが初期化されていません")

            # documentsテーブルから全件取得
            result = (
                self.client.table("documents")
                .select("*")
                .order("upload_date", desc=True)
                .execute()
            )

            # DocumentRecordオブジェクトに変換
            documents = []
            for row in result.data:
                document = DocumentRecord(
                    id=row.get("id", ""),
                    filename=row.get("filename", ""),
                    original_filename=row.get("original_filename", ""),
                    upload_date=row.get("upload_date", ""),
                    file_size=row.get("file_size", 0),
                    total_pages=row.get("total_pages", 0),
                    processing_status=row.get("processing_status", "unknown"),
                )
                documents.append(document)

            logger.info(f"文書一覧取得完了: {len(documents)}件")
            return documents

        except Exception as e:
            logger.error(f"文書一覧取得エラー: {str(e)}", exc_info=True)
            raise VectorStoreError(
                f"文書一覧取得中にエラーが発生しました: {str(e)}"
            ) from e

    @sync_retry(max_attempts=RETRY_ATTEMPTS)
    def delete_document(self, document_id: str) -> None:
        """
        文書を削除

        Args:
            document_id: 文書ID

        Raises:
            VectorStoreError: データベースエラーの場合
        """
        logger.info(f"文書削除開始: {document_id}")

        try:
            # documentsテーブルから削除（CASCADE削除でchunksも一緒に削除される）
            if self.client:
                self.client.table("documents").delete().eq("id", document_id).execute()

            logger.info(f"文書削除完了: {document_id}")

        except Exception as e:
            logger.error(f"文書削除エラー: {str(e)}", exc_info=True)
            raise VectorStoreError(f"文書削除中にエラーが発生しました: {str(e)}") from e

    @async_retry(max_attempts=RETRY_ATTEMPTS)
    async def bulk_insert_embeddings(
        self, embeddings: List[Any], document_chunks: List[Dict[str, Any]]
    ) -> bool:
        """
        バルク埋め込み保存 - Issue #57 要件実装（接続プール対応）

        Args:
            embeddings: EmbeddingResultリスト
            document_chunks: DocumentChunkリスト

        Returns:
            bool: 保存成功フラグ

        Raises:
            VectorStoreError: バルク保存エラーの場合
        """
        logger.info(
            f"バルク埋め込み保存開始: embeddings={len(embeddings)}, chunks={len(document_chunks)}"
        )

        # 接続プールから接続を取得
        client, connection_index = await self._connection_pool.get_connection(async_mode=True)
        
        try:
            # 接続プールから取得したクライアントを使用（フォールバック付き）
            if not client:
                client = self.async_client if self.async_client else self.client
            
            if not client:
                raise VectorStoreError("Supabaseクライアントが初期化されていません")

            # 入力検証
            if not embeddings or not document_chunks:
                raise VectorStoreError("埋め込みまたはチャンクリストが空です")

            if len(embeddings) != len(document_chunks):
                raise VectorStoreError(
                    f"埋め込み数({len(embeddings)})とチャンク数({len(document_chunks)})が一致しません"
                )

            # 先に文書レコードを作成
            document_id = str(uuid.uuid4())
            
            # documentsテーブルに親レコードを作成
            if hasattr(client, 'table'):
                result = client.table("documents").insert({
                    "id": document_id,
                    "filename": document_chunks[0].get("filename", "bulk_upload.pdf"),
                    "original_filename": document_chunks[0].get("filename", "bulk_upload.pdf"),
                    "file_size": sum(chunk.get("token_count", 0) for chunk in document_chunks) * 4,  # 概算
                    "total_pages": max((chunk.get("page_number", 1) for chunk in document_chunks), default=1),
                    "processing_status": "completed",
                })
                
                # 非同期実行対応
                if hasattr(result, 'execute'):
                    if asyncio.iscoroutinefunction(result.execute):
                        await result.execute()
                    else:
                        result.execute()

            # バルクレコード準備
            bulk_records = []
            for _i, (embedding_result, chunk) in enumerate(
                zip(embeddings, document_chunks)
            ):
                # チャンクデータ検証
                validate_chunk_data(chunk)

                # 埋め込みベクトル検証
                embedding_vector = getattr(embedding_result, "embedding", None)
                if embedding_vector:
                    validate_embedding_vector(embedding_vector)

                chunk_record = {
                    "id": str(uuid.uuid4()),
                    "document_id": document_id,
                    "content": chunk.get("content", ""),
                    "filename": chunk.get("filename", ""),
                    "page_number": chunk.get("page_number"),
                    "chapter_number": chunk.get("chapter_number"),
                    "section_name": chunk.get("section_name"),
                    "start_pos": chunk.get("start_pos"),
                    "end_pos": chunk.get("end_pos"),
                    "embedding": embedding_vector,
                    "token_count": chunk.get("token_count", 0),
                }
                bulk_records.append(chunk_record)

            # Supabaseへバルクインサート実行
            bulk_result = client.table("document_chunks").insert(bulk_records)
            
            # 非同期実行対応
            if hasattr(bulk_result, 'execute'):
                if asyncio.iscoroutinefunction(bulk_result.execute):
                    await bulk_result.execute()
                else:
                    bulk_result.execute()

            logger.info(f"バルク埋め込み保存完了: {len(bulk_records)}件")
            return True

        except Exception as e:
            logger.error(f"バルク埋め込み保存エラー: {str(e)}", exc_info=True)
            raise VectorStoreError(
                f"バルク保存中にエラーが発生しました: {str(e)}"
            ) from e
        finally:
            # 接続を必ずプールに戻す
            await self._connection_pool.release_connection(connection_index)

    @async_retry(max_attempts=RETRY_ATTEMPTS)
    async def search_similar_embeddings(
        self, query_embedding: List[float], limit: int = 10, similarity_threshold: float = 0.0
    ) -> List[SearchResult]:
        """
        類似ベクトル検索 - Issue #57 要件実装（非同期・接続プール対応）

        Args:
            query_embedding: クエリ埋め込みベクトル
            limit: 返す結果数
            similarity_threshold: 類似度閾値

        Returns:
            List[SearchResult]: 検索結果リスト

        Raises:
            VectorStoreError: 検索エラーの場合
        """
        start_time = time.time()
        logger.info(f"類似埋め込み検索開始: limit={limit}")

        # 接続プールから接続を取得
        client, connection_index = await self._connection_pool.get_connection(async_mode=True)
        
        try:
            # 接続プールから取得したクライアントを使用（フォールバック付き）
            if not client:
                client = self.async_client if self.async_client else self.client
            
            if not client:
                raise VectorStoreError("Supabaseクライアントが初期化されていません")

            # 入力検証
            validate_embedding_vector(query_embedding)

            # limit パラメータの詳細検証
            if not isinstance(limit, int) or limit <= 0:
                raise VectorStoreError(f"limit は正の整数である必要があります: {limit}")

            if limit > MAX_SEARCH_LIMIT:
                raise VectorStoreError(
                    f"limit は{MAX_SEARCH_LIMIT}以下である必要があります: {limit}"
                )

            # pgvectorのコサイン類似度検索
            # RPC関数を使用した高速ベクトル検索
            # 類似度閾値から距離閾値に変換（distance = 1 - similarity）
            max_distance = 1.0 - similarity_threshold
            
            rpc_result = client.rpc(
                "match_documents",
                {
                    "query_embedding": query_embedding,
                    "match_threshold": max_distance,
                    "match_count": limit,
                },
            )

            # 非同期実行対応
            if hasattr(rpc_result, 'execute'):
                if asyncio.iscoroutinefunction(rpc_result.execute):
                    result = await rpc_result.execute()
                else:
                    result = rpc_result.execute()
            else:
                result = rpc_result

            # 結果をSearchResultオブジェクトに変換
            search_results = []
            if result.data:
                for row in result.data:
                    search_result = SearchResult(
                        content=row.get("content", ""),
                        filename=row.get("filename", ""),
                        page_number=row.get("page_number", 0),
                        similarity_score=1.0
                        - row.get("distance", 1.0),  # 距離を類似度に変換
                        metadata={
                            "section_name": row.get("section_name"),
                            "chapter_number": row.get("chapter_number"),
                            "start_pos": row.get("start_pos"),
                            "end_pos": row.get("end_pos"),
                            "token_count": row.get("token_count", 0),
                        },
                    )
                    search_results.append(search_result)

            # メトリクス更新
            end_time = time.time()
            response_time = end_time - start_time
            self._update_search_metrics(response_time)

            logger.info(f"類似埋め込み検索完了: {len(search_results)}件 ({response_time:.3f}秒)")
            return search_results

        except Exception as e:
            logger.error(f"類似埋め込み検索エラー: {str(e)}", exc_info=True)
            raise VectorStoreError(f"類似検索中にエラーが発生しました: {str(e)}") from e
        finally:
            # 接続を必ずプールに戻す
            await self._connection_pool.release_connection(connection_index)

    def _update_search_metrics(self, response_time: float) -> None:
        """
        検索メトリクスを更新

        Args:
            response_time: 検索応答時間（秒）
        """
        self._search_metrics["total_searches"] += 1
        self._search_metrics["total_time"] += response_time
        self._search_metrics["avg_response_time"] = (
            self._search_metrics["total_time"] / self._search_metrics["total_searches"]
        )
        self._search_metrics["last_search_time"] = response_time

        # パフォーマンス監視ログ
        if response_time > 1.0:  # 1秒超過の場合は警告
            logger.warning(f"検索応答時間が遅いです: {response_time:.3f}秒")
        
        logger.debug(
            f"検索メトリクス更新: 検索回数={self._search_metrics['total_searches']}, "
            f"平均応答時間={self._search_metrics['avg_response_time']:.3f}秒"
        )

    def get_search_metrics(self) -> Dict[str, Any]:
        """
        検索メトリクスを取得

        Returns:
            Dict[str, Any]: 検索メトリクス情報
        """
        return self._search_metrics.copy()

    async def get_connection_pool_status(self) -> Dict[str, Any]:
        """
        接続プール状態を取得

        Returns:
            Dict[str, Any]: 接続プール状態情報
        """
        pool_health = await self._connection_pool.health_check()
        return {
            "connection_pool": pool_health,
            "legacy_semaphore_count": self._connection_semaphore._value,
            "pool_enabled": True
        }


class VectorStoreError(Exception):
    """ベクトルストアエラー"""

    pass
