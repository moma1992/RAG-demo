"""
データベース管理クラス

ベクトル検索システムの中核となるデータベース管理機能
"""

import os
import logging
from typing import List, Dict, Any, Optional
from dataclasses import dataclass

from .vector_store import VectorStore, SearchResult, DocumentRecord, VectorStoreError

logger = logging.getLogger(__name__)


@dataclass
class DatabaseConfig:
    """データベース設定クラス"""
    supabase_url: str
    supabase_key: str
    max_file_size_mb: int = 50
    chunk_size: int = 512
    chunk_overlap: float = 0.1
    similarity_threshold: float = 0.7
    search_top_k: int = 5


class DatabaseManager:
    """データベース管理クラス"""
    
    def __init__(self, config: Optional[DatabaseConfig] = None):
        """
        初期化
        
        Args:
            config: データベース設定 (未指定時は環境変数から取得)
        """
        if config is None:
            config = self._load_config_from_env()
        
        self.config = config
        self.vector_store = VectorStore(
            supabase_url=config.supabase_url,
            supabase_key=config.supabase_key
        )
        
        logger.info("DatabaseManager初期化完了")
    
    def _load_config_from_env(self) -> DatabaseConfig:
        """環境変数からデータベース設定を読み込み"""
        supabase_url = os.getenv("SUPABASE_URL")
        supabase_key = os.getenv("SUPABASE_ANON_KEY")
        
        if not supabase_url or not supabase_key:
            raise ValueError("SUPABASE_URLとSUPABASE_ANON_KEYの環境変数が必要です")
        
        return DatabaseConfig(
            supabase_url=supabase_url,
            supabase_key=supabase_key,
            max_file_size_mb=int(os.getenv("MAX_FILE_SIZE_MB", "50")),
            chunk_size=int(os.getenv("CHUNK_SIZE", "512")),
            chunk_overlap=float(os.getenv("CHUNK_OVERLAP", "0.1")),
            similarity_threshold=float(os.getenv("SIMILARITY_THRESHOLD", "0.7")),
            search_top_k=int(os.getenv("SEARCH_TOP_K", "5"))
        )
    
    def store_document(self, document_data: Dict[str, Any]) -> str:
        """
        文書をデータベースに保存
        
        Args:
            document_data: 文書データ
            
        Returns:
            str: 文書ID
            
        Raises:
            DatabaseManagerError: 保存エラーの場合
        """
        try:
            return self.vector_store.store_document(document_data)
        except VectorStoreError as e:
            raise DatabaseManagerError(f"文書保存エラー: {str(e)}") from e
    
    def store_document_chunks(self, chunks: List[Dict[str, Any]], document_id: str) -> None:
        """
        文書チャンクをデータベースに保存
        
        Args:
            chunks: チャンクリスト
            document_id: 文書ID
            
        Raises:
            DatabaseManagerError: 保存エラーの場合
        """
        try:
            self.vector_store.store_chunks(chunks, document_id)
        except VectorStoreError as e:
            raise DatabaseManagerError(f"チャンク保存エラー: {str(e)}") from e
    
    def search_documents(
        self,
        query_embedding: List[float],
        k: Optional[int] = None,
        similarity_threshold: Optional[float] = None
    ) -> List[SearchResult]:
        """
        ベクトル類似検索を実行
        
        Args:
            query_embedding: 検索クエリのベクトル表現
            k: 返す結果数 (未指定時は設定値を使用)
            similarity_threshold: 類似度閾値 (未指定時は設定値を使用)
            
        Returns:
            List[SearchResult]: 検索結果リスト
            
        Raises:
            DatabaseManagerError: 検索エラーの場合
        """
        try:
            k = k or self.config.search_top_k
            similarity_threshold = similarity_threshold or self.config.similarity_threshold
            
            return self.vector_store.similarity_search(
                query_embedding=query_embedding,
                k=k,
                similarity_threshold=similarity_threshold
            )
        except VectorStoreError as e:
            raise DatabaseManagerError(f"検索エラー: {str(e)}") from e
    
    def get_all_documents(self) -> List[DocumentRecord]:
        """
        登録済み文書一覧を取得
        
        Returns:
            List[DocumentRecord]: 文書レコードリスト
            
        Raises:
            DatabaseManagerError: 取得エラーの場合
        """
        try:
            return self.vector_store.get_documents()
        except VectorStoreError as e:
            raise DatabaseManagerError(f"文書一覧取得エラー: {str(e)}") from e
    
    def delete_document(self, document_id: str) -> None:
        """
        文書を削除 (関連チャンクも同時削除)
        
        Args:
            document_id: 文書ID
            
        Raises:
            DatabaseManagerError: 削除エラーの場合
        """
        try:
            self.vector_store.delete_document(document_id)
        except VectorStoreError as e:
            raise DatabaseManagerError(f"文書削除エラー: {str(e)}") from e
    
    def update_document_status(self, document_id: str, status: str) -> None:
        """
        文書の処理状況を更新
        
        Args:
            document_id: 文書ID
            status: 処理状況 ('processing', 'completed', 'failed')
            
        Raises:
            DatabaseManagerError: 更新エラーの場合
        """
        try:
            # documentsテーブルの処理状況を更新
            if not self.vector_store.client:
                raise DatabaseManagerError("Supabaseクライアントが初期化されていません")
            
            result = self.vector_store.client.table("documents").update({
                "processing_status": status,
                "updated_at": "now()"
            }).eq("id", document_id).execute()
            
            logger.info(f"文書状況更新完了: {document_id} -> {status}")
            
        except Exception as e:
            logger.error(f"文書状況更新エラー: {str(e)}", exc_info=True)
            raise DatabaseManagerError(f"文書状況更新エラー: {str(e)}") from e
    
    def get_database_stats(self) -> Dict[str, Any]:
        """
        データベース統計情報を取得
        
        Returns:
            Dict[str, Any]: 統計情報
            
        Raises:
            DatabaseManagerError: 取得エラーの場合
        """
        try:
            if not self.vector_store.client:
                raise DatabaseManagerError("Supabaseクライアントが初期化されていません")
            
            # 文書数をカウント
            doc_result = self.vector_store.client.table("documents").select("id", count="exact").execute()
            document_count = doc_result.count or 0
            
            # チャンク数をカウント
            chunk_result = self.vector_store.client.table("document_chunks").select("id", count="exact").execute()
            chunk_count = chunk_result.count or 0
            
            # 処理状況別の文書数を取得
            status_result = self.vector_store.client.table("documents").select("processing_status").execute()
            status_counts = {}
            for row in status_result.data:
                status = row.get('processing_status', 'unknown')
                status_counts[status] = status_counts.get(status, 0) + 1
            
            stats = {
                "total_documents": document_count,
                "total_chunks": chunk_count,
                "status_breakdown": status_counts,
                "avg_chunks_per_document": chunk_count / document_count if document_count > 0 else 0
            }
            
            logger.info("データベース統計情報取得完了")
            return stats
            
        except Exception as e:
            logger.error(f"統計情報取得エラー: {str(e)}", exc_info=True)
            raise DatabaseManagerError(f"統計情報取得エラー: {str(e)}") from e
    
    def health_check(self) -> Dict[str, Any]:
        """
        データベース接続ヘルスチェック
        
        Returns:
            Dict[str, Any]: ヘルスチェック結果
        """
        try:
            if not self.vector_store.client:
                return {
                    "status": "error",
                    "message": "Supabaseクライアントが初期化されていません"
                }
            
            # 簡単なクエリでデータベース接続をテスト
            result = self.vector_store.client.table("documents").select("id").limit(1).execute()
            
            return {
                "status": "healthy",
                "message": "データベース接続正常",
                "timestamp": "now()"
            }
            
        except Exception as e:
            logger.error(f"ヘルスチェックエラー: {str(e)}", exc_info=True)
            return {
                "status": "error",
                "message": f"データベース接続エラー: {str(e)}"
            }


class DatabaseManagerError(Exception):
    """データベース管理エラー"""
    pass