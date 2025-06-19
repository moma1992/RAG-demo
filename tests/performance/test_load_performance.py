"""
パフォーマンス・負荷テスト

システムの性能測定とボトルネック特定
"""

import pytest
import time
from unittest.mock import Mock, patch
from services.pdf_processor import PDFProcessor
from services.vector_store import VectorStore
from services.embeddings import EmbeddingService


class TestPDFProcessingPerformance:
    """PDF処理パフォーマンステスト"""
    
    def test_large_pdf_processing_time(self, mock_fitz, mock_spacy):
        """大きなPDF処理時間テスト"""
        processor = PDFProcessor()
        
        # 大きなPDFファイルをシミュレート
        large_pdf_bytes = b"%PDF-1.4\n" + b"large content " * 10000 + b"\n%%EOF"
        
        start_time = time.time()
        result = processor.process_pdf(large_pdf_bytes, "large_test.pdf")
        processing_time = time.time() - start_time
        
        # パフォーマンス要件確認
        assert processing_time < 30.0  # 30秒以内
        assert result.processing_time > 0
        assert result.total_chunks > 0
    
    def test_multiple_pdf_concurrent_processing(self, mock_fitz, mock_spacy):
        """複数PDF同時処理テスト"""
        processor = PDFProcessor()
        
        # 複数のPDFファイルを準備
        pdf_files = []
        for i in range(5):
            pdf_bytes = f"%PDF-1.4\ntest content {i}\n%%EOF".encode()
            pdf_files.append((pdf_bytes, f"test_{i}.pdf"))
        
        start_time = time.time()
        results = []
        
        # 順次処理（並行処理の実装は将来的に）
        for pdf_bytes, filename in pdf_files:
            result = processor.process_pdf(pdf_bytes, filename)
            results.append(result)
        
        total_time = time.time() - start_time
        
        # パフォーマンス要件
        assert total_time < 60.0  # 1分以内
        assert len(results) == 5
        assert all(r.total_chunks > 0 for r in results)


class TestVectorSearchPerformance:
    """ベクトル検索パフォーマンステスト"""
    
    def test_similarity_search_response_time(self, mock_supabase_client):
        """類似検索応答時間テスト"""
        store = VectorStore("https://test.supabase.co", "test-key")
        
        # 大量のテストデータを準備
        test_chunks = []
        for i in range(1000):
            chunk = {
                "content": f"テストコンテンツ{i}",
                "embedding": [0.1 + i * 0.0001] * 1536
            }
            test_chunks.append(chunk)
        
        # データ保存
        store.store_chunks(test_chunks, "performance-test-doc")
        
        # 検索性能測定
        query_embedding = [0.1] * 1536
        search_times = []
        
        for _ in range(10):  # 10回検索実行
            start_time = time.time()
            results = store.similarity_search(query_embedding, k=5)
            search_time = time.time() - start_time
            search_times.append(search_time)
        
        avg_search_time = sum(search_times) / len(search_times)
        
        # パフォーマンス要件
        assert avg_search_time < 2.0  # 平均2秒以内
        assert max(search_times) < 5.0  # 最大5秒以内
    
    def test_batch_embedding_performance(self, mock_openai_client):
        """バッチ埋め込み生成性能テスト"""
        service = EmbeddingService("test-api-key")
        
        # 大量のテキストを準備
        texts = [f"テストテキスト{i}です。" for i in range(100)]
        
        start_time = time.time()
        result = service.create_batch_embeddings(texts)
        processing_time = time.time() - start_time
        
        # パフォーマンス要件
        assert processing_time < 30.0  # 30秒以内
        assert len(result.embeddings) == len(texts)
        
        # スループット計算
        throughput = len(texts) / processing_time
        assert throughput > 1.0  # 1テキスト/秒以上


class TestMemoryUsage:
    """メモリ使用量テスト"""
    
    def test_pdf_processing_memory_efficiency(self, mock_fitz, mock_spacy):
        """PDF処理メモリ効率テスト"""
        processor = PDFProcessor()
        
        # Streamlit Cloud制約: 1GB メモリ
        # 大きなファイルでもメモリ効率的に処理できるかテスト
        large_pdf_bytes = b"%PDF-1.4\n" + b"content " * 100000 + b"\n%%EOF"
        
        try:
            result = processor.process_pdf(large_pdf_bytes, "memory_test.pdf")
            # メモリエラーが発生しないことを確認
            assert result is not None
            assert result.total_chunks > 0
        except MemoryError:
            pytest.fail("メモリ不足エラーが発生しました")
    
    def test_vector_store_memory_efficient_search(self, mock_supabase_client):
        """ベクトルストアメモリ効率検索テスト"""
        store = VectorStore("https://test.supabase.co", "test-key")
        
        # 大量検索でもメモリ効率的に動作するかテスト
        query_embedding = [0.1] * 1536
        
        try:
            # 複数回検索実行
            for _ in range(50):
                results = store.similarity_search(query_embedding, k=10)
                assert isinstance(results, list)
        except MemoryError:
            pytest.fail("メモリ不足エラーが発生しました")


class TestScalabilityBenchmark:
    """スケーラビリティベンチマーク"""
    
    @pytest.mark.slow
    def test_document_volume_scalability(self, mock_supabase_client):
        """文書量スケーラビリティテスト"""
        store = VectorStore("https://test.supabase.co", "test-key")
        
        # 段階的に文書数を増加させてパフォーマンス測定
        document_counts = [10, 50, 100, 500]
        performance_results = []
        
        for doc_count in document_counts:
            # テストデータ準備
            chunks = []
            for i in range(doc_count * 10):  # 1文書あたり10チャンク
                chunk = {
                    "content": f"文書{i//10}_チャンク{i%10}",
                    "embedding": [0.1 + i * 0.00001] * 1536
                }
                chunks.append(chunk)
            
            # 保存時間測定
            start_time = time.time()
            store.store_chunks(chunks, f"scalability-test-{doc_count}")
            store_time = time.time() - start_time
            
            # 検索時間測定
            query_embedding = [0.1] * 1536
            start_time = time.time()
            results = store.similarity_search(query_embedding, k=5)
            search_time = time.time() - start_time
            
            performance_results.append({
                "document_count": doc_count,
                "store_time": store_time,
                "search_time": search_time
            })
        
        # スケーラビリティ要件確認
        for result in performance_results:
            assert result["store_time"] < 60.0  # 1分以内
            assert result["search_time"] < 5.0   # 5秒以内
        
        # パフォーマンス劣化が線形以下であることを確認
        # （実装では詳細な分析を行う）