"""
ベクトル類似検索サービス

Issue #37: Vector Similarity Search Implementation
TDD Green フェーズ: 最小実装

LangChain SupabaseVectorStoreを活用した
高性能ベクトル類似検索システム
"""

import logging
import time
import re
import functools
from typing import List, Dict, Any, Optional, Union, Callable
from dataclasses import dataclass, field
import uuid
import asyncio
from enum import Enum

logger = logging.getLogger(__name__)


@dataclass
class SearchQuery:
    """
    検索クエリデータクラス
    
    ベクトル類似検索の入力パラメータを定義します。
    """
    text: str
    limit: int = 5
    similarity_threshold: float = 0.7
    filters: Optional[Dict[str, Any]] = None
    include_metadata: bool = True
    
    def __post_init__(self) -> None:
        """初期化後の検証"""
        self.validate()
    
    def validate(self) -> None:
        """入力検証"""
        if not isinstance(self.text, str) or not self.text.strip():
            raise ValueError("text は空でない文字列である必要があります")
        
        if not isinstance(self.limit, int) or not (1 <= self.limit <= 100):
            raise ValueError("limit は1以上100以下である必要があります")
        
        if not isinstance(self.similarity_threshold, (int, float)) or not (0.0 <= self.similarity_threshold <= 1.0):
            raise ValueError("similarity_threshold は0.0-1.0の範囲である必要があります")
        
        # セキュリティ検証
        self._validate_security()
    
    def _validate_security(self) -> None:
        """セキュリティ検証"""
        # SQLインジェクション対策
        dangerous_patterns = [
            r"(?i)(union\s+select|drop\s+table|delete\s+from|insert\s+into|update\s+set)",
            r"(?i)(script\s*>|<\s*script|javascript:|vbscript:)",
            r"(?i)(exec\s*\(|eval\s*\(|system\s*\()",
            r"[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]"  # 制御文字
        ]
        
        for pattern in dangerous_patterns:
            if re.search(pattern, self.text):
                raise SecurityError(
                    "危険なコンテンツが検出されました",
                    context={"query_snippet": self.text[:50]}
                )


@dataclass
class SearchResult:
    """
    検索結果データクラス
    
    ベクトル類似検索の結果を格納します。
    """
    chunk_id: str
    content: str
    filename: str
    page_number: int
    similarity_score: float
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self) -> None:
        """初期化後の検証"""
        self.validate()
    
    def validate(self) -> None:
        """検証"""
        if not isinstance(self.similarity_score, (int, float)) or not (0.0 <= self.similarity_score <= 1.0):
            raise ValueError("similarity_score は0.0-1.0の範囲である必要があります")
        
        if not isinstance(self.page_number, int) or self.page_number <= 0:
            raise ValueError("page_number は正の整数である必要があります")


