"""
埋め込みサービス

OpenAI text-embedding-3-smallを使用したベクトル埋め込み生成
"""

from typing import List, Dict, Any, Optional
import logging
import time
import numpy as np
from dataclasses import dataclass

import openai
from openai import OpenAI

logger = logging.getLogger(__name__)

@dataclass
class EmbeddingResult:
    """埋め込み結果"""
    embedding: List[float]
    token_count: int
    model: str

@dataclass
class BatchEmbeddingResult:
    """バッチ埋め込み結果"""
    embeddings: List[List[float]]
    total_tokens: int
    model: str

class EmbeddingService:
    """埋め込みサービスクラス"""
    
    def __init__(self, api_key: str, model: str = "text-embedding-3-small") -> None:
        """
        初期化
        
        Args:
            api_key: OpenAI APIキー
            model: 使用するモデル名
            
        Raises:
            ValueError: APIキーが空の場合
        """
        if not api_key or api_key.strip() == "":
            raise ValueError("APIキーが指定されていません")
            
        self.api_key = api_key
        self.model = model
        self.batch_size = 100  # OpenAI APIレート制限考慮
        self.max_retries = 3
        self.retry_delay = 1.0
        
        # OpenAIクライアント初期化
        self.client = OpenAI(api_key=api_key)
        
        logger.info(f"EmbeddingService初期化完了: model={model}")
    
    def create_embedding(self, text: str) -> EmbeddingResult:
        """
        単一テキストの埋め込みを生成
        
        Args:
            text: 埋め込み対象テキスト
            
        Returns:
            EmbeddingResult: 埋め込み結果
            
        Raises:
            EmbeddingError: 埋め込み生成エラーの場合
        """
        logger.info(f"埋め込み生成開始: {len(text)}文字")
        
        for attempt in range(self.max_retries):
            try:
                # OpenAI API呼び出し
                response = self.client.embeddings.create(
                    input=text,
                    model=self.model
                )
                
                # 応答からデータ抽出
                embedding_data = response.data[0]
                
                result = EmbeddingResult(
                    embedding=embedding_data.embedding,
                    token_count=response.usage.total_tokens,
                    model=self.model
                )
                
                logger.info("埋め込み生成完了")
                return result
                
            except openai.RateLimitError as e:
                if attempt < self.max_retries - 1:
                    wait_time = self.retry_delay * (2 ** attempt)
                    logger.warning(f"レート制限エラー。{wait_time}秒後にリトライします: {str(e)}")
                    time.sleep(wait_time)
                    continue
                else:
                    logger.error(f"レート制限エラー（最大リトライ回数到達）: {str(e)}")
                    raise EmbeddingError(f"レート制限により埋め込み生成に失敗しました: {str(e)}") from e
                    
            except openai.OpenAIError as e:
                logger.error(f"OpenAI APIエラー: {str(e)}", exc_info=True)
                raise EmbeddingError(f"埋め込み生成中にAPIエラーが発生しました: {str(e)}") from e
                
            except Exception as e:
                logger.error(f"埋め込み生成エラー: {str(e)}", exc_info=True)
                raise EmbeddingError(f"埋め込み生成中にエラーが発生しました: {str(e)}") from e
    
    def create_batch_embeddings(self, texts: List[str]) -> BatchEmbeddingResult:
        """
        バッチで埋め込みを生成
        
        Args:
            texts: 埋め込み対象テキストリスト
            
        Returns:
            BatchEmbeddingResult: バッチ埋め込み結果
            
        Raises:
            EmbeddingError: 埋め込み生成エラーの場合
        """
        logger.info(f"バッチ埋め込み生成開始: {len(texts)}件")
        
        all_embeddings = []
        total_tokens = 0
        
        try:
            # テキストを batch_size 単位で分割して処理
            for i in range(0, len(texts), self.batch_size):
                batch_texts = texts[i:i + self.batch_size]
                logger.info(f"バッチ処理中: {i+1}-{min(i+len(batch_texts), len(texts))}/{len(texts)}")
                
                # バッチ処理
                batch_result = self._process_batch(batch_texts)
                all_embeddings.extend(batch_result.embeddings)
                total_tokens += batch_result.total_tokens
            
            result = BatchEmbeddingResult(
                embeddings=all_embeddings,
                total_tokens=total_tokens,
                model=self.model
            )
            
            logger.info(f"バッチ埋め込み生成完了: {len(all_embeddings)}件")
            return result
            
        except Exception as e:
            logger.error(f"バッチ埋め込み生成エラー: {str(e)}", exc_info=True)
            raise EmbeddingError(f"バッチ埋め込み生成中にエラーが発生しました: {str(e)}") from e
    
    def _process_batch(self, batch_texts: List[str]) -> BatchEmbeddingResult:
        """
        単一バッチの処理（内部メソッド）
        
        Args:
            batch_texts: バッチ処理対象テキスト
            
        Returns:
            BatchEmbeddingResult: バッチ処理結果
        """
        for attempt in range(self.max_retries):
            try:
                # OpenAI API呼び出し
                response = self.client.embeddings.create(
                    input=batch_texts,
                    model=self.model
                )
                
                # 応答からデータ抽出
                embeddings = [item.embedding for item in response.data]
                
                return BatchEmbeddingResult(
                    embeddings=embeddings,
                    total_tokens=response.usage.total_tokens,
                    model=self.model
                )
                
            except openai.RateLimitError as e:
                if attempt < self.max_retries - 1:
                    wait_time = self.retry_delay * (2 ** attempt)
                    logger.warning(f"バッチ処理レート制限エラー。{wait_time}秒後にリトライします: {str(e)}")
                    time.sleep(wait_time)
                    continue
                else:
                    logger.error(f"バッチ処理レート制限エラー（最大リトライ回数到達）: {str(e)}")
                    raise EmbeddingError(f"レート制限によりバッチ埋め込み生成に失敗しました: {str(e)}") from e
                    
            except openai.OpenAIError as e:
                logger.error(f"バッチ処理OpenAI APIエラー: {str(e)}", exc_info=True)
                raise EmbeddingError(f"バッチ埋め込み生成中にAPIエラーが発生しました: {str(e)}") from e
    
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
        
        # NumPyを使用してコサイン類似度を計算
        vec1 = np.array(embedding1)
        vec2 = np.array(embedding2)
        
        # ベクトルの内積
        dot_product = np.dot(vec1, vec2)
        
        # ベクトルのノルム
        norm1 = np.linalg.norm(vec1)
        norm2 = np.linalg.norm(vec2)
        
        # ゼロベクトルの場合の処理
        if norm1 == 0.0 or norm2 == 0.0:
            return 0.0
        
        # コサイン類似度 = 内積 / (ノルム1 * ノルム2)
        cosine_similarity = dot_product / (norm1 * norm2)
        
        return float(cosine_similarity)

class EmbeddingError(Exception):
    """埋め込みエラー"""
    pass