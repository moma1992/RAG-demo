"""
ベクトルストレージ操作クラス

Issue #36: ベクトルデータベースへの効率的なチャンク保存・管理機能
TDD Refactor フェーズ: コード品質向上

このモジュールは、Supabase + pgvectorを使用した
大容量ベクトルデータの効率的なバッチ処理機能を提供します。

主要機能:
- バッチチャンク保存・更新・削除
- 埋め込みベクトル管理
- 重複チェック機能
- 部分的失敗に対応したエラーハンドリング
- パフォーマンス統計情報
"""

import logging
import uuid
from typing import List, Dict, Any, Optional, Union, Tuple
from dataclasses import dataclass, field
import math
from datetime import datetime

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class ChunkData:
    """
    文書チャンクデータの不変オブジェクト
    
    ベクトルデータベースに保存される文書チャンクの全情報を含みます。
    immutableな設計により、データの整合性を保証します。
    
    Attributes:
        id: チャンクの一意識別子
        document_id: 親文書のID
        content: チャンクのテキストコンテンツ
        filename: 元ファイル名
        page_number: ページ番号（1以上）
        chapter_number: 章番号（任意）
        section_name: セクション名（任意）
        start_pos: 開始座標 {"x": float, "y": float}
        end_pos: 終了座標 {"x": float, "y": float}
        embedding: 1536次元の埋め込みベクトル
        token_count: トークン数（1以上）
        created_at: 作成日時（自動設定）
    """
    id: str
    document_id: str
    content: str
    filename: str
    page_number: int
    chapter_number: Optional[int] = None
    section_name: Optional[str] = None
    start_pos: Optional[Dict[str, float]] = None
    end_pos: Optional[Dict[str, float]] = None
    embedding: List[float] = field(default_factory=list)
    token_count: int = 0
    created_at: datetime = field(default_factory=datetime.now)
    
    def __post_init__(self) -> None:
        """初期化後の自動検証"""
        self.validate()
    
    def validate(self) -> None:
        """
        チャンクデータの包括的検証
        
        Raises:
            VectorStorageError: 検証エラーの場合
        """
        # UUID形式の検証
        try:
            uuid.UUID(self.id)
        except ValueError:
            raise VectorStorageError(f"無効なチャンクID形式です: {self.id}")
        
        try:
            uuid.UUID(self.document_id)
        except ValueError:
            raise VectorStorageError(f"無効な文書ID形式です: {self.document_id}")
        
        # 必須フィールドの検証
        if not self.content or not self.content.strip():
            raise VectorStorageError("コンテンツが空です")
        
        if len(self.content) > 10000:
            raise VectorStorageError(f"コンテンツが長すぎます: {len(self.content)}文字 (最大10000文字)")
        
        if not self.filename or not self.filename.strip():
            raise VectorStorageError("ファイル名が空です")
        
        # 数値フィールドの検証
        if self.page_number <= 0:
            raise VectorStorageError(f"ページ番号は正の整数である必要があります: {self.page_number}")
        
        if self.chapter_number is not None and self.chapter_number <= 0:
            raise VectorStorageError(f"章番号は正の整数である必要があります: {self.chapter_number}")
        
        if self.token_count <= 0:
            raise VectorStorageError(f"トークン数は正の整数である必要があります: {self.token_count}")
        
        # 座標データの検証
        for pos_name, pos_data in [("start_pos", self.start_pos), ("end_pos", self.end_pos)]:
            if pos_data is not None:
                if not isinstance(pos_data, dict):
                    raise VectorStorageError(f"{pos_name}は辞書形式である必要があります")
                
                required_keys = {"x", "y"}
                if not required_keys.issubset(pos_data.keys()):
                    raise VectorStorageError(f"{pos_name}にはx, yキーが必要です")
                
                for key in required_keys:
                    if not isinstance(pos_data[key], (int, float)):
                        raise VectorStorageError(f"{pos_name}.{key}は数値である必要があります")
        
        # 埋め込みベクトルの詳細検証
        self._validate_embedding()
    
    def _validate_embedding(self) -> None:
        """埋め込みベクトルの詳細検証"""
        if not self.embedding:
            raise VectorStorageError("埋め込みベクトルが空です")
        
        if not isinstance(self.embedding, list):
            raise VectorStorageError("埋め込みベクトルはリスト形式である必要があります")
        
        if len(self.embedding) != 1536:
            raise VectorStorageError(
                f"埋め込みベクトルは1536次元である必要があります。"
                f"現在: {len(self.embedding)}次元"
            )
        
        # ベクトルの数値検証（バッチ処理）
        for i, value in enumerate(self.embedding):
            if not isinstance(value, (int, float)):
                raise VectorStorageError(
                    f"埋め込みベクトルのインデックス {i} が数値ではありません: {type(value)}"
                )
            
            if math.isnan(value):
                raise VectorStorageError(
                    f"埋め込みベクトルのインデックス {i} にNaN値が含まれています"
                )
            
            if math.isinf(value):
                raise VectorStorageError(
                    f"埋め込みベクトルのインデックス {i} に無限大値が含まれています"
                )
        
        # ベクトルのノルム検証（異常値検出）
        vector_norm = math.sqrt(sum(x * x for x in self.embedding))
        if vector_norm == 0:
            raise VectorStorageError("埋め込みベクトルのノルムがゼロです")
        
        if vector_norm > 1000:  # 異常に大きなベクトル
            raise VectorStorageError(f"埋め込みベクトルのノルムが異常に大きいです: {vector_norm}")
    
    def to_dict(self) -> Dict[str, Any]:
        """辞書形式に変換（データベース挿入用）"""
        return {
            "id": self.id,
            "document_id": self.document_id,
            "content": self.content,
            "filename": self.filename,
            "page_number": self.page_number,
            "chapter_number": self.chapter_number,
            "section_name": self.section_name,
            "start_pos": self.start_pos,
            "end_pos": self.end_pos,
            "embedding": self.embedding,
            "token_count": self.token_count,
            "created_at": self.created_at.isoformat() if isinstance(self.created_at, datetime) else self.created_at
        }


