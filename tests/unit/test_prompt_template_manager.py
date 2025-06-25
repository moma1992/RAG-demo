"""
プロンプトテンプレート管理のユニットテスト

TDD Red段階 - 失敗するテストケースを先に作成
"""

import pytest
from unittest.mock import Mock, patch
from dataclasses import dataclass
from typing import List, Dict, Any, Optional
from datetime import datetime

from utils.prompt_templates import (
    PromptTemplateManager,
    PromptTemplate,
    RAGPromptBuilder,
    ConversationPromptBuilder,
    SummarizationPromptBuilder,
    PromptValidationError,
    TemplateNotFoundError
)


class TestPromptTemplateManager:
    """PromptTemplateManagerクラステスト"""
    
    @pytest.fixture
    def template_manager(self):
        """PromptTemplateManagerインスタンス"""
        return PromptTemplateManager()
    
    def test_init_default_templates(self, template_manager):
        """デフォルトテンプレート初期化テスト"""
        # デフォルトで必要なテンプレートが登録されていることを確認
        assert "rag_system" in template_manager.templates
        assert "rag_user" in template_manager.templates
        assert "conversation_system" in template_manager.templates
        assert "summarization_system" in template_manager.templates
        
        # 各テンプレートが適切なタイプであることを確認
        assert isinstance(template_manager.templates["rag_system"], PromptTemplate)
    
    def test_register_template(self, template_manager):
        """テンプレート登録テスト"""
        custom_template = PromptTemplate(
            name="custom_test",
            template="これはテスト用カスタムテンプレートです: {content}",
            variables=["content"],
            description="テスト用"
        )
        
        template_manager.register_template(custom_template)
        
        assert "custom_test" in template_manager.templates
        assert template_manager.templates["custom_test"] == custom_template
    
    def test_register_duplicate_template(self, template_manager):
        """重複テンプレート登録テスト"""
        # 既存テンプレートと同じ名前で登録しようとする
        duplicate_template = PromptTemplate(
            name="rag_system",
            template="新しいテンプレート",
            variables=[],
            description="重複テスト"
        )
        
        with pytest.raises(ValueError) as exc_info:
            template_manager.register_template(duplicate_template)
        
        assert "すでに登録されています" in str(exc_info.value)
    
    def test_get_template_existing(self, template_manager):
        """既存テンプレート取得テスト"""
        template = template_manager.get_template("rag_system")
        
        assert isinstance(template, PromptTemplate)
        assert template.name == "rag_system"
        assert "新入社員向け" in template.template
    
    def test_get_template_not_found(self, template_manager):
        """存在しないテンプレート取得テスト"""
        with pytest.raises(TemplateNotFoundError) as exc_info:
            template_manager.get_template("non_existent")
        
        assert "テンプレートが見つかりません" in str(exc_info.value)
        assert "non_existent" in str(exc_info.value)
    
    def test_list_templates(self, template_manager):
        """テンプレート一覧取得テスト"""
        templates = template_manager.list_templates()
        
        assert isinstance(templates, dict)
        assert len(templates) >= 4  # デフォルトテンプレート数
        assert "rag_system" in templates
        assert all(isinstance(t, PromptTemplate) for t in templates.values())
    
    def test_validate_template_variables(self, template_manager):
        """テンプレート変数検証テスト"""
        # 正常なケース
        is_valid = template_manager.validate_template_variables(
            "rag_user",
            {"context": "テストコンテキスト", "question": "テスト質問"}
        )
        assert is_valid
        
        # 必要な変数が不足しているケース
        with pytest.raises(PromptValidationError) as exc_info:
            template_manager.validate_template_variables(
                "rag_user",
                {"context": "コンテキストのみ"}  # questionが不足
            )
        
        assert "必要な変数が不足しています" in str(exc_info.value)
        assert "question" in str(exc_info.value)
    
    def test_render_template(self, template_manager):
        """テンプレートレンダリングテスト"""
        variables = {
            "context": "テスト用のコンテキスト",
            "question": "これはテスト質問ですか？"
        }
        
        rendered = template_manager.render_template("rag_user", variables)
        
        assert isinstance(rendered, str)
        assert "テスト用のコンテキスト" in rendered
        assert "これはテスト質問ですか？" in rendered
        assert "context" in rendered  # RAGテンプレートの構造
    
    def test_render_template_missing_variables(self, template_manager):
        """変数不足でのレンダリングテスト"""
        with pytest.raises(PromptValidationError):
            template_manager.render_template("rag_user", {"context": "コンテキストのみ"})
    
    def test_update_template(self, template_manager):
        """テンプレート更新テスト"""
        new_template = PromptTemplate(
            name="rag_system",
            template="更新されたシステムプロンプト: {system_info}",
            variables=["system_info"],
            description="更新テスト"
        )
        
        template_manager.update_template("rag_system", new_template)
        
        updated = template_manager.get_template("rag_system")
        assert "更新されたシステムプロンプト" in updated.template
        assert updated.variables == ["system_info"]
    
    def test_delete_template(self, template_manager):
        """テンプレート削除テスト"""
        # カスタムテンプレートを追加
        custom_template = PromptTemplate(
            name="deletable_test",
            template="削除テスト用",
            variables=[],
            description="削除テスト"
        )
        template_manager.register_template(custom_template)
        
        # 削除実行
        template_manager.delete_template("deletable_test")
        
        # 削除確認
        with pytest.raises(TemplateNotFoundError):
            template_manager.get_template("deletable_test")
    
    def test_delete_system_template(self, template_manager):
        """システムテンプレート削除防止テスト"""
        with pytest.raises(ValueError) as exc_info:
            template_manager.delete_template("rag_system")
        
        assert "システムテンプレートは削除できません" in str(exc_info.value)
    
    def test_export_templates(self, template_manager):
        """テンプレートエクスポートテスト"""
        exported = template_manager.export_templates()
        
        assert isinstance(exported, dict)
        assert "templates" in exported
        assert "metadata" in exported
        assert "version" in exported["metadata"]
        assert len(exported["templates"]) >= 4
    
    def test_import_templates(self, template_manager):
        """テンプレートインポートテスト"""
        template_data = {
            "templates": {
                "imported_test": {
                    "name": "imported_test",
                    "template": "インポートテスト: {data}",
                    "variables": ["data"],
                    "description": "インポートテスト用"
                }
            },
            "metadata": {
                "version": "1.0",
                "exported_at": datetime.now().isoformat()
            }
        }
        
        template_manager.import_templates(template_data)
        
        imported_template = template_manager.get_template("imported_test")
        assert imported_template.name == "imported_test"
        assert "インポートテスト" in imported_template.template


