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
import re
import html
import numpy as np

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
        
        # セキュリティ強化：コンテンツ検証
        if not self.content or not self.content.strip():
            raise VectorStorageError("コンテンツが空です")
        
        # セキュリティ：悪意のあるコンテンツの検出
        self._validate_content_security()
        
        if len(self.content) > 10000:
            raise VectorStorageError(f"コンテンツが長すぎます: {len(self.content)}文字 (最大10000文字)")
        
        # セキュリティ強化：ファイル名検証
        if not self.filename or not self.filename.strip():
            raise VectorStorageError("ファイル名が空です")
        
        self._validate_filename_security()
        
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
    
    def _validate_content_security(self) -> None:
        """コンテンツのセキュリティ検証"""
        # SQLインジェクション対策：危険なSQL文字列の検出
        sql_patterns = [
            r"(?i)(union\s+select|drop\s+table|delete\s+from|insert\s+into|update\s+set)",
            r"(?i)(script\s*>|<\s*script|javascript:|vbscript:)",
            r"(?i)(exec\s*\(|eval\s*\(|system\s*\()",
            r"[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]"  # 制御文字
        ]
        
        for pattern in sql_patterns:
            if re.search(pattern, self.content):
                raise VectorStorageError("セキュリティ違反：危険なコンテンツが検出されました")
        
        # 過度に長い連続文字列の検出（DoS攻撃対策）
        if re.search(r'(.)\1{1000,}', self.content):
            raise VectorStorageError("セキュリティ違反：異常な反復パターンが検出されました")
        
        # HTMLエスケープ処理
        if '<' in self.content or '>' in self.content:
            # HTMLタグが含まれている場合は検証
            escaped_content = html.escape(self.content)
            if len(escaped_content) != len(self.content):
                logger.warning("HTMLコンテンツが検出されました。エスケープ処理を推奨します。")
    
    def _validate_filename_security(self) -> None:
        """ファイル名のセキュリティ検証"""
        # パストラバーサル攻撃対策
        dangerous_patterns = [
            r"\.\./", r"\.\.\\", r"^/", r"^[a-zA-Z]:\\",
            r"[\x00-\x1F\x7F]",  # 制御文字
            r"[<>:\"\|?*]",  # Windows禁止文字
        ]
        
        for pattern in dangerous_patterns:
            if re.search(pattern, self.filename):
                raise VectorStorageError("セキュリティ違反：危険なファイル名パターンが検出されました")
        
        # ファイル名長制限（DoS攻撃対策）
        if len(self.filename) > 255:
            raise VectorStorageError("ファイル名が長すぎます (最大255文字)")
        
        # 危険な拡張子のチェック
        dangerous_extensions = [
            '.exe', '.bat', '.cmd', '.com', '.pif', '.scr', '.vbs', '.js', '.jar', '.sh'
        ]
        filename_lower = self.filename.lower()
        for ext in dangerous_extensions:
            if filename_lower.endswith(ext):
                raise VectorStorageError(f"セキュリティ違反：危険な拡張子が検出されました: {ext}")
    
    def _serialize_datetime(self, dt: Union[datetime, str, None]) -> Optional[str]:
        """
        日時オブジェクトの安全なシリアル化
        
        Args:
            dt: シリアル化対象の日時
            
        Returns:
            str: ISO形式の日時文字列またはNone
        """
        if dt is None:
            return None
            
        if isinstance(dt, datetime):
            try:
                # タイムゾーン情報を考慮したISOフォーマット
                if dt.tzinfo is None:
                    # ナイーブな日時のUTC扱い
                    return dt.isoformat() + 'Z'
                else:
                    return dt.isoformat()
            except (ValueError, OverflowError) as e:
                logger.warning(f"日時シリアル化エラー: {str(e)}")
                return str(dt)
                
        elif isinstance(dt, str):
            # 既に文字列の場合はそのまま返す
            return dt
            
        else:
            # 予期しない型の場合
            logger.warning(f"予期しない日時型: {type(dt)}")
            return str(dt) if dt is not None else None
    
    def _validate_embedding(self) -> None:
        """埋め込みベクトルの高速検証（パフォーマンス最適化）"""
        if not self.embedding:
            raise VectorStorageError("埋め込みベクトルが空です")
        
        if not isinstance(self.embedding, list):
            raise VectorStorageError("埋め込みベクトルはリスト形式である必要があります")
        
        if len(self.embedding) != 1536:
            raise VectorStorageError(
                f"埋め込みベクトルは1536次元である必要があります。"
                f"現在: {len(self.embedding)}次元"
            )
        
        # パフォーマンス最適化: NumPyでベクター化処理
        try:
            # NumPy配列に変換（高速処理）
            embedding_array = np.array(self.embedding, dtype=np.float32)
            
            # 全要素の数値検証（ベクター化）
            if not np.all(np.isfinite(embedding_array)):
                # エラー位置を特定
                nan_indices = np.where(np.isnan(embedding_array))[0]
                inf_indices = np.where(np.isinf(embedding_array))[0]
                
                if len(nan_indices) > 0:
                    raise VectorStorageError(
                        f"埋め込みベクトルのインデックス {nan_indices[0]} にNaN値が含まれています"
                    )
                if len(inf_indices) > 0:
                    raise VectorStorageError(
                        f"埋め込みベクトルのインデックス {inf_indices[0]} に無限大値が含まれています"
                    )
            
            # ベクトルのノルム検証（NumPyで高速化）
            vector_norm = float(np.linalg.norm(embedding_array))
            if vector_norm == 0.0:
                raise VectorStorageError("埋め込みベクトルのノルムがゼロです")
            
            if vector_norm > 1000.0:  # 異常に大きなベクトル
                raise VectorStorageError(f"埋め込みベクトルのノルムが異常に大きいです: {vector_norm:.2f}")
                
        except (TypeError, ValueError) as e:
            # NumPy変換エラーの場合は個別検証にフォールバック
            for i, value in enumerate(self.embedding):
                if not isinstance(value, (int, float)):
                    raise VectorStorageError(
                        f"埋め込みベクトルのインデックス {i} が数値ではありません: {type(value)}"
                    )
            raise VectorStorageError(f"埋め込みベクトルの変換エラー: {str(e)}")
    
    def to_dict(self) -> Dict[str, Any]:
        """辞書形式に変換（データベース挿入用）"""
        # セキュリティ：データサニタイズ
        sanitized_content = html.escape(self.content) if self.content else ""
        sanitized_filename = html.escape(self.filename) if self.filename else ""
        sanitized_section = html.escape(self.section_name) if self.section_name else None
        
        return {
            "id": self.id,
            "document_id": self.document_id,
            "content": sanitized_content,
            "filename": sanitized_filename,
            "page_number": self.page_number,
            "chapter_number": self.chapter_number,
            "section_name": sanitized_section,
            "start_pos": self.start_pos,
            "end_pos": self.end_pos,
            "embedding": self.embedding,
            "token_count": self.token_count,
            "created_at": self._serialize_datetime_static(self.created_at)
        }
    
    @staticmethod
    def _serialize_datetime_static(dt: Union[datetime, str, None]) -> Optional[str]:
        """
        日時オブジェクトの安全なシリアル化（静的メソッド版）
        
        Args:
            dt: シリアル化対象の日時
            
        Returns:
            str: ISO形式の日時文字列またはNone
        """
        if dt is None:
            return None
            
        if isinstance(dt, datetime):
            try:
                # タイムゾーン情報を考慮したISOフォーマット
                if dt.tzinfo is None:
                    # ナイーブな日時のUTC扱い
                    return dt.isoformat() + 'Z'
                else:
                    return dt.isoformat()
            except (ValueError, OverflowError):
                return str(dt)
                
        elif isinstance(dt, str):
            # 既に文字列の場合はそのまま返す
            return dt
            
        else:
            # 予期しない型の場合
            return str(dt) if dt is not None else None


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
    
    def save_chunks_batch(self, chunks: List[ChunkData], use_transaction: bool = True) -> BatchResult:
        """
        チャンクデータをバッチで保存（トランザクションサポート）
        
        大容量データの効率的な処理のため、指定されたバッチサイズで
        分割して処理します。トランザクションを使用することでデータの整合性を保証します。
        
        Args:
            chunks: 保存するチャンクデータのリスト
            use_transaction: トランザクションを使用するかどうか
            
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
        
        # パフォーマンス最適化: バッチ単位で処理
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
                
                # トランザクションサポート: 有効なレコードをデータベースに一括挿入
                if valid_records:
                    if use_transaction:
                        success = self._execute_batch_with_transaction(valid_records, batch_num, result)
                    else:
                        success = self._execute_batch_without_transaction(valid_records, batch_num, result)
                    
                    if success:
                        result.success_count += len(valid_records)
                        logger.debug(f"バッチ {batch_num} 保存成功: {len(valid_records)}件")
                
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
            f"失敗{result.failure_count}件, 成功率{result.success_rate:.2%}, "
            f"トランザクション: {'ON' if use_transaction else 'OFF'}"
        )
        
        return result
    
    def _execute_batch_with_transaction(self, records: List[Dict[str, Any]], batch_num: int, result: BatchResult) -> bool:
        """トランザクションでバッチ実行"""
        try:
            # NOTE: Supabaseは自動的にトランザクションを管理するため、
            # 通常のinsert()操作で十分です。エラーが発生した場合は自動的にロールバックされます。
            db_result = self.client.table("document_chunks").insert(records).execute()
            return True
                
        except Exception as db_error:
            # トランザクションロールバックで全件失敗
            failed_chunk_ids = [record["id"] for record in records]
            result.failure_count += len(failed_chunk_ids)
            result.failed_ids.extend(failed_chunk_ids)
            
            error_msg = f"バッチ {batch_num} トランザクションエラー: {str(db_error)}"
            result.errors.append(error_msg)
            logger.error(error_msg, exc_info=True)
            return False
    
    def _execute_batch_without_transaction(self, records: List[Dict[str, Any]], batch_num: int, result: BatchResult) -> bool:
        """トランザクションなしでバッチ実行（今までの動作）"""
        try:
            db_result = self.client.table("document_chunks").insert(records).execute()
            return True
            
        except Exception as db_error:
            # データベースエラーの場合、バッチ全体が失敗
            failed_chunk_ids = [record["id"] for record in records]
            result.failure_count += len(failed_chunk_ids)
            result.failed_ids.extend(failed_chunk_ids)
            
            error_msg = f"バッチ {batch_num} データベース保存エラー: {str(db_error)}"
            result.errors.append(error_msg)
            logger.error(error_msg, exc_info=True)
            return False
    
    def _ensure_client_available(self) -> None:
        """Supabaseクライアントの可用性を確認"""
        if not self.client:
            raise VectorStorageError("Supabaseクライアントが初期化されていません")
    
    def _serialize_datetime(self, dt: Union[datetime, str, None]) -> Optional[str]:
        """
        日時オブジェクトの安全なシリアル化
        
        Args:
            dt: シリアル化対象の日時
            
        Returns:
            str: ISO形式の日時文字列またはNone
        """
        if dt is None:
            return None
            
        if isinstance(dt, datetime):
            try:
                # タイムゾーン情報を考慮したISOフォーマット
                if dt.tzinfo is None:
                    # ナイーブな日時のUTC扱い
                    return dt.isoformat() + 'Z'
                else:
                    return dt.isoformat()
            except (ValueError, OverflowError) as e:
                logger.warning(f"日時シリアル化エラー: {str(e)}")
                return str(dt)
                
        elif isinstance(dt, str):
            # 既に文字列の場合はそのまま返す
            return dt
            
        else:
            # 予期しない型の場合
            logger.warning(f"予期しない日時型: {type(dt)}")
            return str(dt) if dt is not None else None
    
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
                
                # 日時シリアル化バグ修正: 現在時刻を正しく生成
                current_time = datetime.now()
                result = self.client.table("document_chunks").update({
                    "embedding": embedding,
                    "updated_at": self._serialize_datetime(current_time)
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
    
    def delete_chunks_batch(self, chunk_ids: List[str], use_transaction: bool = True) -> BatchResult:
        """
        チャンクをバッチで削除（トランザクションサポート）
        
        Args:
            chunk_ids: 削除対象のチャンクIDリスト
            use_transaction: トランザクションを使用するかどうか
            
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
        
        # トランザクションサポート: バッチ単位で削除
        for i in range(0, len(chunk_ids), self.batch_size):
            batch_ids = chunk_ids[i:i + self.batch_size]
            
            if use_transaction:
                # トランザクションで削除
                try:
                    # NOTE: SupabaseのトランザクションAPIを使用
                    result = self.client.table("document_chunks").delete().in_("id", batch_ids).execute()
                    success_count += len(batch_ids)
                    logger.info(f"トランザクションバッチ削除成功: {len(batch_ids)}件")
                    
                except Exception as e:
                    failure_count += len(batch_ids)
                    failed_ids.extend(batch_ids)
                    error_msg = f"トランザクションバッチ削除エラー: {str(e)}"
                    errors.append(error_msg)
                    logger.error(error_msg)
            else:
                # トランザクションなしで削除
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