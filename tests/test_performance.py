"""
パフォーマンステスト

PDF処理とベクトル検索のパフォーマンス測定
"""

import pytest
import time
from memory_profiler import profile
from pathlib import Path
from unittest.mock import Mock, patch
from services.pdf_processor import PDFProcessor
from services.vector_store import VectorStore
from models.document import DocumentChunk


class TestPDFProcessorPerformance:
    """PDF処理パフォーマンステスト"""

    @pytest.mark.benchmark(group="pdf_processing")
    def test_pdf_processing_speed(self, benchmark, sample_pdf_bytes, mock_fitz, mock_spacy):
        """PDF処理速度テスト"""
        processor = PDFProcessor()
        
        def pdf_process():
            return processor.process_pdf(sample_pdf_bytes, "benchmark.pdf")
        
        result = benchmark(pdf_process)
        assert result is not None
        assert result.total_chunks > 0

    @pytest.mark.benchmark(group="pdf_processing")
    def test_large_pdf_processing(self, benchmark, mock_fitz, mock_spacy):
        """大きなPDF処理テスト"""
        processor = PDFProcessor()
        
        # 大きなPDFをシミュレート（10MB相当）
        large_pdf_data = b"%PDF-1.4\n" + b"x" * (10 * 1024 * 1024) + b"\n%%EOF"
        
        def large_pdf_process():
            return processor.process_pdf(large_pdf_data, "large_benchmark.pdf")
        
        result = benchmark(large_pdf_process)
        assert result is not None

    def test_pdf_processing_memory_usage(self, sample_pdf_bytes, mock_fitz, mock_spacy):
        """PDF処理メモリ使用量テスト"""
        processor = PDFProcessor()
        
        # メモリ使用量を追跡
        import psutil
        import os
        
        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss
        
        # PDF処理実行
        result = processor.process_pdf(sample_pdf_bytes, "memory_test.pdf")
        
        final_memory = process.memory_info().rss
        memory_increase = final_memory - initial_memory
        
        # メモリ増加が100MB以下であることを確認（Streamlit Cloud制約）
        assert memory_increase < 100 * 1024 * 1024
        assert result is not None

    @pytest.mark.slow
    def test_concurrent_pdf_processing(self, sample_pdf_bytes, mock_fitz, mock_spacy):
        """並行PDF処理テスト"""
        import concurrent.futures
        import threading
        
        processor = PDFProcessor()
        
        def process_single_pdf(index):
            return processor.process_pdf(sample_pdf_bytes, f"concurrent_{index}.pdf")
        
        start_time = time.time()
        
        # 5つのPDFを並行処理
        with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
            futures = [executor.submit(process_single_pdf, i) for i in range(5)]
            results = [future.result() for future in concurrent.futures.as_completed(futures)]
        
        elapsed_time = time.time() - start_time
        
        # 5つのPDFを2分以内で処理できることを確認
        assert elapsed_time < 120
        assert len(results) == 5
        assert all(result.total_chunks > 0 for result in results)


class TestVectorStorePerformance:
    """ベクトルストアパフォーマンステスト"""

    @pytest.mark.benchmark(group="vector_search")
    def test_similarity_search_speed(self, benchmark, mock_supabase_client):
        """類似検索速度テスト"""
        store = VectorStore("https://test.supabase.co", "test-key")
        query_embedding = [0.1] * 1536
        
        def similarity_search():
            return store.similarity_search(query_embedding, k=10)
        
        result = benchmark(similarity_search)
        assert isinstance(result, list)

    @pytest.mark.benchmark(group="vector_search")
    def test_bulk_chunk_storage(self, benchmark, mock_supabase_client):
        """大量チャンク保存速度テスト"""
        store = VectorStore("https://test.supabase.co", "test-key")
        
        # 1000個のチャンクを準備
        chunks = [
            {
                "content": f"テストチャンク{i}",
                "page_number": i % 10 + 1,
                "token_count": 50,
                "embedding": [0.1 + i * 0.001] * 1536
            }
            for i in range(1000)
        ]
        
        def bulk_store():
            store.store_chunks(chunks, "bulk_test_document_id")
        
        benchmark(bulk_store)

    def test_search_response_time(self, mock_supabase_client):
        """検索レスポンス時間テスト"""
        store = VectorStore("https://test.supabase.co", "test-key")
        query_embedding = [0.1] * 1536
        
        start_time = time.time()
        results = store.similarity_search(query_embedding, k=5)
        elapsed_time = time.time() - start_time
        
        # 検索が1秒以内に完了することを確認
        assert elapsed_time < 1.0
        assert isinstance(results, list)