class TestRAGPromptBuilder:
    """RAGPromptBuilderクラステスト"""
    
    @pytest.fixture
    def rag_builder(self):
        """RAGPromptBuilderインスタンス"""
        return RAGPromptBuilder()
    
    def test_build_system_prompt(self, rag_builder):
        """RAGシステムプロンプト構築テスト"""
        system_prompt = rag_builder.build_system_prompt()
        
        assert isinstance(system_prompt, str)
        assert "新入社員向け" in system_prompt
        assert "社内文書検索アシスタント" in system_prompt
        assert "提供された文書の内容に基づいて" in system_prompt
    
    def test_build_user_prompt_with_context(self, rag_builder):
        """コンテキスト付きRAGユーザープロンプト構築テスト"""
        query = "研修について教えてください"
        context_chunks = [
            "研修は3日間実施されます。",
            "初日はオリエンテーションです。"
        ]
        
        user_prompt = rag_builder.build_user_prompt(query, context_chunks)
        
        assert isinstance(user_prompt, str)
        assert "context" in user_prompt
        assert "研修は3日間実施されます。" in user_prompt
        assert "初日はオリエンテーションです。" in user_prompt
        assert "question" in user_prompt
        assert query in user_prompt
    
    def test_build_user_prompt_empty_context(self, rag_builder):
        """空コンテキストでのRAGユーザープロンプト構築テスト"""
        query = "質問内容"
        context_chunks = []
        
        user_prompt = rag_builder.build_user_prompt(query, context_chunks)
        
        assert "関連する文書が見つかりませんでした" in user_prompt
        assert query in user_prompt
    
    def test_build_user_prompt_with_metadata(self, rag_builder):
        """メタデータ付きRAGプロンプト構築テスト"""
        query = "質問"
        context_chunks = ["コンテキスト1", "コンテキスト2"]
        metadata = [
            {"filename": "doc1.pdf", "page": 1},
            {"filename": "doc2.pdf", "page": 3}
        ]
        
        user_prompt = rag_builder.build_user_prompt(
            query, context_chunks, include_metadata=True, metadata=metadata
        )
        
        assert "doc1.pdf" in user_prompt
        assert "page: 1" in user_prompt
        assert "doc2.pdf" in user_prompt
        assert "page: 3" in user_prompt
    
    def test_build_conversation_prompt(self, rag_builder):
        """会話形式RAGプロンプト構築テスト"""
        query = "さらに詳しく教えてください"
        context_chunks = ["詳細情報"]
        chat_history = [
            {"role": "user", "content": "研修について教えて"},
            {"role": "assistant", "content": "研修は3日間です"}
        ]
        
        conversation_prompt = rag_builder.build_conversation_prompt(
            query, context_chunks, chat_history
        )
        
        assert isinstance(conversation_prompt, list)
        assert len(conversation_prompt) >= 3  # system + history + new user
        assert conversation_prompt[0]["role"] == "system"
        assert conversation_prompt[-1]["role"] == "user"


