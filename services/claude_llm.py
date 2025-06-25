"""
Claude LLMサービス

LangChain + Anthropic Claude APIを使用したRAG対応テキスト生成機能
"""

from typing import List, Dict, Any, Optional, AsyncIterator, Union
import logging
import time
import asyncio
from dataclasses import dataclass, field
from datetime import datetime

import tiktoken
from langchain_anthropic import ChatAnthropic
from langchain_core.messages import HumanMessage, SystemMessage, AIMessage
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.runnables.retry import RunnableRetry
import anthropic

from utils.error_handler import RAGError

logger = logging.getLogger(__name__)

@dataclass
class ChatMessage:
    """チャットメッセージ"""
    role: str  # "user", "assistant", "system"
    content: str
    
    def __post_init__(self):
        if self.role not in ["user", "assistant", "system"]:
            raise ValueError(f"無効なrole: {self.role}")
        if not self.content or not self.content.strip():
            raise ValueError("空のcontentは許可されていません")

@dataclass
class GenerationResult:
    """生成結果"""
    content: str
    usage: Dict[str, int]
    model: str
    metadata: Dict[str, Any] = field(default_factory=dict)

class ClaudeError(RAGError):
    """Claude関連エラー"""
    pass

class RateLimitError(ClaudeError):
    """レート制限エラー"""
    def __init__(self, message: str, retry_after: Optional[int] = None):
        super().__init__(message)
        self.retry_after = retry_after

class TokenLimitError(ClaudeError):
    """トークン制限エラー"""
    def __init__(self, message: str, current_tokens: int, max_tokens: int):
        super().__init__(message)
        self.current_tokens = current_tokens
        self.max_tokens = max_tokens

