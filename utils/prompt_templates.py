"""
プロンプトテンプレート管理ユーティリティ

RAGシステム用の動的プロンプト生成とテンプレート管理機能
"""

from typing import Dict, List, Any, Optional, Union
import logging
import json
from dataclasses import dataclass, field
from datetime import datetime
from abc import ABC, abstractmethod

logger = logging.getLogger(__name__)

@dataclass
class PromptTemplate:
    """プロンプトテンプレートクラス"""
    name: str
    template: str
    variables: List[str]
    description: str = ""
    tags: List[str] = field(default_factory=list)
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    
    def render(self, variables: Dict[str, Any]) -> str:
        """
        テンプレートをレンダリング
        
        Args:
            variables: テンプレート変数
            
        Returns:
            str: レンダリング結果
            
        Raises:
            PromptValidationError: 変数不足の場合
        """
        try:
            # 必須変数チェック
            missing_vars = set(self.variables) - set(variables.keys())
            if missing_vars:
                raise PromptValidationError(
                    f"必要な変数が不足しています: {missing_vars}",
                    template_name=self.name,
                    missing_variables=list(missing_vars)
                )
            
            return self.template.format(**variables)
            
        except KeyError as e:
            raise PromptValidationError(
                f"テンプレート変数が見つかりません: {str(e)}",
                template_name=self.name
            ) from e
        except Exception as e:
            raise PromptValidationError(
                f"テンプレートレンダリングエラー: {str(e)}",
                template_name=self.name
            ) from e
    
    def validate(self, variables: Dict[str, Any]) -> bool:
        """
        テンプレート変数を検証
        
        Args:
            variables: 検証対象変数
            
        Returns:
            bool: 検証結果
        """
        required_vars = set(self.variables)
        provided_vars = set(variables.keys())
        
        return required_vars.issubset(provided_vars)

class PromptValidationError(Exception):
    """プロンプトバリデーションエラー"""
    def __init__(
        self, 
        message: str, 
        template_name: Optional[str] = None,
        missing_variables: Optional[List[str]] = None
    ):
        super().__init__(message)
        self.template_name = template_name
        self.missing_variables = missing_variables or []

class TemplateNotFoundError(Exception):
    """テンプレート未発見エラー"""
    def __init__(self, message: str, template_name: Optional[str] = None):
        super().__init__(message)
        self.template_name = template_name

