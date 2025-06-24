"""
ベクトルストアサービス

Supabase + pgvectorを使用したベクトル検索機能
"""

from typing import List, Dict, Any
import logging
from dataclasses import dataclass
import uuid
import math

logger = logging.getLogger(__name__)

# セキュリティ関連の定数
EMBEDDING_DIMENSION = 1536
MAX_EMBEDDING_VALUE = 1000.0
MAX_CONTENT_LENGTH = 10000
MAX_SEARCH_LIMIT = 100
MAX_FILENAME_LENGTH = 255


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
    """ベクトルストアクラス"""

    def __init__(self, supabase_url: str, supabase_key: str) -> None:
        """
        初期化

        Args:
            supabase_url: Supabase URL
            supabase_key: Supabase APIキー
        """
        self.supabase_url = supabase_url
        self.supabase_key = supabase_key

        # Supabaseクライアント初期化（テスト時はモック対象）
        try:
            from supabase import create_client

            self.client = create_client(supabase_url, supabase_key)
        except ImportError:
            self.client = None  # type: ignore

        logger.info("VectorStore初期化完了")

    def store_document(self, document_data: Dict[str, Any]) -> str:
        """
        文書をデータベースに保存

        Args:
            document_data: 文書データ

        Returns:
            str: 文書ID

        Raises:
            VectorStoreError: データベースエラーの場合
        """
        logger.info(f"文書保存開始: {document_data.get('filename', 'unknown')}")

        try:
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

    def store_chunks(self, chunks: List[Dict[str, Any]], document_id: str) -> None:
        """
        チャンクをデータベースに保存

        Args:
            chunks: チャンクリスト
            document_id: 文書ID

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
            self.client.table("document_chunks").insert(chunk_records).execute()

            logger.info(f"チャンク保存完了: {len(chunk_records)}個")

        except Exception as e:
            logger.error(f"チャンク保存エラー: {str(e)}", exc_info=True)
            raise VectorStoreError(
                f"チャンク保存中にエラーが発生しました: {str(e)}"
            ) from e

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

    async def bulk_insert_embeddings(
        self, embeddings: List[Any], document_chunks: List[Dict[str, Any]]
    ) -> bool:
        """
        バルク埋め込み保存 - Issue #57 要件実装

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

        try:
            if not self.client:
                raise VectorStoreError("Supabaseクライアントが初期化されていません")

            # 入力検証
            if not embeddings or not document_chunks:
                raise VectorStoreError("埋め込みまたはチャンクリストが空です")

            if len(embeddings) != len(document_chunks):
                raise VectorStoreError(
                    f"埋め込み数({len(embeddings)})とチャンク数({len(document_chunks)})が一致しません"
                )

            # 文書ID生成
            document_id = str(uuid.uuid4())

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
            self.client.table("document_chunks").insert(bulk_records).execute()

            logger.info(f"バルク埋め込み保存完了: {len(bulk_records)}件")
            return True

        except Exception as e:
            logger.error(f"バルク埋め込み保存エラー: {str(e)}", exc_info=True)
            raise VectorStoreError(
                f"バルク保存中にエラーが発生しました: {str(e)}"
            ) from e

    async def search_similar_embeddings(
        self, query_embedding: List[float], limit: int = 10
    ) -> List[SearchResult]:
        """
        類似ベクトル検索 - Issue #57 要件実装

        Args:
            query_embedding: クエリ埋め込みベクトル
            limit: 返す結果数

        Returns:
            List[SearchResult]: 検索結果リスト

        Raises:
            VectorStoreError: 検索エラーの場合
        """
        logger.info(f"類似埋め込み検索開始: limit={limit}")

        try:
            if not self.client:
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
            rpc_result = self.client.rpc(
                "match_documents",
                {
                    "query_embedding": query_embedding,
                    "match_threshold": 0.0,  # 閾値なしで全結果取得
                    "match_count": limit,
                },
            ).execute()

            # 非同期実行の場合はawaitする
            if hasattr(rpc_result, "__await__"):
                result = await rpc_result
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

            logger.info(f"類似埋め込み検索完了: {len(search_results)}件")
            return search_results

        except Exception as e:
            logger.error(f"類似埋め込み検索エラー: {str(e)}", exc_info=True)
            raise VectorStoreError(f"類似検索中にエラーが発生しました: {str(e)}") from e


class VectorStoreError(Exception):
    """ベクトルストアエラー"""

    pass