class ClaudeService:
    """LangChain統合Claude LLMサービスクラス"""
    
    def __init__(
        self, 
        api_key: str, 
        model: str = "claude-3-sonnet-20240229",
        max_tokens: int = 2048,
        temperature: float = 0,
        timeout: int = 30,
        max_retries: int = 3
    ) -> None:
        """
        初期化
        
        Args:
            api_key: Anthropic APIキー
            model: 使用するモデル名
            max_tokens: 最大トークン数
            temperature: 温度パラメータ
            timeout: タイムアウト秒数
            max_retries: 最大リトライ回数
        """
        self.api_key = api_key
        self.model = model
        self.max_tokens = max_tokens
        self.temperature = temperature
        self.timeout = timeout
        self.max_retries = max_retries
        
        # 使用量追跡
        self._usage_stats = {
            "total_requests": 0,
            "total_input_tokens": 0,
            "total_output_tokens": 0,
            "total_cost": 0.0
        }
        
        # LangChain ChatAnthropicクライアント初期化
        try:
            self.llm = ChatAnthropic(
                api_key=api_key,
                model=model,
                max_tokens=max_tokens,
                temperature=temperature,
                timeout=timeout,
                max_retries=max_retries
            )
            
            # リトライ機能付きLLM
            self.llm_with_retry = self.llm.with_retry(
                retry_if_exception_type=(Exception,),
                wait_exponential_jitter=True,
                stop_after_attempt=max_retries + 2
            )
            
            # トークンエンコーダー
            self.tokenizer = tiktoken.get_encoding("cl100k_base")
            
            logger.info(f"ClaudeService初期化完了: model={model}")
            
        except Exception as e:
            logger.error(f"ClaudeService初期化エラー: {str(e)}")
            raise ClaudeError(f"Claude LLMの初期化に失敗しました: {str(e)}") from e
    
    def generate_response(
        self,
        query: str,
        context_chunks: List[str],
        chat_history: Optional[List[ChatMessage]] = None
    ) -> GenerationResult:
        """
        RAG回答を生成
        
        Args:
            query: ユーザーの質問
            context_chunks: 検索された関連文書チャンク
            chat_history: チャット履歴
            
        Returns:
            GenerationResult: 生成結果
            
        Raises:
            ClaudeError: Claude関連エラーの場合
        """
        start_time = time.time()
        logger.info(f"回答生成開始: query={query[:50]}...")
        
        # 入力検証
        if not query or not query.strip():
            raise ValueError("空の質問は許可されていません")
        
        try:
            # トークン制限チェック
            total_tokens = self._estimate_total_tokens(query, context_chunks, chat_history)
            if total_tokens > 90000:  # 安全マージン
                raise TokenLimitError(
                    f"トークン制限を超えています: {total_tokens} > 90000",
                    total_tokens, 90000
                )
            
            # メッセージを構築
            messages = self._build_messages(query, context_chunks, chat_history)
            
            # Claude API呼び出し
            response = self.llm_with_retry.invoke(messages)
            
            # 使用量追跡
            usage = {
                "input_tokens": getattr(response, "usage_metadata", {}).get("input_tokens", 0),
                "output_tokens": getattr(response, "usage_metadata", {}).get("output_tokens", 0)
            }
            
            self._update_usage_stats(usage)
            
            processing_time = time.time() - start_time
            
            result = GenerationResult(
                content=response.content,
                usage=usage,
                model=self.model,
                metadata={
                    "processing_time": processing_time,
                    "timestamp": datetime.now().isoformat()
                }
            )
            
            logger.info(f"回答生成完了: {processing_time:.2f}秒")
            return result
            
        except anthropic.RateLimitError as e:
            retry_after = getattr(e.response, "headers", {}).get("retry-after")
            raise RateLimitError(
                "レート制限に達しました。しばらく時間をおいてから再度お試しください。",
                retry_after=int(retry_after) if retry_after else None
            ) from e
            
        except anthropic.APIError as e:
            logger.error(f"Claude API エラー: {str(e)}")
            raise ClaudeError(f"Claude API呼び出しでエラーが発生しました: {str(e)}") from e
            
        except asyncio.TimeoutError as e:
            logger.error(f"Claude APIタイムアウト: {str(e)}")
            raise ClaudeError(f"Claude APIがタイムアウトしました: {str(e)}") from e
            
        except Exception as e:
            logger.error(f"回答生成エラー: {str(e)}", exc_info=True)
            raise ClaudeError(f"回答生成中にエラーが発生しました: {str(e)}") from e
    
    async def agenerate_response(
        self,
        query: str,
        context_chunks: List[str],
        chat_history: Optional[List[ChatMessage]] = None
    ) -> GenerationResult:
        """
        非同期RAG回答生成
        
        Args:
            query: ユーザーの質問
            context_chunks: 検索された関連文書チャンク
            chat_history: チャット履歴
            
        Returns:
            GenerationResult: 生成結果
        """
        start_time = time.time()
        logger.info(f"非同期回答生成開始: query={query[:50]}...")
        
        # 入力検証
        if not query or not query.strip():
            raise ValueError("空の質問は許可されていません")
        
        try:
            # メッセージを構築
            messages = self._build_messages(query, context_chunks, chat_history)
            
            # 非同期Claude API呼び出し
            response = await self.llm_with_retry.ainvoke(messages)
            
            # 使用量追跡
            usage = {
                "input_tokens": getattr(response, "usage_metadata", {}).get("input_tokens", 0),
                "output_tokens": getattr(response, "usage_metadata", {}).get("output_tokens", 0)
            }
            
            self._update_usage_stats(usage)
            
            processing_time = time.time() - start_time
            
            result = GenerationResult(
                content=response.content,
                usage=usage,
                model=self.model,
                metadata={
                    "processing_time": processing_time,
                    "timestamp": datetime.now().isoformat(),
                    "async": True
                }
            )
            
            logger.info(f"非同期回答生成完了: {processing_time:.2f}秒")
            return result
            
        except Exception as e:
            logger.error(f"非同期回答生成エラー: {str(e)}", exc_info=True)
            raise ClaudeError(f"非同期回答生成中にエラーが発生しました: {str(e)}") from e
    
    async def astream_response(
        self,
        query: str,
        context_chunks: List[str],
        chat_history: Optional[List[ChatMessage]] = None
    ) -> AsyncIterator[Dict[str, Any]]:
        """
        非同期ストリーミング回答生成
        
        Args:
            query: ユーザーの質問
            context_chunks: 検索された関連文書チャンク
            chat_history: チャット履歴
            
        Yields:
            Dict[str, Any]: ストリーミングチャンク
        """
        logger.info(f"ストリーミング回答生成開始: query={query[:50]}...")
        
        try:
            # メッセージを構築
            messages = self._build_messages(query, context_chunks, chat_history)
            
            # ストリーミング呼び出し
            async for chunk in self.llm_with_retry.astream(messages):
                yield {
                    "content": chunk.content,
                    "usage": getattr(chunk, "usage_metadata", {}),
                    "model": self.model,
                    "timestamp": datetime.now().isoformat()
                }
                
        except Exception as e:
            logger.error(f"ストリーミング回答生成エラー: {str(e)}")
            raise ClaudeError(f"ストリーミング回答生成中にエラーが発生しました: {str(e)}") from e
    
    def summarize_text(self, text: str, max_length: int = 500) -> GenerationResult:
        """
        テキストを要約
        
        Args:
            text: 要約対象テキスト
            max_length: 最大文字数
            
        Returns:
            GenerationResult: 要約結果
            
        Raises:
            ClaudeError: Claude関連エラーの場合
        """
        start_time = time.time()
        logger.info(f"テキスト要約開始: {len(text)}文字")
        
        try:
            # 要約プロンプトを構築
            system_prompt = f"""あなたは優秀な要約アシスタントです。
提供されたテキストを{max_length}文字以内で要約してください。

要約のガイドライン：
- 重要なポイントを簡潔にまとめる
- 元の文書の主要な内容を保持する
- 読みやすい日本語で記述する
- 箇条書きを活用して構造化する"""

            user_prompt = f"""以下のテキストを要約してください：

{text}"""

            # メッセージ構築
            messages = [
                SystemMessage(content=system_prompt),
                HumanMessage(content=user_prompt)
            ]
            
            # Claude API呼び出し
            response = self.llm_with_retry.invoke(messages)
            
            # 使用量追跡
            usage = {
                "input_tokens": getattr(response, "usage_metadata", {}).get("input_tokens", 0),
                "output_tokens": getattr(response, "usage_metadata", {}).get("output_tokens", 0)
            }
            
            self._update_usage_stats(usage)
            
            processing_time = time.time() - start_time
            
            result = GenerationResult(
                content=response.content,
                usage=usage,
                model=self.model,
                metadata={
                    "processing_time": processing_time,
                    "timestamp": datetime.now().isoformat(),
                    "operation": "summarization",
                    "original_length": len(text),
                    "summary_length": len(response.content)
                }
            )
            
            logger.info(f"テキスト要約完了: {processing_time:.2f}秒")
            return result
            
        except Exception as e:
            logger.error(f"テキスト要約エラー: {str(e)}", exc_info=True)
            raise ClaudeError(f"テキスト要約中にエラーが発生しました: {str(e)}") from e
    
    def _build_system_prompt(self) -> str:
        """システムプロンプトを構築"""
        return """あなたは新入社員向けの社内文書検索アシスタントです。

<instructions>
以下のガイドラインに従って回答してください：

1. 提供された文書の内容に基づいて正確に回答する
2. 文書に記載されていない情報については「文書に記載がありません」と伝える
3. 新入社員にとって分かりやすい日本語で説明する
4. 関連する文書名やページ番号を参考として示す
5. 不明な点があれば人事部に確認するよう案内する
6. 回答は親切で丁寧な口調で行う
7. 情報が不十分な場合は、追加の質問を提案する
</instructions>

回答形式：
- 簡潔で分かりやすい説明
- 根拠となる文書の引用
- 必要に応じた補足説明"""
    
    def _build_user_prompt(self, query: str, context_chunks: List[str]) -> str:
        """ユーザープロンプトを構築"""
        if context_chunks:
            context_text = "\n\n---\n\n".join(context_chunks)
            return f"""<context>
{context_text}
</context>

<question>
{query}
</question>

上記のcontextに基づいて、questionに回答してください。
contextに関連情報がない場合は、その旨を明確に伝えてください。"""
        else:
            return f"""<question>
{query}
</question>

関連する文書が見つかりませんでした。
一般的な情報でお答えできる場合は回答し、具体的な社内情報が必要な場合は人事部への確認をお勧めください。"""
    
    def _build_messages(
        self, 
        query: str, 
        context_chunks: List[str], 
        chat_history: Optional[List[ChatMessage]] = None
    ) -> List[Union[SystemMessage, HumanMessage, AIMessage]]:
        """LangChain用メッセージを構築"""
        messages = []
        
        # システムメッセージ
        messages.append(SystemMessage(content=self._build_system_prompt()))
        
        # チャット履歴
        if chat_history:
            for msg in chat_history:
                if msg.role == "user":
                    messages.append(HumanMessage(content=msg.content))
                elif msg.role == "assistant":
                    messages.append(AIMessage(content=msg.content))
        
        # 現在のユーザープロンプト
        user_prompt = self._build_user_prompt(query, context_chunks)
        messages.append(HumanMessage(content=user_prompt))
        
        return messages
    
    def _count_tokens(self, text: str) -> int:
        """トークン数を計算"""
        try:
            return len(self.tokenizer.encode(text))
        except Exception as e:
            logger.warning(f"トークン数計算エラー: {str(e)}")
            # フォールバック: 文字数の1/4を概算
            return len(text) // 4
    
    def _estimate_total_tokens(
        self, 
        query: str, 
        context_chunks: List[str], 
        chat_history: Optional[List[ChatMessage]] = None
    ) -> int:
        """総トークン数を推定"""
        total = 0
        
        # システムプロンプト
        total += self._count_tokens(self._build_system_prompt())
        
        # コンテキスト
        context_text = "\n\n---\n\n".join(context_chunks) if context_chunks else ""
        total += self._count_tokens(context_text)
        
        # クエリ
        total += self._count_tokens(query)
        
        # チャット履歴
        if chat_history:
            for msg in chat_history:
                total += self._count_tokens(msg.content)
        
        # 出力トークンの予備
        total += self.max_tokens
        
        return total
    
    def _update_usage_stats(self, usage: Dict[str, int]) -> None:
        """使用量統計を更新"""
        self._usage_stats["total_requests"] += 1
        self._usage_stats["total_input_tokens"] += usage.get("input_tokens", 0)
        self._usage_stats["total_output_tokens"] += usage.get("output_tokens", 0)
        
        # コスト計算（Claude-3 Sonnetの価格）
        input_cost = usage.get("input_tokens", 0) * 0.003 / 1000
        output_cost = usage.get("output_tokens", 0) * 0.015 / 1000
        self._usage_stats["total_cost"] += input_cost + output_cost
    
    def get_usage_stats(self) -> Dict[str, Union[int, float]]:
        """使用量統計を取得"""
        return self._usage_stats.copy()
    
    def reset_usage_stats(self) -> None:
        """使用量統計をリセット"""
        self._usage_stats = {
            "total_requests": 0,
            "total_input_tokens": 0,
            "total_output_tokens": 0,
            "total_cost": 0.0
        }
        logger.info("使用量統計をリセットしました")

# 後方互換性のためのエイリアス
ClaudeLLMService = ClaudeService
LLMError = ClaudeError