class PromptTemplateManager:
    """プロンプトテンプレート管理クラス"""
    
    def __init__(self):
        """初期化"""
        self.templates: Dict[str, PromptTemplate] = {}
        self._system_templates = set()
        
        # デフォルトテンプレートを登録
        self._register_default_templates()
        
        logger.info("PromptTemplateManager初期化完了")
    
    def _register_default_templates(self) -> None:
        """デフォルトテンプレートを登録"""
        # RAGシステムプロンプト
        rag_system = PromptTemplate(
            name="rag_system",
            template="""あなたは新入社員向けの社内文書検索アシスタントです。

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
- 必要に応じた補足説明""",
            variables=[],
            description="RAGシステム用基本システムプロンプト",
            tags=["system", "rag", "default"]
        )
        
        # RAGユーザープロンプト
        rag_user = PromptTemplate(
            name="rag_user",
            template="""<context>
{context}
</context>

<question>
{question}
</question>

上記のcontextに基づいて、questionに回答してください。
contextに関連情報がない場合は、その旨を明確に伝えてください。""",
            variables=["context", "question"],
            description="RAG用ユーザープロンプト",
            tags=["user", "rag", "default"]
        )
        
        # 会話システムプロンプト
        conversation_system = PromptTemplate(
            name="conversation_system",
            template="""あなたは新入社員向けの対話型社内文書検索アシスタントです。

以下の特徴を持って対話してください：
- 会話履歴を考慮した自然な対話
- 文脈を理解した継続的なサポート
- 追加質問や確認を積極的に行う
- 親しみやすく親切な口調

前の会話内容を踏まえて、適切に回答してください。""",
            variables=[],
            description="対話型RAGシステム用システムプロンプト",
            tags=["system", "conversation", "default"]
        )
        
        # 要約システムプロンプト
        summarization_system = PromptTemplate(
            name="summarization_system",
            template="""あなたは優秀な文書要約アシスタントです。

要約のガイドライン：
- 重要なポイントを簡潔にまとめる
- 元の文書の主要な内容を保持する
- 読みやすい日本語で記述する
- 構造化された形式で提示する
- 新入社員にとって理解しやすい内容にする""",
            variables=[],
            description="文書要約用システムプロンプト",
            tags=["system", "summarization", "default"]
        )
        
        # システムテンプレートとして登録
        system_templates = [rag_system, rag_user, conversation_system, summarization_system]
        
        for template in system_templates:
            self.templates[template.name] = template
            self._system_templates.add(template.name)
    
    def register_template(self, template: PromptTemplate) -> None:
        """
        テンプレートを登録
        
        Args:
            template: 登録するテンプレート
            
        Raises:
            ValueError: テンプレート名が重複している場合
        """
        if template.name in self.templates:
            raise ValueError(f"テンプレート '{template.name}' はすでに登録されています")
        
        self.templates[template.name] = template
        logger.info(f"テンプレート登録完了: {template.name}")
    
    def get_template(self, name: str) -> PromptTemplate:
        """
        テンプレートを取得
        
        Args:
            name: テンプレート名
            
        Returns:
            PromptTemplate: テンプレート
            
        Raises:
            TemplateNotFoundError: テンプレートが見つからない場合
        """
        if name not in self.templates:
            raise TemplateNotFoundError(
                f"テンプレートが見つかりません: {name}",
                template_name=name
            )
        
        return self.templates[name]
    
    def list_templates(self) -> Dict[str, PromptTemplate]:
        """
        登録済みテンプレート一覧を取得
        
        Returns:
            Dict[str, PromptTemplate]: テンプレート辞書
        """
        return self.templates.copy()
    
    def validate_template_variables(self, template_name: str, variables: Dict[str, Any]) -> bool:
        """
        テンプレート変数を検証
        
        Args:
            template_name: テンプレート名
            variables: 検証対象変数
            
        Returns:
            bool: 検証結果
            
        Raises:
            TemplateNotFoundError: テンプレートが見つからない場合
            PromptValidationError: 変数不足の場合
        """
        template = self.get_template(template_name)
        
        if not template.validate(variables):
            missing_vars = set(template.variables) - set(variables.keys())
            raise PromptValidationError(
                f"必要な変数が不足しています: {missing_vars}",
                template_name=template_name,
                missing_variables=list(missing_vars)
            )
        
        return True
    
    def render_template(self, template_name: str, variables: Dict[str, Any]) -> str:
        """
        テンプレートをレンダリング
        
        Args:
            template_name: テンプレート名
            variables: テンプレート変数
            
        Returns:
            str: レンダリング結果
            
        Raises:
            TemplateNotFoundError: テンプレートが見つからない場合
            PromptValidationError: 変数不足の場合
        """
        template = self.get_template(template_name)
        return template.render(variables)
    
    def update_template(self, name: str, template: PromptTemplate) -> None:
        """
        テンプレートを更新
        
        Args:
            name: 更新対象テンプレート名
            template: 新しいテンプレート
            
        Raises:
            TemplateNotFoundError: テンプレートが見つからない場合
        """
        if name not in self.templates:
            raise TemplateNotFoundError(
                f"更新対象のテンプレートが見つかりません: {name}",
                template_name=name
            )
        
        # 名前を更新対象に合わせる
        template.name = name
        self.templates[name] = template
        
        logger.info(f"テンプレート更新完了: {name}")
    
    def delete_template(self, name: str) -> None:
        """
        テンプレートを削除
        
        Args:
            name: 削除対象テンプレート名
            
        Raises:
            TemplateNotFoundError: テンプレートが見つからない場合
            ValueError: システムテンプレートを削除しようとした場合
        """
        if name not in self.templates:
            raise TemplateNotFoundError(
                f"削除対象のテンプレートが見つかりません: {name}",
                template_name=name
            )
        
        if name in self._system_templates:
            raise ValueError(f"システムテンプレートは削除できません: {name}")
        
        del self.templates[name]
        logger.info(f"テンプレート削除完了: {name}")
    
    def export_templates(self) -> Dict[str, Any]:
        """
        テンプレートをエクスポート
        
        Returns:
            Dict[str, Any]: エクスポートデータ
        """
        export_data = {
            "templates": {},
            "metadata": {
                "version": "1.0",
                "exported_at": datetime.now().isoformat(),
                "total_templates": len(self.templates)
            }
        }
        
        for name, template in self.templates.items():
            export_data["templates"][name] = {
                "name": template.name,
                "template": template.template,
                "variables": template.variables,
                "description": template.description,
                "tags": template.tags,
                "created_at": template.created_at
            }
        
        return export_data
    
    def import_templates(self, data: Dict[str, Any]) -> None:
        """
        テンプレートをインポート
        
        Args:
            data: インポートデータ
        """
        templates_data = data.get("templates", {})
        
        for name, template_data in templates_data.items():
            template = PromptTemplate(
                name=template_data["name"],
                template=template_data["template"],
                variables=template_data["variables"],
                description=template_data.get("description", ""),
                tags=template_data.get("tags", []),
                created_at=template_data.get("created_at", datetime.now().isoformat())
            )
            
            # システムテンプレートは上書きしない
            if name not in self._system_templates:
                self.templates[name] = template
        
        logger.info(f"テンプレートインポート完了: {len(templates_data)}件")

