"""
トークンカウントユーティリティ

OpenAI tiktoken ライブラリを使用した正確なトークン数計算
"""

import logging
from typing import List, Dict, Any, Optional

logger = logging.getLogger(__name__)

# tiktoken がインストールされていない場合の代替実装
try:
    import tiktoken
    TIKTOKEN_AVAILABLE = True
except ImportError:
    TIKTOKEN_AVAILABLE = False
    logger.warning("tiktoken not installed. Using fallback token estimation.")


class TokenCounter:
    """トークンカウンタークラス"""
    
    def __init__(self, model: str = "text-embedding-3-small"):
        """
        初期化
        
        Args:
            model: 使用するモデル名
        """
        self.model = model
        self.encoding = None
        
        if TIKTOKEN_AVAILABLE:
            try:
                # モデルに対応するエンコーディングを取得
                if model in ["text-embedding-3-small", "text-embedding-3-large"]:
                    # text-embedding-3系はcl100k_baseを使用
                    self.encoding = tiktoken.get_encoding("cl100k_base")
                elif model == "text-embedding-ada-002":
                    # ada-002もcl100k_baseを使用
                    self.encoding = tiktoken.get_encoding("cl100k_base")
                else:
                    # デフォルト
                    self.encoding = tiktoken.get_encoding("cl100k_base")
                logger.info(f"TokenCounter initialized with tiktoken for model: {model}")
            except Exception as e:
                logger.error(f"Failed to initialize tiktoken: {str(e)}")
                self.encoding = None
        else:
            logger.info("TokenCounter initialized with fallback estimation")
    
    def count_tokens(self, text: str) -> int:
        """
        テキストのトークン数をカウント
        
        Args:
            text: カウント対象テキスト
            
        Returns:
            int: トークン数
        """
        if not text:
            return 0
        
        if self.encoding is not None:
            # tiktokenを使用した正確なカウント
            try:
                tokens = self.encoding.encode(text)
                return len(tokens)
            except Exception as e:
                logger.error(f"tiktoken encoding error: {str(e)}")
                # フォールバックに切り替え
                return self._estimate_tokens(text)
        else:
            # フォールバック推定
            return self._estimate_tokens(text)
    
    def count_tokens_batch(self, texts: List[str]) -> List[int]:
        """
        バッチテキストのトークン数をカウント
        
        Args:
            texts: カウント対象テキストリスト
            
        Returns:
            List[int]: 各テキストのトークン数
        """
        return [self.count_tokens(text) for text in texts]
    
    def _estimate_tokens(self, text: str) -> int:
        """
        トークン数の推定（フォールバック）
        
        日本語と英語の混在テキストに対応した推定アルゴリズム
        
        Args:
            text: 推定対象テキスト
            
        Returns:
            int: 推定トークン数
        """
        if not text:
            return 0
        
        # 日本語文字数をカウント
        japanese_chars = sum(1 for char in text if self._is_japanese(char))
        
        # 英語単語数をカウント（簡易的な分割）
        non_japanese_text = ''.join(' ' if self._is_japanese(c) else c for c in text)
        english_words = len(non_japanese_text.split())
        
        # 推定計算
        # 日本語: 1文字 ≈ 0.7トークン（実測値ベース）
        # 英語: 1単語 ≈ 1.3トークン（実測値ベース）
        estimated_tokens = int(japanese_chars * 0.7 + english_words * 1.3)
        
        # 最小値1を保証
        return max(1, estimated_tokens)
    
    def _is_japanese(self, char: str) -> bool:
        """
        文字が日本語かどうか判定
        
        Args:
            char: 判定対象文字
            
        Returns:
            bool: 日本語の場合True
        """
        # Unicode範囲で日本語を判定
        code = ord(char)
        return (
            (0x3040 <= code <= 0x309F) or  # ひらがな
            (0x30A0 <= code <= 0x30FF) or  # カタカナ
            (0x4E00 <= code <= 0x9FFF) or  # 漢字（CJK統合漢字）
            (0x3400 <= code <= 0x4DBF)     # CJK統合漢字拡張A
        )
    
    def validate_token_limit(self, text: str, max_tokens: int = 8192) -> bool:
        """
        トークン数制限の検証
        
        Args:
            text: 検証対象テキスト
            max_tokens: 最大トークン数
            
        Returns:
            bool: 制限内の場合True
        """
        token_count = self.count_tokens(text)
        return token_count <= max_tokens
    
    def truncate_to_token_limit(self, text: str, max_tokens: int = 8192) -> str:
        """
        トークン数制限に合わせてテキストを切り詰め
        
        Args:
            text: 切り詰め対象テキスト
            max_tokens: 最大トークン数
            
        Returns:
            str: 切り詰められたテキスト
        """
        if self.validate_token_limit(text, max_tokens):
            return text
        
        # 二分探索で適切な長さを見つける
        left, right = 0, len(text)
        result = ""
        
        while left <= right:
            mid = (left + right) // 2
            truncated = text[:mid]
            if self.count_tokens(truncated) <= max_tokens:
                result = truncated
                left = mid + 1
            else:
                right = mid - 1
        
        return result
    
    def get_model_info(self) -> Dict[str, Any]:
        """
        モデル情報を取得
        
        Returns:
            Dict[str, Any]: モデル情報
        """
        return {
            "model": self.model,
            "tiktoken_available": TIKTOKEN_AVAILABLE,
            "encoding_name": self.encoding.name if self.encoding else None,
            "estimation_method": "tiktoken" if self.encoding else "fallback"
        }


# グローバルインスタンス（デフォルトモデル用）
default_counter = TokenCounter()


def count_tokens(text: str, model: Optional[str] = None) -> int:
    """
    テキストのトークン数をカウント（便利関数）
    
    Args:
        text: カウント対象テキスト
        model: 使用するモデル名（省略時はデフォルト）
        
    Returns:
        int: トークン数
    """
    if model and model != default_counter.model:
        counter = TokenCounter(model)
        return counter.count_tokens(text)
    else:
        return default_counter.count_tokens(text)


def estimate_embedding_cost(texts: List[str], model: str = "text-embedding-3-small") -> Dict[str, Any]:
    """
    埋め込み生成コストを推定（便利関数）
    
    Args:
        texts: テキストリスト
        model: 使用するモデル
        
    Returns:
        Dict[str, Any]: コスト推定結果
    """
    from models.embedding import OPENAI_EMBEDDING_MODELS
    
    counter = TokenCounter(model)
    token_counts = counter.count_tokens_batch(texts)
    total_tokens = sum(token_counts)
    
    model_info = OPENAI_EMBEDDING_MODELS.get(model, {})
    cost_per_1k = model_info.get("cost_per_1k_tokens", 0)
    estimated_cost = (total_tokens / 1000.0) * cost_per_1k
    
    return {
        "texts_count": len(texts),
        "total_tokens": total_tokens,
        "avg_tokens": total_tokens / len(texts) if texts else 0,
        "model": model,
        "cost_per_1k_tokens": cost_per_1k,
        "estimated_cost_usd": estimated_cost,
        "token_counts": token_counts
    }