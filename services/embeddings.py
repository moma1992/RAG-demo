"""
OpenAI Embeddings Service
Issue #54: OpenAI text-embedding-3-small完全実装

OpenAI text-embedding-3-smallを使用したベクトル埋め込み生成サービス
"""

from typing import List, Dict, Any, Optional
import logging
import time
import asyncio
from datetime import datetime
import openai
import tiktoken

# models.embeddingから完全なデータモデルをインポート
from models.embedding import (
    EmbeddingResult,
    EmbeddingBatch,
    EmbeddingValidationError,
    OPENAI_EMBEDDING_DIMENSION
)

# トークンカウントユーティリティ
from utils.tokenizer import TokenCounter

# Supabase統合用（Issue #48要件）
from services.vector_store import VectorStore

logger = logging.getLogger(__name__)

# Issue #54専用のレスポンス時間追跡データクラス
from dataclasses import dataclass

@dataclass  
class BatchEmbeddingResult:
    """バッチ埋め込み結果（Issue #54互換性）"""
    embeddings: List[List[float]]
    total_tokens: int
    model: str

class EmbeddingService:
    """OpenAI Embeddings サービスクラス"""
    
    def __init__(self, api_key: str, model: str = "text-embedding-3-small", timeout: Optional[int] = None, async_mode: bool = False) -> None:
        """
        OpenAI Embeddings Service初期化
        
        Args:
            api_key: OpenAI APIキー
            model: 使用するモデル名
            timeout: タイムアウト秒数
            async_mode: 非同期モード
            
        Raises:
            ValueError: APIキーが空または不正形式の場合
            EmbeddingError: OpenAIクライアント初期化失敗の場合
        """
        if not api_key:
            raise ValueError("APIキーが空です")
        
        if not api_key.startswith("sk-"):
            raise ValueError("APIキー形式が不正です")
        
        self.api_key = api_key
        self.model = model
        self.timeout = timeout
        self.async_mode = async_mode
        
        # Issue #53のTokenCounterと統合
        self.token_counter = TokenCounter(model)
        
        try:
            if async_mode:
                self.client = openai.AsyncOpenAI(
                    api_key=api_key,
                    timeout=timeout
                )
                self.async_client = self.client
                self.sync_client = None
            else:
                self.client = openai.OpenAI(
                    api_key=api_key,
                    timeout=timeout
                )
                self.sync_client = self.client
                self.async_client = None
            
            # トークンエンコーダー初期化（フォールバック用）
            try:
                self.tokenizer = tiktoken.encoding_for_model("gpt-3.5-turbo")
            except Exception:
                self.tokenizer = None
            
            logger.info(f"EmbeddingService初期化完了: model={model}")
            
        except Exception as e:
            logger.error(f"OpenAIクライアント初期化エラー: {str(e)}")
            raise EmbeddingError(f"OpenAIクライアント初期化に失敗しました: {str(e)}") from e
    
    def generate_embedding(self, text: str) -> EmbeddingResult:
        """
        単一テキストの埋め込みを生成
        
        Args:
            text: 埋め込み対象テキスト
            
        Returns:
            EmbeddingResult: 埋め込み結果（Issue #53データモデル使用）
            
        Raises:
            ValueError: テキストが空、None、または長すぎる場合
            EmbeddingError: 埋め込み生成エラーの場合
        """
        # 入力検証
        if text is None:
            raise ValueError("テキストがNoneです")
        
        if not text.strip():
            raise ValueError("テキストが空です")
        
        # トークン数チェック（Issue #53のTokenCounterを使用）
        token_count = self.token_counter.count_tokens(text)
        if token_count > 8192:
            raise ValueError("テキストが長すぎます（8192トークン制限）")
        
        logger.info(f"埋め込み生成開始: {len(text)}文字, {token_count}トークン")
        
        start_time = time.time()
        
        try:
            response = self.client.embeddings.create(
                input=text,
                model=self.model
            )
            
            end_time = time.time()
            response_time = end_time - start_time
            
            # Issue #53のEmbeddingResultデータクラスを使用
            result = EmbeddingResult(
                text=text,
                embedding=response.data[0].embedding,
                token_count=response.usage.total_tokens,
                model=self.model,
                created_at=datetime.now()
            )
            
            # Issue #54要件：response_time追跡
            result.response_time = response_time
            
            logger.info(f"埋め込み生成完了: {response_time:.3f}秒")
            return result
            
        except EmbeddingValidationError as e:
            logger.error(f"埋め込み検証エラー: {str(e)}", exc_info=True)
            raise EmbeddingError(f"埋め込み検証エラー: {str(e)}") from e
        except Exception as e:
            # OpenAI例外の種類を判定
            error_name = e.__class__.__name__
            error_message = str(e)
            
            if error_name == "AuthenticationError":
                logger.error(f"認証エラー: {error_message}")
                raise EmbeddingError(f"認証に失敗しました: {error_message}") from e
            elif error_name == "RateLimitError":
                logger.error(f"レート制限エラー: {error_message}")
                if "quota" in error_message.lower():
                    raise EmbeddingError(f"APIクォータを超過しました: {error_message}") from e
                else:
                    raise EmbeddingError(f"レート制限に達しました: {error_message}") from e
            elif error_name == "Timeout" or "timeout" in error_message.lower():
                logger.error(f"タイムアウトエラー: {error_message}")
                raise EmbeddingError(f"リクエストがタイムアウトしました: {error_message}") from e
            elif error_name == "InternalServerError":
                logger.error(f"サーバーエラー: {error_message}")
                raise EmbeddingError(f"サーバーエラーが発生しました: {error_message}") from e
            elif "connection" in error_message.lower():
                logger.error(f"ネットワーク接続エラー: {error_message}")
                raise EmbeddingError(f"ネットワーク接続エラーが発生しました: {error_message}") from e
            else:
                logger.error(f"予期しないエラー: {error_message}", exc_info=True)
                raise EmbeddingError(f"埋め込み生成中にエラーが発生しました: {error_message}") from e
    
    async def generate_embedding_async(self, text: str) -> EmbeddingResult:
        """
        非同期で単一テキストの埋め込みを生成
        
        Args:
            text: 埋め込み対象テキスト
            
        Returns:
            EmbeddingResult: 埋め込み結果
            
        Raises:
            ValueError: テキストが空、None、または長すぎる場合
            EmbeddingError: 埋め込み生成エラーの場合
        """
        if not self.async_mode or self.async_client is None:
            raise EmbeddingError("非同期モードが有効化されていません")
        
        # 入力検証
        if text is None:
            raise ValueError("テキストがNoneです")
        
        if not text.strip():
            raise ValueError("テキストが空です")
        
        token_count = self.token_counter.count_tokens(text)
        if token_count > 8192:
            raise ValueError("テキストが長すぎます（8192トークン制限）")
        
        logger.info(f"非同期埋め込み生成開始: {len(text)}文字")
        
        start_time = time.time()
        
        try:
            response = await self.async_client.embeddings.create(
                input=text,
                model=self.model
            )
            
            end_time = time.time()
            response_time = end_time - start_time
            
            result = EmbeddingResult(
                text=text,
                embedding=response.data[0].embedding,
                token_count=response.usage.total_tokens,
                model=self.model,
                created_at=datetime.now()
            )
            result.response_time = response_time
            
            logger.info(f"非同期埋め込み生成完了: {response_time:.3f}秒")
            return result
            
        except Exception as e:
            logger.error(f"非同期埋め込み生成エラー: {str(e)}")
            raise EmbeddingError(f"非同期埋め込み生成中にエラーが発生しました: {str(e)}") from e
    
    def generate_batch_embeddings(self, texts: List[str]) -> BatchEmbeddingResult:
        """
        バッチで埋め込みを生成（Issue #54互換性）
        
        Args:
            texts: 埋め込み対象テキストリスト
            
        Returns:
            BatchEmbeddingResult: バッチ埋め込み結果
            
        Raises:
            ValueError: テキストリストが空または制限超過の場合
            EmbeddingError: 埋め込み生成エラーの場合
        """
        if not texts:
            raise ValueError("テキストリストが空です")
        
        if len(texts) > 2048:
            raise ValueError("バッチサイズが制限を超えています")
        
        logger.info(f"バッチ埋め込み生成開始: {len(texts)}件")
        
        try:
            response = self.client.embeddings.create(
                input=texts,
                model=self.model
            )
            
            embeddings = [item.embedding for item in response.data]
            
            result = BatchEmbeddingResult(
                embeddings=embeddings,
                total_tokens=response.usage.total_tokens,
                model=self.model
            )
            
            logger.info(f"バッチ埋め込み生成完了: {len(embeddings)}件")
            return result
            
        except Exception as e:
            logger.error(f"バッチ埋め込み生成エラー: {str(e)}", exc_info=True)
            raise EmbeddingError(f"バッチ埋め込み生成中にエラーが発生しました: {str(e)}") from e
    
    def create_batch_embeddings(self, texts: List[str]) -> EmbeddingBatch:
        """
        バッチで埋め込みを生成（Issue #53互換性）
        
        Args:
            texts: 埋め込み対象テキストリスト
            
        Returns:
            EmbeddingBatch: バッチ埋め込み結果
            
        Raises:
            ValueError: テキストリストが空または制限超過の場合
            EmbeddingError: 埋め込み生成エラーの場合
        """
        if not texts:
            raise ValueError("テキストリストが空です")
        
        logger.info(f"バッチ埋め込み生成開始: {len(texts)}件")
        
        try:
            # 各テキストのEmbeddingResultを生成
            results = []
            for text in texts:
                # 実際のOpenAI APIを呼び出し
                response = self.client.embeddings.create(
                    input=text,
                    model=self.model
                )
                
                result = EmbeddingResult(
                    text=text,
                    embedding=response.data[0].embedding,
                    token_count=response.usage.total_tokens,
                    model=self.model,
                    created_at=datetime.now()
                )
                results.append(result)
            
            # EmbeddingBatchオブジェクトを作成
            batch = EmbeddingBatch(results)
            
            logger.info(f"バッチ埋め込み生成完了: {len(results)}件")
            return batch
            
        except EmbeddingValidationError as e:
            logger.error(f"バッチ埋め込み検証エラー: {str(e)}", exc_info=True)
            raise EmbeddingError(f"バッチ埋め込み検証エラー: {str(e)}") from e
        except Exception as e:
            logger.error(f"バッチ埋め込み生成エラー: {str(e)}", exc_info=True)
            raise EmbeddingError(f"バッチ埋め込み生成中にエラーが発生しました: {str(e)}") from e
    
    def estimate_tokens(self, text: str) -> int:
        """
        テキストのトークン数を推定
        
        Args:
            text: 推定対象テキスト
            
        Returns:
            int: 推定トークン数
            
        Raises:
            ValueError: テキストが空の場合
        """
        if not text:
            raise ValueError("テキストが空です")
        
        # Issue #53のTokenCounterを優先使用
        return self.token_counter.count_tokens(text)
    
    def validate_embedding_dimension(self, embedding: List[float]) -> bool:
        """
        埋め込み次元数を検証
        
        Args:
            embedding: 検証対象埋め込み
            
        Returns:
            bool: 検証結果
        """
        # models.embeddingの定数を使用
        return len(embedding) == OPENAI_EMBEDDING_DIMENSION
    
    def get_model_info(self) -> Dict[str, Any]:
        """
        モデル情報を取得
        
        Returns:
            Dict[str, Any]: モデル情報
        """
        return {
            "model": self.model,
            "dimension": OPENAI_EMBEDDING_DIMENSION,
            "max_tokens": 8192,
            "async_mode": self.async_mode,
            "timeout": self.timeout
        }
    
    def calculate_embedding_cost(self, tokens: int) -> float:
        """
        埋め込みコストを計算
        
        Args:
            tokens: トークン数
            
        Returns:
            float: コスト（USD）
        """
        # OpenAI text-embedding-3-small価格: $0.00002 / 1K tokens
        cost_per_1k_tokens = 0.00002
        return (tokens / 1000) * cost_per_1k_tokens
    
    def calculate_cosine_similarity(
        self, 
        embedding1: List[float], 
        embedding2: List[float]
    ) -> float:
        """
        コサイン類似度を計算
        
        Args:
            embedding1: 埋め込み1
            embedding2: 埋め込み2
            
        Returns:
            float: コサイン類似度
            
        Raises:
            ValueError: 埋め込み次元が一致しない場合
        """
        if len(embedding1) != len(embedding2):
            raise ValueError("埋め込みの次元数が一致しません")
        
        # ドット積計算
        dot_product = sum(a * b for a, b in zip(embedding1, embedding2))
        
        # ノルム計算
        norm1 = sum(a * a for a in embedding1) ** 0.5
        norm2 = sum(b * b for b in embedding2) ** 0.5
        
        if norm1 == 0 or norm2 == 0:
            return 0.0
        
        return dot_product / (norm1 * norm2)
    
    def store_embeddings_to_supabase(
        self,
        texts: List[str],
        supabase_url: str,
        supabase_key: str,
        document_id: str,
        filename: str = "document.pdf"
    ) -> List[str]:
        """
        埋め込みを生成してSupabaseに保存（Issue #48要件）
        
        Args:
            texts: 埋め込み対象テキストリスト
            supabase_url: Supabase URL
            supabase_key: Supabase APIキー
            document_id: 文書ID
            filename: ファイル名
            
        Returns:
            List[str]: 保存されたチャンクIDリスト
            
        Raises:
            ValueError: 無効な入力パラメータの場合
            EmbeddingError: 埋め込み生成またはSupabase保存エラーの場合
        """
        logger.info(f"Supabase埋め込み保存開始: {len(texts)}件のテキスト")
        
        # 入力検証
        if not texts:
            raise ValueError("テキストリストが空です")
        
        if not supabase_url or not supabase_key or not document_id:
            raise ValueError("Supabaseパラメータが不正です")
        
        try:
            # VectorStoreインスタンスを作成
            vector_store = VectorStore(supabase_url, supabase_key)
            
            # 先に文書レコードを作成
            document_data = {
                "filename": filename,
                "original_filename": filename,
                "file_size": sum(len(text) for text in texts) * 4,  # 概算
                "total_pages": len(texts),
                "processing_status": "completed"
            }
            stored_doc_id = vector_store.store_document(document_data, document_id)
            
            # 各テキストの埋め込みを生成
            embedding_results = []
            chunk_data = []
            
            for i, text in enumerate(texts):
                # 埋め込み生成
                embedding_result = self.generate_embedding(text)
                embedding_results.append(embedding_result)
                
                # チャンクデータ準備
                chunk = {
                    "content": text,
                    "filename": filename,
                    "page_number": i + 1,  # 仮のページ番号
                    "token_count": embedding_result.token_count,
                    "embedding": embedding_result.embedding
                }
                chunk_data.append(chunk)
            
            # Supabaseにチャンクを保存（提供されたdocument_idを使用）
            chunk_ids = vector_store.store_chunks(chunk_data, stored_doc_id)
            
            logger.info(f"Supabase埋め込み保存完了: {len(chunk_ids)}件")
            return chunk_ids
            
        except Exception as e:
            logger.error(f"Supabase埋め込み保存エラー: {str(e)}", exc_info=True)
            raise EmbeddingError(f"Supabase保存中にエラーが発生しました: {str(e)}") from e
    
    def batch_store_embeddings_to_supabase(
        self,
        texts: List[str],
        supabase_url: str,
        supabase_key: str,
        document_id: str,
        filename: str = "document.pdf",
        batch_size: int = 100
    ) -> List[str]:
        """
        バッチで埋め込みを生成してSupabaseに保存（Issue #48要件）
        
        Args:
            texts: 埋め込み対象テキストリスト
            supabase_url: Supabase URL
            supabase_key: Supabase APIキー
            document_id: 文書ID
            filename: ファイル名
            batch_size: バッチサイズ
            
        Returns:
            List[str]: 保存されたチャンクIDリスト
            
        Raises:
            ValueError: 無効な入力パラメータの場合
            EmbeddingError: バッチ埋め込み生成またはSupabase保存エラーの場合
        """
        logger.info(f"Supabaseバッチ埋め込み保存開始: {len(texts)}件のテキスト")
        
        # 入力検証
        if not texts:
            raise ValueError("テキストリストが空です")
        
        if batch_size <= 0 or batch_size > 2048:
            raise ValueError("バッチサイズが不正です（1-2048）")
        
        try:
            # VectorStoreインスタンスを作成
            vector_store = VectorStore(supabase_url, supabase_key)
            
            # 先に文書レコードを作成
            document_data = {
                "filename": filename,
                "original_filename": filename,
                "file_size": sum(len(text) for text in texts) * 4,  # 概算
                "total_pages": len(texts),
                "processing_status": "completed"
            }
            stored_doc_id = vector_store.store_document(document_data, document_id)
            
            all_chunk_ids = []
            
            # バッチごとに処理
            for i in range(0, len(texts), batch_size):
                batch_texts = texts[i:i+batch_size]
                
                # バッチ埋め込み生成
                batch_result = self.generate_batch_embeddings(batch_texts)
                
                # チャンクデータ準備
                chunk_data = []
                for j, (text, embedding) in enumerate(zip(batch_texts, batch_result.embeddings)):
                    chunk = {
                        "content": text,
                        "filename": filename,
                        "page_number": i + j + 1,  # 連続ページ番号
                        "token_count": self.token_counter.count_tokens(text),  # 正確なトークン数
                        "embedding": embedding
                    }
                    chunk_data.append(chunk)
                
                # Supabaseにバッチ保存（提供されたdocument_idを使用）
                batch_chunk_ids = vector_store.store_chunks(chunk_data, stored_doc_id)
                all_chunk_ids.extend(batch_chunk_ids)
                
                logger.info(f"バッチ {i//batch_size + 1} 保存完了: {len(batch_texts)}件")
            
            logger.info(f"Supabaseバッチ埋め込み保存完了: {len(all_chunk_ids)}件")
            return all_chunk_ids
            
        except Exception as e:
            logger.error(f"Supabaseバッチ埋め込み保存エラー: {str(e)}", exc_info=True)
            raise EmbeddingError(f"バッチSupabase保存中にエラーが発生しました: {str(e)}") from e


class EmbeddingError(Exception):
    """埋め込みエラー"""
    pass