class PromptBuilder(ABC):
    """プロンプトビルダー基底クラス"""
    
    @abstractmethod
    def build_system_prompt(self) -> str:
        """システムプロンプトを構築"""
        pass

class RAGPromptBuilder(PromptBuilder):
    """RAG用プロンプトビルダー"""
    
    def __init__(self, template_manager: Optional[PromptTemplateManager] = None):
        """
        初期化
        
        Args:
            template_manager: テンプレートマネージャー
        """
        self.template_manager = template_manager or PromptTemplateManager()
    
    def build_system_prompt(self) -> str:
        """RAGシステムプロンプトを構築"""
        return self.template_manager.render_template("rag_system", {})
    
    def build_user_prompt(
        self, 
        query: str, 
        context_chunks: List[str],
        include_metadata: bool = False,
        metadata: Optional[List[Dict[str, Any]]] = None
    ) -> str:
        """
        RAGユーザープロンプトを構築
        
        Args:
            query: ユーザーの質問
            context_chunks: コンテキストチャンク
            include_metadata: メタデータを含むか
            metadata: チャンクのメタデータ
            
        Returns:
            str: ユーザープロンプト
        """
        if not context_chunks:
            context = "関連する文書が見つかりませんでした。"
        else:
            if include_metadata and metadata:
                context_parts = []
                for i, chunk in enumerate(context_chunks):
                    meta = metadata[i] if i < len(metadata) else {}
                    filename = meta.get("filename", "不明")
                    page = meta.get("page", "不明")
                    
                    context_parts.append(f"[出典: {filename}, page: {page}]\n{chunk}")
                
                context = "\n\n---\n\n".join(context_parts)
            else:
                context = "\n\n---\n\n".join(context_chunks)
        
        return self.template_manager.render_template("rag_user", {
            "context": context,
            "question": query
        })
    
    def build_conversation_prompt(
        self,
        query: str,
        context_chunks: List[str],
        chat_history: List[Dict[str, str]]
    ) -> List[Dict[str, str]]:
        """
        会話形式RAGプロンプトを構築
        
        Args:
            query: 現在の質問
            context_chunks: コンテキストチャンク
            chat_history: チャット履歴
            
        Returns:
            List[Dict[str, str]]: メッセージリスト
        """
        messages = []
        
        # システムメッセージ
        system_prompt = self.template_manager.render_template("conversation_system", {})
        messages.append({"role": "system", "content": system_prompt})
        
        # チャット履歴
        messages.extend(chat_history)
        
        # 現在のプロンプト
        user_prompt = self.build_user_prompt(query, context_chunks)
        messages.append({"role": "user", "content": user_prompt})
        
        return messages