class TestConversationPromptBuilder:
    """ConversationPromptBuilderクラステスト"""
    
    @pytest.fixture
    def conversation_builder(self):
        """ConversationPromptBuilderインスタンス"""
        return ConversationPromptBuilder()
    
    def test_build_system_prompt(self, conversation_builder):
        """会話システムプロンプト構築テスト"""
        system_prompt = conversation_builder.build_system_prompt()
        
        assert "会話履歴を考慮" in system_prompt
        assert "自然な対話" in system_prompt
    
    def test_format_chat_history(self, conversation_builder):
        """チャット履歴フォーマットテスト"""
        chat_history = [
            {"role": "user", "content": "質問1"},
            {"role": "assistant", "content": "回答1"},
            {"role": "user", "content": "質問2"}
        ]
        
        formatted = conversation_builder.format_chat_history(chat_history)
        
        assert isinstance(formatted, list)
        assert len(formatted) == 3
        assert all("role" in msg for msg in formatted)
        assert all("content" in msg for msg in formatted)
    
    def test_build_conversational_prompt(self, conversation_builder):
        """会話型プロンプト構築テスト"""
        query = "続きを教えて"
        context = "追加情報"
        history = [{"role": "user", "content": "最初の質問"}]
        
        messages = conversation_builder.build_conversational_prompt(
            query, context, history
        )
        
        assert isinstance(messages, list)
        assert messages[0]["role"] == "system"
        assert messages[-1]["role"] == "user"
        assert query in messages[-1]["content"]


