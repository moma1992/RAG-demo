"""
外部API統合テスト

OpenAI、Claude、Supabase APIとの統合テスト
"""

import pytest
from unittest.mock import Mock, patch
from services.embeddings import EmbeddingService
from services.claude_llm import ClaudeLLMService
from services.vector_store import VectorStore


class TestEmbeddingServiceIntegration:
    """埋め込みサービス統合テスト"""
    
    def test_text_embedding_generation(self, mock_openai_client):
        """テキスト埋め込み生成統合テスト"""
        service = EmbeddingService("test-api-key")
        text = "これはテスト用のサンプルテキストです。"
        
        result = service.create_embedding(text)
        
        assert result is not None
        assert hasattr(result, 'embedding')
        assert isinstance(result.embedding, list)
        assert len(result.embedding) == 1536  # OpenAI text-embedding-3-small dimension
        assert all(isinstance(val, float) for val in result.embedding)
    
    def test_batch_embedding_generation(self, mock_openai_client):
        """バッチ埋め込み生成統合テスト"""
        service = EmbeddingService("test-api-key")
        texts = [
            "テキスト1",
            "テキスト2", 
            "テキスト3"
        ]
        
        result = service.create_batch_embeddings(texts)
        
        assert result is not None
        assert hasattr(result, 'embeddings')
        assert isinstance(result.embeddings, list)
        assert len(result.embeddings) == len(texts)
        assert all(len(emb) == 1536 for emb in result.embeddings)


class TestClaudeLLMIntegration:
    """Claude LLM統合テスト"""
    
    def test_answer_generation(self, mock_claude_client):
        """回答生成統合テスト"""
        service = ClaudeLLMService("test-api-key")
        
        context_chunks = [
            "コンテキスト1: 会社の基本情報について",
            "コンテキスト2: 新入社員研修について" 
        ]
        question = "新入社員研修の内容を教えてください"
        
        result = service.generate_response(question, context_chunks)
        
        assert result is not None
        assert hasattr(result, 'content')
        assert isinstance(result.content, str)
        assert len(result.content) > 0
    
    def test_answer_with_context_metadata(self, mock_claude_client):
        """コンテキストメタデータ付き回答生成統合テスト"""
        service = ClaudeLLMService("test-api-key")
        
        context_chunks = [
            "新入社員研修は3週間実施されます。（研修資料.pdf, ページ1より）"
        ]
        question = "研修期間はどのくらいですか？"
        
        result = service.generate_response(question, context_chunks)
        
        assert result is not None
        assert hasattr(result, 'content')
        assert isinstance(result.content, str)
        assert len(result.content) > 0
        assert hasattr(result, 'usage')


class TestSupabaseIntegration:
    """Supabase統合テスト"""
    
    def test_database_connection(self, mock_supabase_client):
        """データベース接続統合テスト"""
        store = VectorStore("https://test.supabase.co", "test-key")
        
        # 接続テスト（初期化が成功することを確認）
        assert store.supabase_url == "https://test.supabase.co"
        assert store.supabase_key == "test-key"
    
    def test_vector_search_with_large_dataset(self, mock_supabase_client):
        """大量データでのベクトル検索統合テスト"""
        store = VectorStore("https://test.supabase.co", "test-key")
        
        # 大量のテストデータ準備
        test_chunks = []
        for i in range(100):
            chunk = {
                "content": f"テストコンテンツ{i}",
                "page_number": i % 10 + 1,
                "embedding": [0.1 + i * 0.001] * 1536
            }
            test_chunks.append(chunk)
        
        # データ保存
        document_id = "test-doc-id"
        store.store_chunks(test_chunks, document_id)
        
        # 検索実行
        query_embedding = [0.1] * 1536
        results = store.similarity_search(query_embedding, k=10)
        
        assert isinstance(results, list)
        assert len(results) <= 10  # 指定したk値以下