class ConversationPromptBuilder(PromptBuilder):
    """会話用プロンプトビルダー"""
    
    def __init__(self, template_manager: Optional[PromptTemplateManager] = None):
        self.template_manager = template_manager or PromptTemplateManager()
    
    def build_system_prompt(self) -> str:
        """会話システムプロンプトを構築"""
        return self.template_manager.render_template("conversation_system", {})
    
    def format_chat_history(self, chat_history: List[Dict[str, str]]) -> List[Dict[str, str]]:
        """
        チャット履歴をフォーマット
        
        Args:
            chat_history: 生のチャット履歴
            
        Returns:
            List[Dict[str, str]]: フォーマット済み履歴
        """
        formatted = []
        for msg in chat_history:
            if "role" in msg and "content" in msg:
                formatted.append({
                    "role": msg["role"],
                    "content": msg["content"]
                })
        
        return formatted
    
    def build_conversational_prompt(
        self,
        query: str,
        context: str,
        history: List[Dict[str, str]]
    ) -> List[Dict[str, str]]:
        """
        会話型プロンプトを構築
        
        Args:
            query: 現在の質問
            context: コンテキスト
            history: チャット履歴
            
        Returns:
            List[Dict[str, str]]: メッセージリスト
        """
        messages = []
        
        # システムメッセージ
        messages.append({
            "role": "system",
            "content": self.build_system_prompt()
        })
        
        # 履歴
        messages.extend(self.format_chat_history(history))
        
        # 現在のクエリ（コンテキスト付き）
        current_prompt = f"""参考情報:
{context}

質問: {query}"""
        
        messages.append({
            "role": "user",
            "content": current_prompt
        })
        
        return messages

class SummarizationPromptBuilder(PromptBuilder):
    """要約用プロンプトビルダー"""
    
    def __init__(self, template_manager: Optional[PromptTemplateManager] = None):
        self.template_manager = template_manager or PromptTemplateManager()
    
    def build_system_prompt(self) -> str:
        """要約システムプロンプトを構築"""
        return self.template_manager.render_template("summarization_system", {})
    
    def build_summarization_prompt(
        self, 
        text: str, 
        max_length: int = 500,
        style: str = "bullet_points"
    ) -> str:
        """
        要約プロンプトを構築
        
        Args:
            text: 要約対象テキスト
            max_length: 最大文字数
            style: 要約スタイル（bullet_points, paragraph, key_points）
            
        Returns:
            str: 要約プロンプト
            
        Raises:
            ValueError: 無効なスタイルの場合
        """
        style_instructions = {
            "bullet_points": "箇条書き形式で簡潔にまとめてください",
            "paragraph": "段落形式で自然な文章としてまとめてください",
            "key_points": "重要なポイントを番号付きリストで整理してください"
        }
        
        if style not in style_instructions:
            raise ValueError(f"サポートされていないスタイル: {style}")
        
        system_prompt = self.build_system_prompt()
        
        user_prompt = f"""以下のテキストを{max_length}文字以内で要約してください。

要約スタイル: {style_instructions[style]}

対象テキスト:
{text}

要約:"""
        
        return f"{system_prompt}\n\n{user_prompt}"

# グローバルインスタンス
_global_template_manager = None

def get_template_manager() -> PromptTemplateManager:
    """グローバルテンプレートマネージャーを取得"""
    global _global_template_manager
    if _global_template_manager is None:
        _global_template_manager = PromptTemplateManager()
    return _global_template_manager