class ErrorSeverity(Enum):
    """エラー重要度分類"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class VectorSearchError(Exception):
    """ベクトル検索基底エラークラス"""
    def __init__(
        self,
        message: str,
        error_code: str = "VECTOR_SEARCH_ERROR",
        severity: ErrorSeverity = ErrorSeverity.MEDIUM,
        context: Optional[Dict[str, Any]] = None
    ):
        self.message = message
        self.error_code = error_code
        self.severity = severity
        self.context = context or {}
        self.timestamp = time.time()
        super().__init__(self.message)


class DatabaseConnectionError(VectorSearchError):
    """データベース接続エラー"""
    def __init__(self, message: str, context: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=f"データベース接続エラー: {message}",
            error_code="DB_CONNECTION_ERROR",
            severity=ErrorSeverity.HIGH,
            context=context
        )


class EmbeddingGenerationError(VectorSearchError):
    """埋め込みベクトル生成エラー"""
    def __init__(self, message: str, context: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=f"埋め込み生成エラー: {message}",
            error_code="EMBEDDING_ERROR",
            severity=ErrorSeverity.MEDIUM,
            context=context
        )


class QueryValidationError(VectorSearchError):
    """クエリ検証エラー"""
    def __init__(self, message: str, context: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=f"クエリ検証エラー: {message}",
            error_code="QUERY_VALIDATION_ERROR",
            severity=ErrorSeverity.LOW,
            context=context
        )


class PerformanceError(VectorSearchError):
    """パフォーマンス要件違反エラー"""
    def __init__(self, message: str, context: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=f"パフォーマンス要件違反: {message}",
            error_code="PERFORMANCE_ERROR",
            severity=ErrorSeverity.MEDIUM,
            context=context
        )


class SecurityError(VectorSearchError):
    """セキュリティ違反エラー"""
    def __init__(self, message: str, context: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=f"セキュリティ違反: {message}",
            error_code="SECURITY_ERROR",
            severity=ErrorSeverity.CRITICAL,
            context=context
        )


def retry_with_exponential_backoff(
    max_retries: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 30.0,
    exceptions: tuple = (Exception,)
) -> Callable:
    """
    指数バックオフリトライデコレータ
    
    Args:
        max_retries: 最大リトライ回数
        base_delay: 基本遅延時間（秒）
        max_delay: 最大遅延時間（秒）
        exceptions: リトライ対象外例外のタプル
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            last_exception = None
            
            for attempt in range(max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e
                    
                    if attempt == max_retries:
                        logger.error(
                            f"最大リトライ回数に達しました: {func.__name__}",
                            extra={
                                "attempts": attempt + 1,
                                "max_retries": max_retries,
                                "error": str(e)
                            }
                        )
                        raise
                    
                    # 指数バックオフ計算
                    delay = min(base_delay * (2 ** attempt), max_delay)
                    
                    logger.warning(
                        f"リトライ実行中: {func.__name__} (試行 {attempt + 1}/{max_retries + 1})",
                        extra={
                            "attempt": attempt + 1,
                            "delay": delay,
                            "error": str(e)
                        }
                    )
                    
                    time.sleep(delay)
            
            # 最後の例外を再発生
            if last_exception:
                raise last_exception
                
        return wrapper
    return decorator


class StructuredLogger:
    """構造化ログクラス"""
    
    def __init__(self, name: str):
        self.logger = logging.getLogger(name)
        
    def log_search_start(self, query: str, limit: int, threshold: float) -> None:
        """検索開始ログ"""
        self.logger.info(
            "ベクトル検索開始",
            extra={
                "event": "search_start",
                "query_length": len(query),
                "limit": limit,
                "threshold": threshold,
                "timestamp": time.time()
            }
        )
    
    def log_search_success(
        self,
        results_count: int,
        response_time_ms: float,
        query: str = ""
    ) -> None:
        """検索成功ログ"""
        self.logger.info(
            f"ベクトル検索完了: {results_count}件取得",
            extra={
                "event": "search_success",
                "results_count": results_count,
                "response_time_ms": response_time_ms,
                "query_length": len(query),
                "timestamp": time.time()
            }
        )
    
    def log_error(
        self,
        error: VectorSearchError,
        context: Optional[Dict[str, Any]] = None
    ) -> None:
        """エラーログ"""
        log_level = {
            ErrorSeverity.LOW: logging.INFO,
            ErrorSeverity.MEDIUM: logging.WARNING,
            ErrorSeverity.HIGH: logging.ERROR,
            ErrorSeverity.CRITICAL: logging.CRITICAL
        }.get(error.severity, logging.ERROR)
        
        self.logger.log(
            log_level,
            f"エラー発生: {error.message}",
            extra={
                "event": "error",
                "error_code": error.error_code,
                "severity": error.severity.value,
                "error_context": error.context,
                "additional_context": context or {},
                "timestamp": error.timestamp
            },
            exc_info=True
        )
    
    def log_performance_warning(
        self,
        operation: str,
        response_time_ms: float,
        threshold_ms: float = 500.0
    ) -> None:
        """パフォーマンス警告ログ"""
        if response_time_ms > threshold_ms:
            self.logger.warning(
                f"パフォーマンス警告: {operation}が{response_time_ms:.2f}ms（閾値: {threshold_ms}ms）",
                extra={
                    "event": "performance_warning",
                    "operation": operation,
                    "response_time_ms": response_time_ms,
                    "threshold_ms": threshold_ms,
                    "timestamp": time.time()
                }
            )


class VectorSearch:
    """
    ベクトル類似検索メインクラス
    
    LangChain SupabaseVectorStoreを使用した
    高性能ベクトル検索機能を提供します。
    """
    
    def __init__(
        self,
        supabase_client: Any,
        embeddings: Any,
        table_name: str = "document_chunks",
        enable_retry: bool = True,
        max_retries: int = 3,
        performance_threshold_ms: float = 500.0
    ) -> None:
        """
        初期化
        
        Args:
            supabase_client: Supabaseクライアント
            embeddings: 埋め込みモデル（OpenAI等）
            table_name: 検索対象テーブル名
            enable_retry: リトライ機能を有効にするか
            max_retries: 最大リトライ回数
            performance_threshold_ms: パフォーマンス警告閾値（ミリ秒）
        """
        self.supabase_client = supabase_client
        self.embeddings = embeddings
        self.table_name = table_name
        self.enable_retry = enable_retry
        self.max_retries = max_retries
        self.performance_threshold_ms = performance_threshold_ms
        self.structured_logger = StructuredLogger(__name__)
        
        # 初期化確認
        self._verify_initialization()
        
        logger.info(f"VectorSearch初期化完了: table={table_name}")
    
    def _verify_initialization(self) -> None:
        """初期化検証"""
        try:
            if not self.supabase_client:
                raise DatabaseConnectionError(
                    "Supabaseクライアントが設定されていません",
                    context={"table_name": self.table_name}
                )
            
            if not self.embeddings:
                raise EmbeddingGenerationError(
                    "埋め込みモデルが設定されていません",
                    context={"table_name": self.table_name}
                )
                
        except Exception as e:
            if isinstance(e, VectorSearchError):
                self.structured_logger.log_error(e)
                raise
            else:
                error = VectorSearchError(
                    f"初期化エラー: {str(e)}",
                    error_code="INITIALIZATION_ERROR",
                    severity=ErrorSeverity.CRITICAL
                )
                self.structured_logger.log_error(error)
                raise error
    
    @retry_with_exponential_backoff(
        max_retries=3,
        base_delay=1.0,
        exceptions=(DatabaseConnectionError, EmbeddingGenerationError)
    )
    def search_similar_chunks(self, query: SearchQuery) -> List[SearchResult]:
        """
        類似チャンク検索
        
        Args:
            query: 検索クエリ
            
        Returns:
            List[SearchResult]: 検索結果リスト
            
        Raises:
            VectorSearchError: 検索エラーの場合
        """
        start_time = time.time()
        
        try:
            # 検索開始ログ
            self.structured_logger.log_search_start(
                query.text, query.limit, query.similarity_threshold
            )
            
            # クエリ検証
            self._validate_search_query(query)
            
            # 埋め込みベクトル生成（リトライ対象）
            query_embedding = self._generate_embedding(query.text)
            
            # データベース検索（リトライ対象）
            search_results = self._execute_vector_search(query, query_embedding)
            
            # パフォーマンス計測
            end_time = time.time()
            response_time_ms = (end_time - start_time) * 1000
            
            # パフォーマンス警告チェック
            self.structured_logger.log_performance_warning(
                "search_similar_chunks", response_time_ms, self.performance_threshold_ms
            )
            
            # 成功ログ
            self.structured_logger.log_search_success(
                len(search_results), response_time_ms, query.text
            )
            
            return search_results
            
        except VectorSearchError as e:
            # 構造化エラーログ
            self.structured_logger.log_error(e, {"operation": "search_similar_chunks"})
            raise
        except Exception as e:
            # 予期しないエラーをVectorSearchErrorに変換
            error = VectorSearchError(
                f"予期しない検索エラー: {str(e)}",
                error_code="UNEXPECTED_SEARCH_ERROR",
                severity=ErrorSeverity.HIGH,
                context={
                    "operation": "search_similar_chunks",
                    "query_text": query.text[:100],  # プライバシー保護のため100文字まで
                    "limit": query.limit
                }
            )
            self.structured_logger.log_error(error)
            raise error
    
    def _validate_search_query(self, query: SearchQuery) -> None:
        """検索クエリ詳細検証"""
        try:
            # 基本バリデーションは既にSearchQueryで実行済み
            
            # 追加セキュリティチェック
            if self._contains_suspicious_content(query.text):
                raise SecurityError(
                    "危険なコンテンツが検出されました",
                    context={"query_snippet": query.text[:50]}
                )
            
            # リソース制限チェック
            if len(query.text) > 10000:  # 10KB制限
                raise QueryValidationError(
                    "クエリテキストが長すぎます（10KB以下にしてください）",
                    context={"text_length": len(query.text)}
                )
                
        except VectorSearchError:
            raise
        except Exception as e:
            raise QueryValidationError(
                f"クエリ検証中にエラーが発生しました: {str(e)}",
                context={"query_text": query.text[:100]}
            )
    
    def _contains_suspicious_content(self, text: str) -> bool:
        """疑わしいコンテンツの検出"""
        # 既存のセキュリティパターンに加えて追加チェック
        suspicious_patterns = [
            r"(?i)(union\s+select|drop\s+table|delete\s+from|insert\s+into|update\s+set)",
            r"(?i)(<\s*script|script\s*>|javascript:|vbscript:)",
            r"(?i)(exec\s*\(|eval\s*\(|system\s*\()",
            r"[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]",  # 制御文字
            r"(?i)(\.\.\/|\.\.\\)",  # パストラバーサル
            r"(?i)(file:\/\/|ftp:\/\/)",  # 危険なプロトコル
        ]
        
        for pattern in suspicious_patterns:
            if re.search(pattern, text):
                return True
        return False
    
    def _generate_embedding(self, text: str) -> List[float]:
        """埋め込みベクトル生成（エラーハンドリング付き）"""
        try:
            embedding = self.embeddings.embed_query(text)
            
            # 埋め込みベクトル検証
            if not embedding or len(embedding) == 0:
                raise EmbeddingGenerationError(
                    "空の埋め込みベクトルが返されました",
                    context={"text_length": len(text)}
                )
            
            return embedding
            
        except Exception as e:
            if isinstance(e, VectorSearchError):
                raise
            
            # API制限エラー等の分類
            error_msg = str(e).lower()
            if "rate limit" in error_msg or "quota" in error_msg:
                raise EmbeddingGenerationError(
                    "API利用制限に達しました。しばらく時間をおいてから再度お試しください",
                    context={"original_error": str(e)}
                )
            elif "connection" in error_msg or "timeout" in error_msg:
                raise EmbeddingGenerationError(
                    "API接続エラーが発生しました",
                    context={"original_error": str(e)}
                )
            else:
                raise EmbeddingGenerationError(
                    f"埋め込み生成中にエラーが発生しました: {str(e)}",
                    context={"text_length": len(text)}
                )
    
    def _execute_vector_search(
        self, 
        query: SearchQuery, 
        query_embedding: List[float]
    ) -> List[SearchResult]:
        """ベクトル検索実行（エラーハンドリング付き）"""
        try:
            max_distance = 1.0 - query.similarity_threshold
            
            # Supabase RPC関数を使用したベクトル検索
            result = self.supabase_client.rpc(
                "match_documents",
                {
                    "query_embedding": query_embedding,
                    "match_threshold": max_distance,
                    "match_count": query.limit,
                }
            ).execute()
            
            # 結果変換
            search_results = []
            if result.data:
                for row in result.data:
                    try:
                        similarity_score = 1.0 - row.get("distance", 1.0)
                        
                        search_result = SearchResult(
                            chunk_id=row.get("id", ""),
                            content=row.get("content", ""),
                            filename=row.get("filename", ""),
                            page_number=row.get("page_number", 1),
                            similarity_score=similarity_score,
                            metadata={
                                "section_name": row.get("section_name"),
                                "chapter_number": row.get("chapter_number"),
                                "start_pos": row.get("start_pos"),
                                "end_pos": row.get("end_pos"),
                                "token_count": row.get("token_count", 0),
                            } if query.include_metadata else {}
                        )
                        search_results.append(search_result)
                    except Exception as e:
                        logger.warning(f"結果変換エラー（スキップ）: {str(e)}")
                        continue
            
            return search_results
            
        except Exception as e:
            if isinstance(e, VectorSearchError):
                raise
            
            # データベースエラーの分類
            error_msg = str(e).lower()
            if "connection" in error_msg or "timeout" in error_msg:
                raise DatabaseConnectionError(
                    "データベース接続エラーが発生しました",
                    context={
                        "table_name": self.table_name,
                        "original_error": str(e)
                    }
                )
            elif "permission" in error_msg or "auth" in error_msg:
                raise DatabaseConnectionError(
                    "データベース認証エラーが発生しました",
                    context={
                        "table_name": self.table_name,
                        "original_error": str(e)
                    }
                )
            else:
                raise DatabaseConnectionError(
                    f"データベース検索中にエラーが発生しました: {str(e)}",
                    context={
                        "table_name": self.table_name,
                        "query_limit": query.limit
                    }
                )
    
    def hybrid_search(self, query: SearchQuery) -> List[SearchResult]:
        """
        ハイブリッド検索（ベクトル + 全文検索）
        
        Args:
            query: 検索クエリ
            
        Returns:
            List[SearchResult]: 検索結果リスト
        """
        try:
            # 基本的な実装：類似検索と同じ動作
            # 実際の実装では、全文検索と組み合わせる
            result = self.supabase_client.rpc(
                "hybrid_search_documents",  # ハイブリッド検索用RPC関数
                {
                    "query_text": query.text,
                    "query_embedding": self.embeddings.embed_query(query.text),
                    "match_count": query.limit,
                    "similarity_threshold": query.similarity_threshold
                }
            ).execute()
            
            return self._convert_to_search_results(result.data, query.include_metadata)
            
        except Exception as e:
            logger.error(f"ハイブリッド検索エラー: {str(e)}", exc_info=True)
            raise VectorSearchError(f"ハイブリッド検索中にエラーが発生しました: {str(e)}") from e
    
    def search_by_filters(
        self,
        filters: Dict[str, Any],
        limit: int = 20
    ) -> List[SearchResult]:
        """
        フィルタのみでの検索
        
        Args:
            filters: 検索フィルタ
            limit: 結果数上限
            
        Returns:
            List[SearchResult]: 検索結果リスト
        """
        try:
            # フィルタベース検索
            query_builder = self.supabase_client.table(self.table_name).select("*")
            
            # フィルタ条件適用
            for key, value in filters.items():
                if isinstance(value, dict):
                    # 範囲検索等の複雑なフィルタ
                    for op, op_value in value.items():
                        if op == "$gte":
                            query_builder = query_builder.gte(key, op_value)
                        elif op == "$lte":
                            query_builder = query_builder.lte(key, op_value)
                        elif op == "$eq":
                            query_builder = query_builder.eq(key, op_value)
                        elif op == "$in":
                            query_builder = query_builder.in_(key, op_value)
                else:
                    # 単純な等価フィルタ
                    query_builder = query_builder.eq(key, value)
            
            result = query_builder.limit(limit).execute()
            
            return self._convert_to_search_results(result.data, include_metadata=True)
            
        except Exception as e:
            logger.error(f"フィルタ検索エラー: {str(e)}", exc_info=True)
            raise VectorSearchError(f"フィルタ検索中にエラーが発生しました: {str(e)}") from e
    
    def get_chunk_by_id(self, chunk_id: str) -> Optional[SearchResult]:
        """
        ID指定でチャンク取得
        
        Args:
            chunk_id: チャンクID
            
        Returns:
            Optional[SearchResult]: 検索結果（見つからない場合はNone）
        """
        try:
            result = self.supabase_client.table(self.table_name).select("*").eq("id", chunk_id).execute()
            
            if result.data:
                row = result.data[0]
                return SearchResult(
                    chunk_id=row.get("id", ""),
                    content=row.get("content", ""),
                    filename=row.get("filename", ""),
                    page_number=row.get("page_number", 1),
                    similarity_score=1.0,  # ID検索では類似度は最大
                    metadata={
                        "section_name": row.get("section_name"),
                        "chapter_number": row.get("chapter_number"),
                        "start_pos": row.get("start_pos"),
                        "end_pos": row.get("end_pos"),
                        "token_count": row.get("token_count", 0),
                    }
                )
            
            return None
            
        except Exception as e:
            logger.error(f"ID検索エラー: {str(e)}", exc_info=True)
            raise VectorSearchError(f"ID検索中にエラーが発生しました: {str(e)}") from e
    
    def calculate_similarity_score(self, distance: float) -> float:
        """
        距離から類似度スコアを計算
        
        Args:
            distance: pgvectorのコサイン距離
            
        Returns:
            float: 類似度スコア (0.0-1.0)
        """
        return 1.0 - distance
    
    def _convert_to_search_results(
        self,
        data: List[Dict[str, Any]],
        include_metadata: bool = True
    ) -> List[SearchResult]:
        """
        データベース結果をSearchResultに変換
        
        Args:
            data: データベース結果
            include_metadata: メタデータを含めるか
            
        Returns:
            List[SearchResult]: 変換された検索結果
        """
        results = []
        for row in data:
            similarity_score = 1.0 - row.get("distance", 0.0)
            
            result = SearchResult(
                chunk_id=row.get("id", ""),
                content=row.get("content", ""),
                filename=row.get("filename", ""),
                page_number=row.get("page_number", 1),
                similarity_score=similarity_score,
                metadata={
                    "section_name": row.get("section_name"),
                    "chapter_number": row.get("chapter_number"),
                    "start_pos": row.get("start_pos"),
                    "end_pos": row.get("end_pos"),
                    "token_count": row.get("token_count", 0),
                } if include_metadata else {}
            )
            results.append(result)
        
        return results