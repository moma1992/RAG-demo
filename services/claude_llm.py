"""
Claude LLMサービス

Anthropic Claude APIを使用したテキスト生成機能
"""

from typing import List, Dict, Any, Optional
import logging
import time
from dataclasses import dataclass

import anthropic
from anthropic import Anthropic

logger = logging.getLogger(__name__)

@dataclass
class ChatMessage:
    """チャットメッセージ"""
    role: str  # "user" or "assistant"
    content: str

@dataclass
class GenerationResult:
    """生成結果"""
    content: str
    usage: Dict[str, int]
    model: str

class ClaudeLLMService:
    """Claude LLMサービスクラス"""
    
    def __init__(self, api_key: str, model: str = "claude-3-haiku-20240307") -> None:
        """
        初期化
        
        Args:
            api_key: Anthropic APIキー
            model: 使用するモデル名
            
        Raises:
            ValueError: APIキーが空の場合
        """
        if not api_key or api_key.strip() == "":
            raise ValueError("APIキーが指定されていません")
            
        self.api_key = api_key
        self.model = model
        self.max_tokens = 4096
        self.max_retries = 3
        self.retry_delay = 1.0
        
        # Anthropicクライアント初期化
        self.client = Anthropic(api_key=api_key)
        
        logger.info(f"ClaudeLLMService初期化完了: model={model}")
    
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
            LLMError: LLMエラーの場合
        """
        logger.info(f"回答生成開始: query={query[:50]}...")
        
        for attempt in range(self.max_retries):
            try:
                # システムプロンプトを構築
                system_prompt = self._build_system_prompt()
                
                # ユーザープロンプトを構築
                user_prompt = self._build_user_prompt(query, context_chunks)
                
                # メッセージ履歴を構築
                messages = []
                if chat_history:
                    messages.extend([
                        {"role": msg.role, "content": msg.content} 
                        for msg in chat_history
                    ])
                messages.append({"role": "user", "content": user_prompt})
                
                # Claude API呼び出し
                response = self.client.messages.create(
                    model=self.model,
                    max_tokens=self.max_tokens,
                    system=system_prompt,
                    messages=messages
                )
                
                # 応答からデータ抽出
                content = response.content[0].text
                
                result = GenerationResult(
                    content=content,
                    usage={
                        "input_tokens": response.usage.input_tokens,
                        "output_tokens": response.usage.output_tokens
                    },
                    model=self.model
                )
                
                logger.info("回答生成完了")
                return result
                
            except anthropic.RateLimitError as e:
                if attempt < self.max_retries - 1:
                    wait_time = self.retry_delay * (2 ** attempt)
                    logger.warning(f"レート制限エラー。{wait_time}秒後にリトライします: {str(e)}")
                    time.sleep(wait_time)
                    continue
                else:
                    logger.error(f"レート制限エラー（最大リトライ回数到達）: {str(e)}")
                    raise LLMError(f"レート制限により回答生成に失敗しました: {str(e)}") from e
                    
            except anthropic.AnthropicError as e:
                logger.error(f"Claude APIエラー: {str(e)}", exc_info=True)
                raise LLMError(f"回答生成中にAPIエラーが発生しました: {str(e)}") from e
                
            except Exception as e:
                logger.error(f"回答生成エラー: {str(e)}", exc_info=True)
                raise LLMError(f"回答生成中にエラーが発生しました: {str(e)}") from e
    
    def _build_system_prompt(self) -> str:
        """システムプロンプトを構築"""
        return """あなたは新入社員向けの社内文書検索アシスタントです。

以下のガイドラインに従って回答してください：

1. 提供された文書の内容に基づいて正確に回答する
2. 文書に記載されていない情報については「文書に記載がありません」と伝える
3. 新入社員にとって分かりやすい日本語で説明する
4. 関連する文書名やページ番号を参考として示す
5. 不明な点があれば人事部に確認するよう案内する

回答は親切で丁寧な口調で行ってください。"""
    
    def _build_user_prompt(self, query: str, context_chunks: List[str]) -> str:
        """ユーザープロンプトを構築"""
        context_text = "\n\n---\n\n".join(context_chunks) if context_chunks else "関連する文書が見つかりませんでした。"
        
        return f"""参考文書：
{context_text}

質問：
{query}

上記の参考文書を基に、質問に回答してください。"""
    
    def summarize_text(self, text: str, max_length: int = 500) -> GenerationResult:
        """
        テキストを要約
        
        Args:
            text: 要約対象テキスト
            max_length: 最大文字数
            
        Returns:
            GenerationResult: 要約結果
            
        Raises:
            LLMError: LLMエラーの場合
        """
        logger.info(f"テキスト要約開始: {len(text)}文字")
        
        for attempt in range(self.max_retries):
            try:
                # 要約用のシステムプロンプト
                system_prompt = f"""あなたは文書要約の専門家です。
以下のガイドラインに従って、日本語で簡潔な要約を作成してください：

1. 重要なポイントを漏らさずに要約する
2. 新入社員にとって分かりやすい表現を使用する
3. 最大{max_length}文字以内で要約する
4. 元の文書の主要な内容を正確に反映する"""

                # ユーザープロンプト
                user_prompt = f"""以下のテキストを要約してください：

{text}"""

                # Claude API呼び出し
                response = self.client.messages.create(
                    model=self.model,
                    max_tokens=self.max_tokens,
                    system=system_prompt,
                    messages=[{"role": "user", "content": user_prompt}]
                )
                
                # 応答からデータ抽出
                content = response.content[0].text
                
                result = GenerationResult(
                    content=content,
                    usage={
                        "input_tokens": response.usage.input_tokens,
                        "output_tokens": response.usage.output_tokens
                    },
                    model=self.model
                )
                
                logger.info("テキスト要約完了")
                return result
                
            except anthropic.RateLimitError as e:
                if attempt < self.max_retries - 1:
                    wait_time = self.retry_delay * (2 ** attempt)
                    logger.warning(f"要約処理レート制限エラー。{wait_time}秒後にリトライします: {str(e)}")
                    time.sleep(wait_time)
                    continue
                else:
                    logger.error(f"要約処理レート制限エラー（最大リトライ回数到達）: {str(e)}")
                    raise LLMError(f"レート制限により要約処理に失敗しました: {str(e)}") from e
                    
            except anthropic.AnthropicError as e:
                logger.error(f"要約処理Claude APIエラー: {str(e)}", exc_info=True)
                raise LLMError(f"テキスト要約中にAPIエラーが発生しました: {str(e)}") from e
                
            except Exception as e:
                logger.error(f"テキスト要約エラー: {str(e)}", exc_info=True)
                raise LLMError(f"テキスト要約中にエラーが発生しました: {str(e)}") from e

class LLMError(Exception):
    """LLMエラー"""
    pass