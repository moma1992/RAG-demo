"""
完全パイプライン統合テスト

PDF処理からベクトル検索までの全体的な統合テスト
"""

import pytest
from unittest.mock import Mock, patch
from services.pdf_processor import PDFProcessor
from services.vector_store import VectorStore
import uuid


class TestPDFProcessorIntegration:
    """PDF処理統合テスト"""
    
    def test_full_pdf_processing_pipeline(self, sample_pdf_bytes, mock_fitz, mock_spacy):
        """完全なPDF処理パイプラインテスト"""
        processor = PDFProcessor()
        filename = "integration_test.pdf"
        
        # 処理実行
        result = processor.process_pdf(sample_pdf_bytes, filename)
        
        # 結果検証
        assert result.total_pages > 0
        assert result.total_chunks > 0
        assert all(chunk.filename == filename for chunk in result.chunks)
        assert all(chunk.content for chunk in result.chunks)
        assert all(chunk.token_count > 0 for chunk in result.chunks)


class TestVectorStoreIntegration:
    """ベクトルストア統合テスト"""
    
    def test_document_lifecycle(self, mock_supabase_client):
        """文書ライフサイクル統合テスト"""
        store = VectorStore("https://test.supabase.co", "test-key")
        
        # 1. 文書保存
        document_data = {
            "filename": "lifecycle_test.pdf",
            "file_size": 2048,
            "total_pages": 5
        }
        document_id = store.store_document(document_data)
        
        # 2. チャンク保存
        chunks = [
            {
                "content": f"テストチャンク{i}",
                "page_number": i % 5 + 1,
                "embedding": [0.1 + i * 0.01] * 1536
            }
            for i in range(10)
        ]
        store.store_chunks(chunks, document_id)
        
        # 3. 検索実行
        query_embedding = [0.1] * 1536
        results = store.similarity_search(query_embedding)
        
        # 4. 文書一覧確認
        documents = store.get_documents()
        
        # 5. 文書削除
        store.delete_document(document_id)
        
        # 全ての操作がエラーなしで完了することを確認
        assert document_id is not None
        assert isinstance(results, list)
        assert isinstance(documents, list)


class TestFullSystemIntegration:
    """システム全体統合テスト"""
    
    def test_pdf_to_search_pipeline(
        self, 
        sample_pdf_bytes, 
        mock_fitz, 
        mock_spacy, 
        mock_supabase_client,
        mock_openai_client
    ):
        """PDF処理から検索までの完全パイプラインテスト"""
        # 1. PDF処理
        processor = PDFProcessor()
        filename = "full_pipeline_test.pdf"
        processing_result = processor.process_pdf(sample_pdf_bytes, filename)
        
        # 2. ベクトルストア保存
        store = VectorStore("https://test.supabase.co", "test-key")
        
        # 文書情報保存
        document_data = {
            "filename": filename,
            "file_size": len(sample_pdf_bytes),
            "total_pages": processing_result.total_pages
        }
        document_id = store.store_document(document_data)
        
        # チャンクデータ準備（埋め込みベクトル付き）
        chunks_with_embeddings = []
        for chunk in processing_result.chunks:
            chunk_data = {
                "content": chunk.content,
                "page_number": chunk.page_number,
                "token_count": chunk.token_count,
                "embedding": [0.1] * 1536  # モック埋め込み
            }
            chunks_with_embeddings.append(chunk_data)
        
        # チャンク保存
        store.store_chunks(chunks_with_embeddings, document_id)
        
        # 3. 検索実行
        query_embedding = [0.1] * 1536
        search_results = store.similarity_search(query_embedding)
        
        # 結果検証
        assert processing_result.total_chunks > 0
        assert document_id is not None
        assert isinstance(search_results, list)
        
        # パイプライン全体が正常に動作することを確認
        assert processing_result.errors == []