class TestSummarizationPromptBuilder:
    """SummarizationPromptBuilderクラステスト"""
    
    @pytest.fixture
    def summarization_builder(self):
        """SummarizationPromptBuilderインスタンス"""
        return SummarizationPromptBuilder()
    
    def test_build_summarization_prompt(self, summarization_builder):
        """要約プロンプト構築テスト"""
        text = "これは要約対象の長いテキストです。" * 100
        max_length = 200
        style = "bullet_points"
        
        prompt = summarization_builder.build_summarization_prompt(
            text, max_length, style
        )
        
        assert isinstance(prompt, str)
        assert str(max_length) in prompt
        assert "箇条書き" in prompt  # bullet_pointsの日本語
        assert text[:100] in prompt  # テキストの一部が含まれる
    
    def test_build_summarization_prompt_different_styles(self, summarization_builder):
        """異なるスタイルでの要約プロンプト構築テスト"""
        text = "テストテキスト"
        
        # 段落スタイル
        paragraph_prompt = summarization_builder.build_summarization_prompt(
            text, 100, "paragraph"
        )
        assert "段落形式" in paragraph_prompt
        
        # キーポイントスタイル
        key_points_prompt = summarization_builder.build_summarization_prompt(
            text, 100, "key_points"
        )
        assert "重要なポイント" in key_points_prompt
    
    def test_build_summarization_prompt_invalid_style(self, summarization_builder):
        """無効なスタイルでの要約プロンプト構築テスト"""
        with pytest.raises(ValueError) as exc_info:
            summarization_builder.build_summarization_prompt(
                "text", 100, "invalid_style"
            )
        
        assert "サポートされていないスタイル" in str(exc_info.value)


class TestPromptTemplate:
    """PromptTemplateクラステスト"""
    
    def test_prompt_template_creation(self):
        """PromptTemplate作成テスト"""
        template = PromptTemplate(
            name="test_template",
            template="これは{variable1}と{variable2}のテストです",
            variables=["variable1", "variable2"],
            description="テスト用テンプレート",
            tags=["test", "example"]
        )
        
        assert template.name == "test_template"
        assert template.template == "これは{variable1}と{variable2}のテストです"
        assert template.variables == ["variable1", "variable2"]
        assert template.description == "テスト用テンプレート"
        assert template.tags == ["test", "example"]
    
    def test_prompt_template_render(self):
        """PromptTemplateレンダリングテスト"""
        template = PromptTemplate(
            name="render_test",
            template="Hello {name}, you are {age} years old",
            variables=["name", "age"]
        )
        
        rendered = template.render({"name": "John", "age": "25"})
        
        assert rendered == "Hello John, you are 25 years old"
    
    def test_prompt_template_render_missing_variable(self):
        """変数不足でのレンダリングテスト"""
        template = PromptTemplate(
            name="error_test",
            template="Hello {name}",
            variables=["name"]
        )
        
        with pytest.raises(PromptValidationError):
            template.render({})
    
    def test_prompt_template_validate(self):
        """PromptTemplateバリデーションテスト"""
        template = PromptTemplate(
            name="validation_test",
            template="Test {var1} and {var2}",
            variables=["var1", "var2"]
        )
        
        # 正常なケース
        assert template.validate({"var1": "value1", "var2": "value2"})
        
        # 変数不足
        assert not template.validate({"var1": "value1"})
        
        # 余分な変数（これは許可される）
        assert template.validate({"var1": "value1", "var2": "value2", "extra": "value"})


class TestPromptValidationError:
    """PromptValidationErrorクラステスト"""
    
    def test_prompt_validation_error_creation(self):
        """PromptValidationError作成テスト"""
        error = PromptValidationError(
            "バリデーションエラー",
            template_name="test_template",
            missing_variables=["var1", "var2"]
        )
        
        assert str(error) == "バリデーションエラー"
        assert error.template_name == "test_template"
        assert error.missing_variables == ["var1", "var2"]


class TestTemplateNotFoundError:
    """TemplateNotFoundErrorクラステスト"""
    
    def test_template_not_found_error_creation(self):
        """TemplateNotFoundError作成テスト"""
        error = TemplateNotFoundError("テンプレートが見つかりません", template_name="missing_template")
        
        assert str(error) == "テンプレートが見つかりません"
        assert error.template_name == "missing_template"