"""
OpenAI Embeddings Service
Issue #54: OpenAI text-embedding-3-small完全実装

OpenAI text-embedding-3-smallを使用したベクトル埋め込み生成サービス
"""

from typing import List, Dict, Any, Optional
import logging
import time
import asyncio
from dataclasses import dataclass
import openai
import tiktoken

logger = logging.getLogger(__name__)

@dataclass
class EmbeddingResult:
    """埋め込み結果"""
    embedding: List[float]
    token_count: int
    model: str
    response_time: Optional[float] = None

@dataclass  
class BatchEmbeddingResult:
    """バッチ埋め込み結果"""
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
        
        try:
            if async_mode:
                self.client = openai.AsyncOpenAI(
                    api_key=api_key,
                    timeout=timeout
                )
            else:
                self.client = openai.OpenAI(
                    api_key=api_key,
                    timeout=timeout
                )
            
            # トークンエンコーダー初期化
            self.tokenizer = tiktoken.encoding_for_model("gpt-3.5-turbo")
            
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
            EmbeddingResult: 埋め込み結果
            
        Raises:
            ValueError: テキストが空、None、または長すぎる場合
            EmbeddingError: 埋め込み生成エラーの場合
        """
        # 入力検証
        if text is None:
            raise ValueError("テキストがNoneです")
        
        if not text.strip():
            raise ValueError("テキストが空です")
        
        # トークン数チェック
        token_count = self.estimate_tokens(text)
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
            
            result = EmbeddingResult(
                embedding=response.data[0].embedding,
                token_count=response.usage.total_tokens,
                model=self.model,
                response_time=response_time
            )
            
            logger.info(f"埋め込み生成完了: {response_time:.3f}秒")
            return result
            
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
        if not self.async_mode:
            raise EmbeddingError("非同期モードが有効化されていません")
        
        # 入力検証
        if text is None:
            raise ValueError("テキストがNoneです")
        
        if not text.strip():
            raise ValueError("テキストが空です")
        
        token_count = self.estimate_tokens(text)
        if token_count > 8192:
            raise ValueError("テキストが長すぎます（8192トークン制限）")
        
        logger.info(f"非同期埋め込み生成開始: {len(text)}文字")
        
        start_time = time.time()
        
        try:
            response = await self.client.embeddings.create(
                input=text,
                model=self.model
            )
            
            end_time = time.time()
            response_time = end_time - start_time
            
            result = EmbeddingResult(
                embedding=response.data[0].embedding,
                token_count=response.usage.total_tokens,
                model=self.model,
                response_time=response_time
            )
            
            logger.info(f"非同期埋め込み生成完了: {response_time:.3f}秒")
            return result
            
        except Exception as e:
            logger.error(f"非同期埋め込み生成エラー: {str(e)}")
            raise EmbeddingError(f"非同期埋め込み生成中にエラーが発生しました: {str(e)}") from e
    
    def generate_batch_embeddings(self, texts: List[str]) -> BatchEmbeddingResult:
        """
        バッチで埋め込みを生成
        
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
            raise ValueError("バッチサイズが制限を超えています（2048件まで）")
        
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
        
        try:
            tokens = self.tokenizer.encode(text)
            return len(tokens)
        except Exception as e:
            logger.warning(f"トークン推定エラー、文字数ベース推定を使用: {str(e)}")
            # フォールバック: 文字数ベース推定（日本語対応）
            return len(text) // 2 if any('\u3040' <= c <= '\u309f' or '\u30a0' <= c <= '\u30ff' or '\u4e00' <= c <= '\u9faf' for c in text) else len(text) // 4
    
    def validate_embedding_dimension(self, embedding: List[float]) -> bool:
        """
        埋め込み次元数を検証
        
        Args:
            embedding: 検証対象埋め込み
            
        Returns:
            bool: 検証結果
        """
        expected_dim = 1536  # text-embedding-3-smallの次元数
        return len(embedding) == expected_dim
    
    def get_model_info(self) -> Dict[str, Any]:
        """
        モデル情報を取得
        
        Returns:
            Dict[str, Any]: モデル情報
        """
        return {
            "model": self.model,
            "dimension": 1536,
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


class EmbeddingError(Exception):
    """埋め込みエラー"""
    pass