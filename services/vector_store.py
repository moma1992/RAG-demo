"""
ベクトルストアサービス

Supabase + pgvectorを使用したベクトル検索機能
"""

from typing import List, Dict, Any, Optional, Tuple
import logging
from dataclasses import dataclass
import uuid

logger = logging.getLogger(__name__)

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
            self.client = None
            
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
                result = self.client.table("documents").insert({
                    "id": document_id,
                    "filename": document_data.get("filename"),
                    "original_filename": document_data.get("original_filename", document_data.get("filename")),
                    "file_size": document_data.get("file_size", 0),
                    "total_pages": document_data.get("total_pages", 0),
                    "processing_status": "processing"
                }).execute()
            
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
                    "token_count": chunk.get("token_count", 0)
                }
                chunk_records.append(chunk_record)
            
            # バッチ挿入実行
            result = self.client.table("document_chunks").insert(chunk_records).execute()
            
            logger.info(f"チャンク保存完了: {len(chunk_records)}個")
            
        except Exception as e:
            logger.error(f"チャンク保存エラー: {str(e)}", exc_info=True)
            raise VectorStoreError(f"チャンク保存中にエラーが発生しました: {str(e)}") from e
    
    def similarity_search(
        self,
        query_embedding: List[float],
        k: int = 5,
        similarity_threshold: float = 0.7
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
            
            # pgvectorのコサイン距離検索を実行
            # 距離を類似度スコアに変換: similarity = 1 - distance
            max_distance = 1.0 - similarity_threshold
            
            # RPC関数を使用したベクトル検索
            result = self.client.rpc(
                'match_documents',
                {
                    'query_embedding': query_embedding,
                    'match_threshold': max_distance,
                    'match_count': k
                }
            ).execute()
            
            # 結果をSearchResultオブジェクトに変換
            search_results = []
            for row in result.data:
                search_result = SearchResult(
                    content=row.get('content', ''),
                    filename=row.get('filename', ''),
                    page_number=row.get('page_number', 0),
                    similarity_score=1.0 - row.get('distance', 1.0),  # 距離を類似度に変換
                    metadata={
                        'section_name': row.get('section_name'),
                        'chapter_number': row.get('chapter_number'),
                        'start_pos': row.get('start_pos'),
                        'end_pos': row.get('end_pos'),
                        'token_count': row.get('token_count', 0)
                    }
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
            result = self.client.table("documents").select("*").order("upload_date", desc=True).execute()
            
            # DocumentRecordオブジェクトに変換
            documents = []
            for row in result.data:
                document = DocumentRecord(
                    id=row.get('id', ''),
                    filename=row.get('filename', ''),
                    original_filename=row.get('original_filename', ''),
                    upload_date=row.get('upload_date', ''),
                    file_size=row.get('file_size', 0),
                    total_pages=row.get('total_pages', 0),
                    processing_status=row.get('processing_status', 'unknown')
                )
                documents.append(document)
            
            logger.info(f"文書一覧取得完了: {len(documents)}件")
            return documents
            
        except Exception as e:
            logger.error(f"文書一覧取得エラー: {str(e)}", exc_info=True)
            raise VectorStoreError(f"文書一覧取得中にエラーが発生しました: {str(e)}") from e
    
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
                result = self.client.table("documents").delete().eq("id", document_id).execute()
            
            logger.info(f"文書削除完了: {document_id}")
            
        except Exception as e:
            logger.error(f"文書削除エラー: {str(e)}", exc_info=True)
            raise VectorStoreError(f"文書削除中にエラーが発生しました: {str(e)}") from e

class VectorStoreError(Exception):
    """ベクトルストアエラー"""
    pass