@dataclass
class BatchResult:
    """バッチ処理結果"""
    success_count: int
    failure_count: int
    total_count: int
    failed_ids: List[str]
    errors: List[str]
    
    @property
    def success_rate(self) -> float:
        """成功率を計算"""
        if self.total_count == 0:
            return 0.0
        return self.success_count / self.total_count
    
    @property
    def is_complete_success(self) -> bool:
        """全件成功かどうか"""
        return self.failure_count == 0
    
    @property
    def is_complete_failure(self) -> bool:
        """全件失敗かどうか"""
        return self.success_count == 0


class VectorStorageError(Exception):
    """ベクトルストレージエラー"""
    pass


class VectorStorage:
    """ベクトルストレージ操作クラス"""
    
    def __init__(
        self,
        supabase_url: str,
        supabase_key: str,
        batch_size: int = 100
    ) -> None:
        """
        初期化
        
        Args:
            supabase_url: Supabase URL
            supabase_key: Supabase APIキー
            batch_size: バッチ処理サイズ
        """
        self.supabase_url = supabase_url
        self.supabase_key = supabase_key
        self.batch_size = batch_size
        
        # Supabaseクライアント初期化
        try:
            from supabase import create_client
            self.client = create_client(supabase_url, supabase_key)
        except ImportError:
            self.client = None
            logger.warning("Supabaseクライアントの初期化に失敗しました")
        
        logger.info(f"VectorStorage初期化完了: batch_size={batch_size}")
    
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
        if not chunks:
            raise VectorStorageError("保存するチャンクが空です")
        
        self._ensure_client_available()
        
        logger.info(f"バッチ保存開始: {len(chunks)}件, バッチサイズ: {self.batch_size}")
        
        result = BatchResult(
            success_count=0,
            failure_count=0,
            total_count=len(chunks),
            failed_ids=[],
            errors=[]
        )
        
        # バッチ単位で処理
        for i in range(0, len(chunks), self.batch_size):
            batch = chunks[i:i + self.batch_size]
            batch_num = (i // self.batch_size) + 1
            total_batches = ((len(chunks) - 1) // self.batch_size) + 1
            
            logger.debug(f"バッチ {batch_num}/{total_batches} 処理開始: {len(batch)}件")
            
            try:
                # チャンクデータの事前検証と変換
                valid_records = []
                for chunk in batch:
                    try:
                        # __post_init__で既に検証済みだが、念のため再検証
                        chunk.validate()
                        valid_records.append(chunk.to_dict())
                    except VectorStorageError as e:
                        result.failure_count += 1
                        result.failed_ids.append(chunk.id)
                        result.errors.append(f"チャンク {chunk.id} の検証エラー: {str(e)}")
                        logger.warning(f"チャンク検証失敗 {chunk.id}: {str(e)}")
                
                # 有効なレコードをデータベースに一括挿入
                if valid_records:
                    try:
                        db_result = self.client.table("document_chunks").insert(valid_records).execute()
                        result.success_count += len(valid_records)
                        logger.debug(f"バッチ {batch_num} 保存成功: {len(valid_records)}件")
                    except Exception as db_error:
                        # データベースエラーの場合、バッチ全体が失敗
                        for record in valid_records:
                            result.failure_count += 1
                            result.failed_ids.append(record["id"])
                        
                        error_msg = f"バッチ {batch_num} データベース保存エラー: {str(db_error)}"
                        result.errors.append(error_msg)
                        logger.error(error_msg, exc_info=True)
                
            except Exception as e:
                # 予期しないエラー
                for chunk in batch:
                    result.failure_count += 1
                    result.failed_ids.append(chunk.id)
                
                error_msg = f"バッチ {batch_num} 予期しないエラー: {str(e)}"
                result.errors.append(error_msg)
                logger.error(error_msg, exc_info=True)
        
        logger.info(
            f"バッチ保存完了: 成功{result.success_count}件, "
            f"失敗{result.failure_count}件, 成功率{result.success_rate:.2%}"
        )
        
        return result
    
    def _ensure_client_available(self) -> None:
        """Supabaseクライアントの可用性を確認"""
        if not self.client:
            raise VectorStorageError("Supabaseクライアントが初期化されていません")
    
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
            
        Raises:
            VectorStorageError: 更新エラーの場合
        """
        if not updates:
            raise VectorStorageError("更新データが空です")
        
        if not self.client:
            raise VectorStorageError("Supabaseクライアントが初期化されていません")
        
        success_count = 0
        failure_count = 0
        failed_ids = []
        errors = []
        
        for update in updates:
            try:
                # 更新データの検証
                chunk_id = update.get("id")
                embedding = update.get("embedding")
                
                if not chunk_id:
                    raise VectorStorageError("更新対象のIDが指定されていません")
                
                if not embedding or len(embedding) != 1536:
                    raise VectorStorageError("無効な埋め込みベクトルです")
                
                # データベース更新
                result = self.client.table("document_chunks").update({
                    "embedding": embedding,
                    "updated_at": "now()"
                }).eq("id", chunk_id).execute()
                
                success_count += 1
                
            except Exception as e:
                failure_count += 1
                failed_ids.append(update.get("id", "unknown"))
                error_msg = f"埋め込み更新エラー: {str(e)}"
                errors.append(error_msg)
                logger.error(error_msg)
        
        total_count = len(updates)
        
        result = BatchResult(
            success_count=success_count,
            failure_count=failure_count,
            total_count=total_count,
            failed_ids=failed_ids,
            errors=errors
        )
        
        logger.info(f"埋め込み更新完了: 成功{success_count}件, 失敗{failure_count}件")
        
        return result
    
    def check_duplicates(self, chunk_ids: List[str]) -> List[str]:
        """
        重複チャンクIDをチェック
        
        Args:
            chunk_ids: チェック対象のチャンクIDリスト
            
        Returns:
            List[str]: 既存のチャンクIDリスト
            
        Raises:
            VectorStorageError: チェックエラーの場合
        """
        if not chunk_ids:
            return []
        
        if not self.client:
            raise VectorStorageError("Supabaseクライアントが初期化されていません")
        
        try:
            # データベースで既存IDをチェック
            result = self.client.table("document_chunks").select("id").in_("id", chunk_ids).execute()
            
            existing_ids = [row["id"] for row in result.data]
            
            logger.info(f"重複チェック完了: {len(existing_ids)}/{len(chunk_ids)}件が既存")
            
            return existing_ids
            
        except Exception as e:
            error_msg = f"重複チェックエラー: {str(e)}"
            logger.error(error_msg)
            raise VectorStorageError(error_msg) from e
    
    def delete_chunks_batch(self, chunk_ids: List[str]) -> BatchResult:
        """
        チャンクをバッチで削除
        
        Args:
            chunk_ids: 削除対象のチャンクIDリスト
            
        Returns:
            BatchResult: バッチ処理結果
            
        Raises:
            VectorStorageError: 削除エラーの場合
        """
        if not chunk_ids:
            raise VectorStorageError("削除するチャンクIDが空です")
        
        if not self.client:
            raise VectorStorageError("Supabaseクライアントが初期化されていません")
        
        success_count = 0
        failure_count = 0
        failed_ids = []
        errors = []
        
        # バッチ単位で削除
        for i in range(0, len(chunk_ids), self.batch_size):
            batch_ids = chunk_ids[i:i + self.batch_size]
            
            try:
                result = self.client.table("document_chunks").delete().in_("id", batch_ids).execute()
                success_count += len(batch_ids)
                logger.info(f"バッチ削除成功: {len(batch_ids)}件")
                
            except Exception as e:
                failure_count += len(batch_ids)
                failed_ids.extend(batch_ids)
                error_msg = f"バッチ削除エラー: {str(e)}"
                errors.append(error_msg)
                logger.error(error_msg)
        
        total_count = len(chunk_ids)
        
        result = BatchResult(
            success_count=success_count,
            failure_count=failure_count,
            total_count=total_count,
            failed_ids=failed_ids,
            errors=errors
        )
        
        logger.info(f"バッチ削除完了: 成功{success_count}件, 失敗{failure_count}件")
        
        return result
    
    def get_storage_stats(self) -> Dict[str, Any]:
        """
        ストレージ統計情報を取得
        
        Returns:
            Dict[str, Any]: 統計情報
            
        Raises:
            VectorStorageError: 取得エラーの場合
        """
        if not self.client:
            raise VectorStorageError("Supabaseクライアントが初期化されていません")
        
        try:
            # チャンク数をカウント
            chunk_result = self.client.table("document_chunks").select("id", count="exact").execute()
            total_chunks = chunk_result.count or 0
            
            # 文書別チャンク数を取得
            doc_result = self.client.table("document_chunks").select("document_id").execute()
            doc_counts = {}
            for row in doc_result.data:
                doc_id = row["document_id"]
                doc_counts[doc_id] = doc_counts.get(doc_id, 0) + 1
            
            stats = {
                "total_chunks": total_chunks,
                "total_documents": len(doc_counts),
                "avg_chunks_per_document": total_chunks / len(doc_counts) if doc_counts else 0,
                "batch_size": self.batch_size,
                "timestamp": "now()"
            }
            
            logger.info("ストレージ統計情報取得完了")
            return stats
            
        except Exception as e:
            error_msg = f"統計情報取得エラー: {str(e)}"
            logger.error(error_msg)
            raise VectorStorageError(error_msg) from e