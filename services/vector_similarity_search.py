"""
ベクトル類似検索サービス

Issue #37: Vector Similarity Search Implementation
高性能ベクトル類似検索システム実装

LangChain SupabaseVectorStoreを活用した
企業内文書検索向けベクトル検索エンジン

主要機能:
- 意味的類似検索（OpenAI埋め込みベクトル）
- ハイブリッド検索（ベクトル + 全文検索）
- フィルタリング機能（メタデータベース）
- パフォーマンス最適化（500ms以下）
- セキュリティ検証（入力値検証）
"""

import logging
import time
import re
from typing import List, Dict, Any, Optional, Union
from dataclasses import dataclass, field
import uuid

logger = logging.getLogger(__name__)

# パフォーマンス最適化定数
DEFAULT_SIMILARITY_THRESHOLD = 0.7
DEFAULT_SEARCH_LIMIT = 10
MAX_SEARCH_LIMIT = 100
PERFORMANCE_WARNING_THRESHOLD_MS = 500

# セキュリティ関連定数
MAX_QUERY_LENGTH = 1000
MAX_FILTER_DEPTH = 3


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
        
        if len(self.text) > MAX_QUERY_LENGTH:
            raise ValueError(f"クエリテキストが長すぎます（最大{MAX_QUERY_LENGTH}文字）")
        
        if not isinstance(self.limit, int) or not (1 <= self.limit <= MAX_SEARCH_LIMIT):
            raise ValueError(f"limit は1以上{MAX_SEARCH_LIMIT}以下である必要があります")
        
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
                raise ValueError("セキュリティ違反：危険なコンテンツが検出されました")


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


class VectorSearchError(Exception):
    """ベクトル検索エラー"""
    pass


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
        table_name: str = "document_chunks"
    ) -> None:
        """
        初期化
        
        Args:
            supabase_client: Supabaseクライアント
            embeddings: 埋め込みモデル（OpenAI等）
            table_name: 検索対象テーブル名
        """
        self.supabase_client = supabase_client
        self.embeddings = embeddings
        self.table_name = table_name
        
        logger.info(f"VectorSearch初期化完了: table={table_name}")
    
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
        try:
            start_time = time.time()
            
            # 埋め込みベクトル生成
            try:
                query_embedding = self.embeddings.embed_query(query.text)
            except Exception as e:
                raise VectorSearchError(f"埋め込みベクトル生成エラー: {str(e)}") from e
            
            # pgvectorコサイン距離検索
            max_distance = 1.0 - query.similarity_threshold
            
            try:
                # Supabase RPC関数を使用したベクトル検索
                result = self.supabase_client.rpc(
                    "match_documents",
                    {
                        "query_embedding": query_embedding,
                        "match_threshold": max_distance,
                        "match_count": query.limit,
                    }
                ).execute()
            except Exception as e:
                raise VectorSearchError(f"データベース検索エラー: {str(e)}") from e
            
            # 結果変換
            search_results = []
            if result.data:
                for row in result.data:
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
            
            end_time = time.time()
            response_time = (end_time - start_time) * 1000
            
            # パフォーマンス警告チェック
            if response_time > PERFORMANCE_WARNING_THRESHOLD_MS:
                logger.warning(f"検索時間が閾値を超過: {response_time:.2f}ms > {PERFORMANCE_WARNING_THRESHOLD_MS}ms")
            
            logger.info(f"類似検索完了: {len(search_results)}件, {response_time:.2f}ms")
            
            return search_results
            
        except VectorSearchError:
            raise
        except Exception as e:
            logger.error(f"予期しない検索エラー: {str(e)}", exc_info=True)
            raise VectorSearchError(f"検索処理中にエラーが発生しました: {str(e)}") from e
    
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