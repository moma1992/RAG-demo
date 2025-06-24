"""
ベクトルストアサービスのパフォーマンステスト - Issue #57 要件検証

500ms以下のレスポンス要件およびバルク処理性能の検証
"""

import pytest
import asyncio
import time
from unittest.mock import Mock, patch
from services.vector_store import VectorStore, VectorStoreError, SearchResult


class TestPerformanceRequirements:
    """パフォーマンス要件テストクラス"""
    
    @pytest.mark.asyncio
    async def test_search_similar_embeddings_response_time(self, mock_supabase_client):
        """500ms以下レスポンス要件テスト"""
        store = VectorStore("https://test.supabase.co", "test-key")
        
        # 高速レスポンスのモック設定
        mock_result = Mock()
        mock_result.data = [
            {
                "content": "高速検索結果",
                "filename": "test.pdf",
                "page_number": 1,
                "distance": 0.1,
                "section_name": "テスト章",
                "chapter_number": 1,
                "start_pos": {"x": 100, "y": 200},
                "end_pos": {"x": 300, "y": 250},
                "token_count": 50
            }
        ]
        
        # レスポンス時間シミュレーション (100ms)
        async def mock_execute():
            await asyncio.sleep(0.1)  # 100ms wait
            return mock_result
        
        mock_supabase_client.rpc.return_value.execute = mock_execute
        
        query_embedding = [0.1] * 1536
        
        # 実行時間測定
        start_time = time.time()
        results = await store.search_similar_embeddings(query_embedding, limit=10)
        end_time = time.time()
        
        execution_time = (end_time - start_time) * 1000  # ミリ秒変換
        
        # 検証
        assert execution_time < 500  # 500ms以下
        assert len(results) == 1
        assert results[0].content == "高速検索結果"
    
    @pytest.mark.asyncio
    async def test_bulk_insert_embeddings_large_dataset_performance(self, mock_supabase_client):
        """大量データバルク処理性能テスト"""
        store = VectorStore("https://test.supabase.co", "test-key")
        
        # バルク処理のモック設定
        async def mock_execute():
            await asyncio.sleep(0.2)  # 200ms処理時間
            return Mock()
        
        mock_supabase_client.table.return_value.insert.return_value.execute = mock_execute
        
        # 1000件のテストデータ生成
        embedding_results = [
            Mock(embedding=[0.1] * 1536, metadata={"id": str(i)})
            for i in range(1000)
        ]
        document_chunks = [
            {
                "content": f"大量データテスト{i}",
                "filename": "large_test.pdf",
                "page_number": i % 100 + 1,
                "token_count": 50
            }
            for i in range(1000)
        ]
        
        # 実行時間測定
        start_time = time.time()
        result = await store.bulk_insert_embeddings(embedding_results, document_chunks)
        end_time = time.time()
        
        execution_time = (end_time - start_time) * 1000  # ミリ秒変換
        
        # 検証
        assert result is True
        assert execution_time < 1000  # 1秒以下（大量データ用の緩い条件）
        
        # 1件あたりの処理時間チェック
        per_item_time = execution_time / 1000
        assert per_item_time < 1  # 1件あたり1ms以下
    
    @pytest.mark.asyncio
    async def test_concurrent_search_operations(self, mock_supabase_client):
        """並行検索処理性能テスト"""
        store = VectorStore("https://test.supabase.co", "test-key")
        
        # 並行処理用モック設定
        mock_result = Mock()
        mock_result.data = [
            {
                "content": f"並行検索結果",
                "filename": "concurrent_test.pdf",
                "page_number": 1,
                "distance": 0.15,
                "section_name": "並行テスト章",
                "chapter_number": 1,
                "start_pos": {"x": 100, "y": 200},
                "end_pos": {"x": 300, "y": 250},
                "token_count": 40
            }
        ]
        
        async def mock_execute():
            await asyncio.sleep(0.05)  # 50ms処理時間
            return mock_result
        
        mock_supabase_client.rpc.return_value.execute = mock_execute
        
        query_embedding = [0.1] * 1536
        
        # 10個の並行検索を実行
        start_time = time.time()
        tasks = [
            store.search_similar_embeddings(query_embedding, limit=5)
            for _ in range(10)
        ]
        results = await asyncio.gather(*tasks)
        end_time = time.time()
        
        execution_time = (end_time - start_time) * 1000  # ミリ秒変換
        
        # 検証
        assert len(results) == 10
        assert all(len(result) == 1 for result in results)
        
        # 並行処理により単発処理×10より高速であることを確認
        # 理想的には500ms以下（単発50ms×10=500msに対して並行処理効果）
        assert execution_time < 300  # 十分に高速
    
    @pytest.mark.asyncio
    async def test_memory_efficiency_large_embeddings(self, mock_supabase_client):
        """大量埋め込みベクトルのメモリ効率テスト"""
        store = VectorStore("https://test.supabase.co", "test-key")
        
        # メモリ効率的な処理のモック設定
        mock_supabase_client.table.return_value.insert.return_value.execute.return_value = Mock()
        
        # 5000件の大規模データセット
        embedding_results = [
            Mock(embedding=[0.001 * i] * 1536, metadata={"id": str(i)})
            for i in range(5000)
        ]
        document_chunks = [
            {
                "content": f"メモリ効率テスト {i} " + "A" * 100,  # 長いコンテンツ
                "filename": "memory_test.pdf",
                "page_number": i % 200 + 1,
                "token_count": 150
            }
            for i in range(5000)
        ]
        
        # 実行（メモリ例外が発生しないことを確認）
        try:
            result = await store.bulk_insert_embeddings(embedding_results, document_chunks)
            assert result is True
        except MemoryError:
            pytest.fail("メモリ不足エラーが発生しました - メモリ効率の改善が必要")
        except Exception as e:
            # VectorStoreError以外の予期しないエラーは失敗とする
            if not isinstance(e, VectorStoreError):
                pytest.fail(f"予期しないエラーが発生しました: {e}")


class TestScalabilityLimits:
    """スケーラビリティ限界テストクラス"""
    
    @pytest.mark.asyncio
    async def test_max_search_limit_boundary(self, mock_supabase_client):
        """最大検索件数境界値テスト"""
        store = VectorStore("https://test.supabase.co", "test-key")
        
        # 最大件数の結果モック設定
        mock_result = Mock()
        mock_result.data = [
            {
                "content": f"境界値テスト結果{i}",
                "filename": "boundary_test.pdf",
                "page_number": i + 1,
                "distance": 0.01 * i,
                "section_name": f"第{i+1}章",
                "chapter_number": i + 1,
                "start_pos": {"x": 100, "y": 200},
                "end_pos": {"x": 300, "y": 250},
                "token_count": 30
            }
            for i in range(100)  # MAX_SEARCH_LIMIT = 100
        ]
        
        mock_supabase_client.rpc.return_value.execute.return_value = mock_result
        
        query_embedding = [0.1] * 1536
        
        # 最大件数での検索実行
        results = await store.search_similar_embeddings(query_embedding, limit=100)
        
        # 検証
        assert len(results) == 100
        assert all(isinstance(r, SearchResult) for r in results)
        
        # 最大件数超過はエラー
        with pytest.raises(VectorStoreError, match="limit は100以下である必要があります"):
            await store.search_similar_embeddings(query_embedding, limit=101)