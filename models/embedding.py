"""
Embedding Data Model

Issue #53: Embedding Data Model Implementation
OpenAI Embeddings API向けの効率的なデータモデル実装

主要機能:
- EmbeddingResult: 埋め込み結果データクラス
- EmbeddingBatch: バッチ処理用クラス
- ベクトル次元検証（1536次元）
- メタデータ管理（トークン数、コスト計算）
- Supabase スキーマ互換性
- 型安全性とPythonic性能
"""

import math
import statistics
from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)

# OpenAI Embedding API 定数
OPENAI_EMBEDDING_DIMENSION = 1536
OPENAI_EMBEDDING_MODELS = {
    "text-embedding-3-small": {
        "dimension": 1536,
        "cost_per_1k_tokens": 0.00002
    },
    "text-embedding-3-large": {
        "dimension": 3072,
        "cost_per_1k_tokens": 0.00013
    },
    "text-embedding-ada-002": {
        "dimension": 1536,
        "cost_per_1k_tokens": 0.0001
    }
}

# セキュリティと制限
MAX_TEXT_LENGTH = 8192  # OpenAI制限
MIN_TOKEN_COUNT = 1
MAX_TOKEN_COUNT = 8192


class EmbeddingDimensionError(ValueError):
    """埋め込みベクトル次元エラー"""
    def __init__(self, message: str, expected_dim: int, actual_dim: int):
        self.expected_dim = expected_dim
        self.actual_dim = actual_dim
        super().__init__(message)


class EmbeddingValidationError(ValueError):
    """埋め込みデータ検証エラー"""
    def __init__(self, message: str, field: str = "", value: Any = None):
        self.field = field
        self.value = value
        super().__init__(message)


def validate_embedding_vector(embedding: List[float], expected_dimension: int = OPENAI_EMBEDDING_DIMENSION) -> bool:
    """
    埋め込みベクトルの検証
    
    Args:
        embedding: 検証対象の埋め込みベクトル
        expected_dimension: 期待される次元数
        
    Returns:
        bool: 検証成功時True
        
    Raises:
        EmbeddingDimensionError: 次元数が不正な場合
        EmbeddingValidationError: ベクトル値が不正な場合
    """
    if not isinstance(embedding, list):
        raise EmbeddingValidationError(
            "埋め込みベクトルはリスト形式である必要があります",
            field="embedding",
            value=type(embedding)
        )
    
    if len(embedding) != expected_dimension:
        raise EmbeddingDimensionError(
            f"埋め込みベクトルは{expected_dimension}次元である必要があります。現在: {len(embedding)}次元",
            expected_dim=expected_dimension,
            actual_dim=len(embedding)
        )
    
    for i, value in enumerate(embedding):
        if not isinstance(value, (int, float)):
            raise EmbeddingValidationError(
                f"インデックス {i} の値は数値である必要があります",
                field=f"embedding[{i}]",
                value=value
            )
        
        if math.isnan(value):
            raise EmbeddingValidationError(
                f"インデックス {i} にNaNまたは無限大値が含まれています",
                field=f"embedding[{i}]",
                value=value
            )
        
        if math.isinf(value):
            raise EmbeddingValidationError(
                f"インデックス {i} にNaNまたは無限大値が含まれています",
                field=f"embedding[{i}]",
                value=value
            )
    
    return True


def validate_embedding_text(text: Any) -> bool:
    """
    埋め込み対象テキストの検証
    
    Args:
        text: 検証対象テキスト
        
    Returns:
        bool: 検証成功時True
        
    Raises:
        EmbeddingValidationError: テキストが不正な場合
    """
    if not isinstance(text, str):
        raise EmbeddingValidationError(
            "テキストは文字列である必要があります",
            field="text",
            value=type(text)
        )
    
    if not text.strip():
        raise EmbeddingValidationError(
            "テキストは空でない文字列である必要があります",
            field="text",
            value=text
        )
    
    if len(text) > MAX_TEXT_LENGTH:
        raise EmbeddingValidationError(
            f"テキストが長すぎます（最大{MAX_TEXT_LENGTH}文字）",
            field="text",
            value=len(text)
        )
    
    return True


def validate_embedding_model(model: str) -> bool:
    """
    埋め込みモデルの検証
    
    Args:
        model: 検証対象モデル名
        
    Returns:
        bool: 検証成功時True
        
    Raises:
        EmbeddingValidationError: モデルが不正な場合
    """
    if not isinstance(model, str):
        raise EmbeddingValidationError(
            "モデル名は文字列である必要があります",
            field="model",
            value=type(model)
        )
    
    if model not in OPENAI_EMBEDDING_MODELS:
        raise EmbeddingValidationError(
            f"サポートされていないモデルです: {model}",
            field="model",
            value=model
        )
    
    return True