class TestEndToEndPerformance:
    """エンドツーエンドパフォーマンステスト"""

    @pytest.mark.slow
    def test_full_document_pipeline_performance(
        self, 
        sample_pdf_bytes, 
        mock_fitz, 
        mock_spacy, 
        mock_supabase_client,
        mock_openai_client
    ):
        """完全文書処理パイプライン性能テスト"""
        from services.embeddings import EmbeddingService
        
        start_time = time.time()
        
        # 1. PDF処理
        pdf_processor = PDFProcessor()
        pdf_result = pdf_processor.process_pdf(sample_pdf_bytes, "pipeline_test.pdf")
        
        # 2. 埋め込み生成
        embedding_service = EmbeddingService()
        for chunk in pdf_result.chunks:
            chunk.embedding = embedding_service.create_embedding(chunk.content)
        
        # 3. ベクトルストア保存
        vector_store = VectorStore("https://test.supabase.co", "test-key")
        document_id = vector_store.store_document({
            "filename": "pipeline_test.pdf",
            "file_size": len(sample_pdf_bytes),
            "total_pages": pdf_result.total_pages
        })
        
        chunk_data = [
            {
                "content": chunk.content,
                "page_number": chunk.page_number,
                "token_count": chunk.token_count,
                "embedding": chunk.embedding
            }
            for chunk in pdf_result.chunks
        ]
        vector_store.store_chunks(chunk_data, document_id)
        
        # 4. 検索実行
        query_embedding = embedding_service.create_embedding("テストクエリ")
        search_results = vector_store.similarity_search(query_embedding, k=5)
        
        total_time = time.time() - start_time
        
        # パイプライン全体が2分以内で完了することを確認
        assert total_time < 120
        assert pdf_result.total_chunks > 0
        assert document_id is not None
        assert isinstance(search_results, list)

    def test_memory_leak_detection(self, sample_pdf_bytes, mock_fitz, mock_spacy):
        """メモリリーク検出テスト"""
        import gc
        import psutil
        import os
        
        processor = PDFProcessor()
        process = psutil.Process(os.getpid())
        
        initial_memory = process.memory_info().rss
        
        # 同じPDFを100回処理
        for i in range(100):
            result = processor.process_pdf(sample_pdf_bytes, f"leak_test_{i}.pdf")
            
            # 定期的にガベージコレクション実行
            if i % 10 == 0:
                gc.collect()
        
        final_memory = process.memory_info().rss
        memory_increase = final_memory - initial_memory
        
        # メモリ増加が50MB以下であることを確認（メモリリークなし）
        assert memory_increase < 50 * 1024 * 1024

    @pytest.mark.benchmark(group="data_model")
    def test_document_chunk_creation_speed(self, benchmark):
        """DocumentChunk作成速度テスト"""
        def create_chunks():
            chunks = []
            for i in range(1000):
                chunk = DocumentChunk(
                    content=f"ベンチマークチャンク{i}",
                    filename="benchmark.pdf",
                    page_number=i % 10 + 1,
                    token_count=25,
                    embedding=[0.1] * 1536
                )
                chunks.append(chunk)
            return chunks
        
        chunks = benchmark(create_chunks)
        assert len(chunks) == 1000

    @pytest.mark.timeout(120)
    def test_timeout_compliance(self, sample_pdf_bytes, mock_fitz, mock_spacy):
        """タイムアウト制約遵守テスト"""
        processor = PDFProcessor()
        
        # 大量のPDFを処理して2分以内に完了することを確認
        start_time = time.time()
        
        for i in range(50):
            result = processor.process_pdf(sample_pdf_bytes, f"timeout_test_{i}.pdf")
            assert result is not None
        
        elapsed_time = time.time() - start_time
        assert elapsed_time < 120  # 2分以内


@pytest.mark.slow
class TestStressTests:
    """ストレステスト"""

    def test_high_load_pdf_processing(self, sample_pdf_bytes, mock_fitz, mock_spacy):
        """高負荷PDF処理テスト"""
        processor = PDFProcessor()
        
        # 複数のPDFを連続処理
        results = []
        start_time = time.time()
        
        for i in range(20):
            result = processor.process_pdf(sample_pdf_bytes, f"stress_test_{i}.pdf")
            results.append(result)
        
        elapsed_time = time.time() - start_time
        
        # 20個のPDFを2分以内で処理
        assert elapsed_time < 120
        assert len(results) == 20
        assert all(result.total_chunks > 0 for result in results)

    def test_large_embedding_vectors(self, mock_supabase_client):
        """大量埋め込みベクトルテスト"""
        store = VectorStore("https://test.supabase.co", "test-key")
        
        # 10,000個の埋め込みベクトルをシミュレート
        large_chunks = [
            {
                "content": f"大量データチャンク{i}",
                "page_number": i % 100 + 1,
                "token_count": 50,
                "embedding": [0.001 * j for j in range(1536)]
            }
            for i in range(10000)
        ]
        
        start_time = time.time()
        store.store_chunks(large_chunks, "large_document_id")
        elapsed_time = time.time() - start_time
        
        # 10,000個のチャンクを2分以内で保存
        assert elapsed_time < 120