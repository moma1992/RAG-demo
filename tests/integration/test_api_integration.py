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
        service = EmbeddingService()
        text = "これはテスト用のサンプルテキストです。"
        
        embedding = service.generate_embedding(text)
        
        assert embedding is not None
        assert isinstance(embedding, list)
        assert len(embedding) == 1536  # OpenAI text-embedding-3-small dimension
        assert all(isinstance(val, float) for val in embedding)
    
    def test_batch_embedding_generation(self, mock_openai_client):
        """バッチ埋め込み生成統合テスト"""
        service = EmbeddingService()
        texts = [
            "テキスト1",
            "テキスト2", 
            "テキスト3"
        ]
        
        embeddings = service.generate_batch_embeddings(texts)
        
        assert embeddings is not None
        assert isinstance(embeddings, list)
        assert len(embeddings) == len(texts)
        assert all(len(emb) == 1536 for emb in embeddings)


class TestClaudeLLMIntegration:
    """Claude LLM統合テスト"""
    
    def test_answer_generation(self, mock_claude_client):
        """回答生成統合テスト"""
        service = ClaudeLLMService()
        
        context_chunks = [
            "コンテキスト1: 会社の基本情報について",
            "コンテキスト2: 新入社員研修について" 
        ]
        question = "新入社員研修の内容を教えてください"
        
        answer = service.generate_answer(question, context_chunks)
        
        assert answer is not None
        assert isinstance(answer, str)
        assert len(answer) > 0
    
    def test_answer_with_citations(self, mock_claude_client):
        """引用付き回答生成統合テスト"""
        service = ClaudeLLMService()
        
        context_chunks = [
            {
                "content": "新入社員研修は3週間実施されます。",
                "filename": "研修資料.pdf",
                "page_number": 1
            }
        ]
        question = "研修期間はどのくらいですか？"
        
        result = service.generate_answer_with_citations(question, context_chunks)
        
        assert result is not None
        assert "answer" in result
        assert "citations" in result
        assert isinstance(result["citations"], list)


class TestSupabaseIntegration:
    """Supabase統合テスト"""
    
    def test_database_connection(self, mock_supabase_client):
        """データベース接続統合テスト"""
        store = VectorStore("https://test.supabase.co", "test-key")
        
        # 接続テスト（実際の接続確認）
        connection_status = store.test_connection()
        
        assert connection_status is not None
    
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