@dataclass
class EmbeddingResult:
    """
    埋め込み結果データクラス
    
    OpenAI Embeddings APIからの単一結果を表現します。
    """
    text: str
    embedding: List[float]
    token_count: int
    model: str = "text-embedding-3-small"
    created_at: datetime = field(default_factory=datetime.now)
    response_time: Optional[float] = None
    
    def __post_init__(self) -> None:
        """初期化後の検証"""
        self.validate()
    
    def validate(self) -> None:
        """データ検証"""
        # テキスト検証
        validate_embedding_text(self.text)
        
        # モデル検証
        validate_embedding_model(self.model)
        
        # 埋め込みベクトル検証
        expected_dim = int(OPENAI_EMBEDDING_MODELS[self.model]["dimension"])
        validate_embedding_vector(self.embedding, expected_dim)
        
        # トークン数検証
        if not isinstance(self.token_count, int):
            raise EmbeddingValidationError(
                "トークン数は整数である必要があります",
                field="token_count",
                value=type(self.token_count)
            )
        
        if not (MIN_TOKEN_COUNT <= self.token_count <= MAX_TOKEN_COUNT):
            raise EmbeddingValidationError(
                f"トークン数は正の整数である必要があります（{MIN_TOKEN_COUNT}-{MAX_TOKEN_COUNT}の範囲）",
                field="token_count",
                value=self.token_count
            )
        
        # 作成日時検証
        if not isinstance(self.created_at, datetime):
            raise EmbeddingValidationError(
                "作成日時はdatetimeオブジェクトである必要があります",
                field="created_at",
                value=type(self.created_at)
            )
        
        # レスポンス時間検証
        if self.response_time is not None:
            if not isinstance(self.response_time, (int, float)):
                raise EmbeddingValidationError(
                    "レスポンス時間は数値である必要があります",
                    field="response_time",
                    value=type(self.response_time)
                )
            
            if self.response_time < 0:
                raise EmbeddingValidationError(
                    "レスポンス時間は非負値である必要があります",
                    field="response_time",
                    value=self.response_time
                )
    
    def to_supabase_format(self) -> Dict[str, Any]:
        """
        Supabase挿入用形式に変換
        
        Returns:
            Dict[str, Any]: Supabase互換形式のデータ
        """
        result = {
            "text": self.text,
            "embedding": self.embedding,
            "token_count": self.token_count,
            "model": self.model,
            "created_at": self.created_at.isoformat()
        }
        
        if self.response_time is not None:
            result["response_time"] = self.response_time
            
        return result
    
    def get_metadata(self) -> Dict[str, Any]:
        """
        メタデータ取得
        
        Returns:
            Dict[str, Any]: メタデータ情報
        """
        model_info = OPENAI_EMBEDDING_MODELS[self.model]
        metadata = {
            "model": self.model,
            "dimension": model_info["dimension"],
            "token_count": self.token_count,
            "text_length": len(self.text),
            "created_at": self.created_at,
            "cost_per_1k_tokens": model_info["cost_per_1k_tokens"]
        }
        
        if self.response_time is not None:
            metadata["response_time"] = self.response_time
            
        return metadata
    
    def calculate_cost(self) -> float:
        """
        単一結果のコスト計算
        
        Returns:
            float: 推定コスト（USD）
        """
        model_info = OPENAI_EMBEDDING_MODELS[self.model]
        cost_per_1k = model_info["cost_per_1k_tokens"]
        return (self.token_count / 1000.0) * cost_per_1k


class EmbeddingBatch:
    """
    埋め込みバッチクラス
    
    複数のEmbeddingResultを管理し、バッチ処理とコスト計算を提供します。
    """
    
    def __init__(self, results: List[EmbeddingResult]):
        """
        初期化
        
        Args:
            results: EmbeddingResultのリスト
        """
        if not isinstance(results, list):
            raise EmbeddingValidationError(
                "resultsはリストである必要があります",
                field="results",
                value=type(results)
            )
        
        # 各結果の検証（既に__post_init__で検証済みのはず）
        for i, result in enumerate(results):
            if not isinstance(result, EmbeddingResult):
                raise EmbeddingValidationError(
                    f"インデックス {i} はEmbeddingResultオブジェクトである必要があります",
                    field=f"results[{i}]",
                    value=type(result)
                )
        
        self.results = results
        self._calculate_totals()
    
    def _calculate_totals(self) -> None:
        """合計値の計算"""
        if not self.results:
            self.total_tokens = 0
            self.estimated_cost = 0.0
            return
        
        self.total_tokens = sum(result.token_count for result in self.results)
        self.estimated_cost = sum(result.calculate_cost() for result in self.results)
    
    def to_supabase_bulk_format(self) -> List[Dict[str, Any]]:
        """
        Supabaseバルク挿入用形式に変換
        
        Returns:
            List[Dict[str, Any]]: バルク挿入用データリスト
        """
        return [result.to_supabase_format() for result in self.results]
    
    def get_statistics(self) -> Dict[str, Any]:
        """
        バッチ統計情報取得
        
        Returns:
            Dict[str, Any]: 統計情報
        """
        if not self.results:
            return {
                "count": 0,
                "total_tokens": 0,
                "avg_tokens": 0.0,
                "min_tokens": 0,
                "max_tokens": 0,
                "estimated_cost": 0.0,
                "models_used": []
            }
        
        token_counts = [result.token_count for result in self.results]
        models_used = list(set(result.model for result in self.results))
        
        return {
            "count": len(self.results),
            "total_tokens": self.total_tokens,
            "avg_tokens": statistics.mean(token_counts),
            "min_tokens": min(token_counts),
            "max_tokens": max(token_counts),
            "estimated_cost": self.estimated_cost,
            "models_used": models_used
        }
    
    def filter_by_model(self, model: str) -> 'EmbeddingBatch':
        """
        モデル別フィルタリング
        
        Args:
            model: フィルタリング対象モデル
            
        Returns:
            EmbeddingBatch: フィルタリング結果
        """
        filtered_results = [
            result for result in self.results 
            if result.model == model
        ]
        return EmbeddingBatch(filtered_results)
    
    def get_model_breakdown(self) -> Dict[str, Dict[str, Any]]:
        """
        モデル別内訳取得
        
        Returns:
            Dict[str, Dict[str, Any]]: モデル別統計
        """
        breakdown = {}
        for model in set(result.model for result in self.results):
            model_batch = self.filter_by_model(model)
            breakdown[model] = model_batch.get_statistics()
        
        return breakdown


class EmbeddingCostCalculator:
    """
    埋め込みコスト計算クラス
    
    OpenAI Embeddings APIのコスト計算を提供します。
    """
    
    def __init__(self) -> None:
        """初期化"""
        self.model_costs = OPENAI_EMBEDDING_MODELS.copy()
        logger.info("EmbeddingCostCalculator初期化完了")
    
    def calculate_cost(self, token_count: int, model: str) -> float:
        """
        単一リクエストのコスト計算
        
        Args:
            token_count: トークン数
            model: モデル名
            
        Returns:
            float: 推定コスト（USD）
            
        Raises:
            EmbeddingValidationError: 無効なパラメータの場合
        """
        if not isinstance(token_count, int) or token_count <= 0:
            raise EmbeddingValidationError(
                "トークン数は正の整数である必要があります",
                field="token_count",
                value=token_count
            )
        
        validate_embedding_model(model)
        
        cost_per_1k = self.model_costs[model]["cost_per_1k_tokens"]
        return (token_count / 1000.0) * cost_per_1k
    
    def calculate_batch_cost(self, batch_items: List[Dict[str, Any]]) -> float:
        """
        バッチコスト計算
        
        Args:
            batch_items: バッチアイテムリスト（各アイテムは{'tokens': int, 'model': str}）
            
        Returns:
            float: 総推定コスト（USD）
        """
        if not isinstance(batch_items, list):
            raise EmbeddingValidationError(
                "バッチアイテムはリストである必要があります",
                field="batch_items",
                value=type(batch_items)
            )
        
        total_cost = 0.0
        for i, item in enumerate(batch_items):
            if not isinstance(item, dict):
                raise EmbeddingValidationError(
                    f"バッチアイテム {i} は辞書である必要があります",
                    field=f"batch_items[{i}]",
                    value=type(item)
                )
            
            if "tokens" not in item or "model" not in item:
                raise EmbeddingValidationError(
                    f"バッチアイテム {i} には'tokens'と'model'キーが必要です",
                    field=f"batch_items[{i}]",
                    value=list(item.keys())
                )
            
            total_cost += self.calculate_cost(item["tokens"], item["model"])
        
        return total_cost
    
    def get_model_costs(self) -> Dict[str, Dict[str, Any]]:
        """
        サポートモデルとコスト情報取得
        
        Returns:
            Dict[str, Dict[str, Any]]: モデル情報
        """
        return self.model_costs.copy()
    
    def estimate_batch_cost(self, texts: List[str], model: str = "text-embedding-3-small") -> Dict[str, Any]:
        """
        テキストリストからバッチコスト推定
        
        Args:
            texts: テキストリスト
            model: 使用モデル
            
        Returns:
            Dict[str, Any]: コスト推定結果
        """
        validate_embedding_model(model)
        
        # 正確なトークン数カウント
        from utils.tokenizer import TokenCounter
        token_counter = TokenCounter(model)
        
        estimated_tokens = []
        for text in texts:
            validate_embedding_text(text)
            token_count = token_counter.count_tokens(text)
            estimated_tokens.append(token_count)
        
        total_tokens = sum(estimated_tokens)
        estimated_cost = self.calculate_cost(total_tokens, model)
        
        return {
            "texts_count": len(texts),
            "model": model,
            "estimated_total_tokens": total_tokens,
            "estimated_cost_usd": estimated_cost,
            "cost_per_text": estimated_cost / len(texts) if texts else 0.0,
            "token_breakdown": estimated_tokens
        }