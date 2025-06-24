"""
Batch Embedding Processor Unit Tests
Issue #55: 大量テキストチャンクの効率的バッチ埋め込み処理実装

TDD Red Phase: 失敗テストケース作成
"""

import pytest
import asyncio
import time
from unittest.mock import Mock, patch, AsyncMock, MagicMock
from typing import List, Dict, Any, Callable
import psutil
import os

from utils.batch_processor import (
    BatchEmbeddingProcessor,
    BatchProcessingResult,
    BatchProcessingError,
    ProgressCallback,
    RateLimitConfig
)


class TestBatchEmbeddingProcessor:
    """BatchEmbeddingProcessor メインテストクラス"""
    
    @pytest.fixture
    def rate_limit_config(self):
        """レート制限設定フィクスチャ"""
        return RateLimitConfig(
            requests_per_minute=60,
            tokens_per_minute=1000000,
            max_concurrent_requests=10,
            retry_delays=[1, 2, 4, 8, 16]  # 指数バックオフ
        )
    
    @pytest.fixture
    def processor(self, rate_limit_config):
        """BatchEmbeddingProcessor インスタンス"""
        with patch('services.embeddings.EmbeddingService'):
            return BatchEmbeddingProcessor(
                api_key="sk-test123456789",
                rate_limit_config=rate_limit_config
            )
    
    def test_init_with_valid_config(self, rate_limit_config):
        """正常: 有効な設定での初期化"""
        with patch('services.embeddings.EmbeddingService'):
            processor = BatchEmbeddingProcessor(
                api_key="sk-test123456789",
                rate_limit_config=rate_limit_config
            )
            assert processor.rate_limit_config == rate_limit_config
            assert processor.max_concurrent_requests == 10
    
    def test_init_requires_api_key(self, rate_limit_config):
        """異常: APIキー必須"""
        with pytest.raises(ValueError, match="APIキーが必要です"):
            BatchEmbeddingProcessor(
                api_key="",
                rate_limit_config=rate_limit_config
            )
    
    def test_init_with_invalid_config(self):
        """異常: 無効な設定での初期化失敗"""
        invalid_config = RateLimitConfig(
            requests_per_minute=0,  # 無効値
            tokens_per_minute=-1000,  # 無効値
            max_concurrent_requests=0,  # 無効値
            retry_delays=[]  # 空リスト
        )
        
        with pytest.raises(ValueError, match="無効なレート制限設定"):
            BatchEmbeddingProcessor(
                api_key="sk-test123456789",
                rate_limit_config=invalid_config
            )


class TestProgressTracking:
    """進捗追跡機能テスト"""
    
    @pytest.fixture
    def progress_callback(self):
        """進捗コールバック関数"""
        return Mock(spec=ProgressCallback)
    
    @pytest.fixture  
    def processor(self):
        """テスト用プロセッサー"""
        rate_config = RateLimitConfig(
            requests_per_minute=60,
            tokens_per_minute=1000000,
            max_concurrent_requests=10,
            retry_delays=[1, 2, 4]
        )
        with patch('services.embeddings.EmbeddingService'):
            return BatchEmbeddingProcessor(
                api_key="sk-test123456789",
                rate_limit_config=rate_config
            )
    
    @pytest.mark.asyncio
    async def test_progress_callback_called(self, processor, progress_callback):
        """正常: 進捗コールバック呼び出し"""
        texts = [f"Text {i}" for i in range(10)]
        
        with patch.object(processor, '_process_batch_with_retry', new_callable=AsyncMock) as mock_process:
            mock_process.return_value = ([Mock()] * 10, [])
            
            await processor.process_batch(
                texts=texts,
                progress_callback=progress_callback
            )
            
            # 進捗コールバックが適切に呼び出されたことを確認
            assert progress_callback.call_count >= 2  # 開始と完了
            
            # 最初の呼び出し確認（処理開始時）
            first_call = progress_callback.call_args_list[0][0][0]
            assert first_call.total_count == 10
            
            # 最後の呼び出し確認（完了時）
            last_call = progress_callback.call_args_list[-1][0][0]
            assert last_call.processed_count == 10
            assert last_call.total_count == 10
            assert last_call.success_count == 10
            assert last_call.failure_count == 0
    
    def test_estimate_processing_time_small_batch(self, processor):
        """正常: 小バッチ処理時間推定"""
        texts = [f"Short text {i}" for i in range(10)]
        estimated_time = processor.estimate_processing_time(texts)
        
        assert isinstance(estimated_time, float)
        assert estimated_time > 0
        assert estimated_time < 60  # 10テキストなら1分以内
    
    def test_estimate_processing_time_large_batch(self, processor):
        """正常: 大バッチ処理時間推定"""
        texts = [f"Text {i}" for i in range(100)]
        estimated_time = processor.estimate_processing_time(texts)
        
        assert isinstance(estimated_time, float)
        assert estimated_time > 0
        # 100テキストでレート制限考慮すると数分
        assert estimated_time < 600  # 10分以内
    
    def test_estimate_processing_time_empty_list(self, processor):
        """異常: 空リストでの時間推定"""
        with pytest.raises(ValueError, match="テキストリストが空です"):
            processor.estimate_processing_time([])


class TestBatchProcessing:
    """バッチ処理メイン機能テスト"""
    
    @pytest.fixture
    def processor(self):
        """テスト用プロセッサー"""
        rate_config = RateLimitConfig(
            requests_per_minute=60,
            tokens_per_minute=1000000,
            max_concurrent_requests=5,  # テスト用に制限
            retry_delays=[0.1, 0.2, 0.4]  # テスト用に短縮
        )
        with patch('services.embeddings.EmbeddingService'):
            return BatchEmbeddingProcessor(
                api_key="sk-test123456789",
                rate_limit_config=rate_config
            )
    
    @pytest.mark.asyncio
    async def test_process_small_batch_success(self, processor):
        """正常: 小バッチ(10件)正常処理"""
        texts = [f"Text chunk {i}" for i in range(10)]
        
        # モック設定
        with patch.object(processor, '_process_batch_with_retry', new_callable=AsyncMock) as mock_process:
            mock_results = [Mock(text=text, embedding=[0.1]*1536) for text in texts]
            mock_process.return_value = (mock_results, [])
            
            result = await processor.process_batch(texts)
            
            assert isinstance(result, BatchProcessingResult)
            assert result.total_processed == 10
            assert result.success_count == 10
            assert result.failure_count == 0
            assert len(result.results) == 10
            assert result.processing_time > 0
    
    @pytest.mark.asyncio
    async def test_process_large_batch_success(self, processor):
        """正常: 大バッチ(100件)正常処理"""
        texts = [f"Large batch text {i}" for i in range(100)]
        
        with patch.object(processor, '_process_batch_with_retry', new_callable=AsyncMock) as mock_process:
            # バッチごとにモック結果を返す
            def side_effect(batch_texts):
                return ([Mock(text=text, embedding=[0.1]*1536) for text in batch_texts], [])
            
            mock_process.side_effect = side_effect
            
            result = await processor.process_batch(texts)
            
            assert isinstance(result, BatchProcessingResult)
            assert result.total_processed == 100
            assert result.success_count == 100
            assert result.failure_count == 0
            assert len(result.results) == 100
            
            # 複数バッチに分割されて処理されることを確認
            assert mock_process.call_count >= 1
    
    @pytest.mark.asyncio
    async def test_process_batch_with_partial_failures(self, processor):
        """正常: 部分的失敗を含むバッチ処理"""
        texts = [f"Text {i}" for i in range(20)]
        
        with patch.object(processor, '_process_batch_with_retry', new_callable=AsyncMock) as mock_process:
            # 一部のバッチで失敗を模擬
            def side_effect(batch_texts):
                results = []
                failures = []
                for text in batch_texts:
                    if "5" in text:
                        failures.append(Mock(text=text, error_message="API Error", retry_count=3))
                    else:
                        results.append(Mock(text=text, embedding=[0.1]*1536))
                return (results, failures)
            
            mock_process.side_effect = side_effect
            
            result = await processor.process_batch(texts)
            
            assert isinstance(result, BatchProcessingResult)
            assert result.total_processed == 20
            assert result.success_count < 20  # 一部失敗
            assert result.failure_count > 0
            assert len(result.failed_items) > 0
    
    @pytest.mark.asyncio
    async def test_process_batch_empty_list(self, processor):
        """異常: 空リストでのバッチ処理"""
        with pytest.raises(ValueError, match="テキストリストが空です"):
            await processor.process_batch([])
    
    @pytest.mark.asyncio
    async def test_process_batch_exceeds_limit(self, processor):
        """異常: バッチサイズ制限超過"""
        # 制限を超える大量のテキスト (1001件)
        texts = [f"Text {i}" for i in range(1001)]
        
        with pytest.raises(ValueError, match="バッチサイズが制限を超えています"):
            await processor.process_batch(texts)


class TestRateLimitHandling:
    """レート制限処理テスト"""
    
    @pytest.fixture
    def strict_rate_config(self):
        """厳しいレート制限設定"""
        return RateLimitConfig(
            requests_per_minute=10,  # 非常に低い制限
            tokens_per_minute=10000,
            max_concurrent_requests=2,
            retry_delays=[0.1, 0.2, 0.4, 0.8]
        )
    
    @pytest.fixture
    def processor(self, strict_rate_config):
        """厳しいレート制限付きプロセッサー"""
        with patch('services.embeddings.EmbeddingService'):
            return BatchEmbeddingProcessor(
                api_key="sk-test123456789", 
                rate_limit_config=strict_rate_config
            )
    
    @pytest.mark.asyncio
    async def test_rate_limit_backoff_retry(self, processor):
        """正常: レート制限時の指数バックオフリトライ"""
        texts = [f"Rate limit test {i}" for i in range(5)]
        
        with patch.object(processor, '_process_single_text_with_retry', new_callable=AsyncMock) as mock_process:
            # 各テキストで最初の2回はエラー、3回目で成功
            call_counts = {}
            total_calls = 0
            async def side_effect(text):
                nonlocal total_calls
                total_calls += 1
                if text not in call_counts:
                    call_counts[text] = 0
                call_counts[text] += 1
                if call_counts[text] <= 2:  # 各テキストで2回失敗
                    raise Exception("RateLimitError: Too many requests")
                return Mock(text=text, embedding=[0.1]*1536)
            
            mock_process.side_effect = side_effect
            
            start_time = time.time()
            result = await processor.process_batch(texts)
            end_time = time.time()
            
            # リトライが発生したことを確認
            assert result.success_count == 5
            assert total_calls > 5  # リトライによる追加呼び出し
    
    @pytest.mark.asyncio 
    async def test_rate_limit_max_retries_exceeded(self, processor):
        """異常: 最大リトライ回数超過"""
        texts = [f"Max retry test {i}" for i in range(3)]
        
        with patch.object(processor, '_process_batch_with_retry', new_callable=AsyncMock) as mock_process:
            # 常にレート制限エラーを返す
            mock_process.side_effect = Exception("RateLimitError: Persistent error")
            
            with pytest.raises(BatchProcessingError, match="バッチ処理中にエラーが発生しました"):
                await processor.process_batch(texts)
    
    def test_calculate_delay_exponential_backoff(self, processor):
        """正常: 指数バックオフ遅延計算"""
        delays = [
            processor._calculate_retry_delay(0),
            processor._calculate_retry_delay(1), 
            processor._calculate_retry_delay(2),
            processor._calculate_retry_delay(3)
        ]
        
        # 指数的に増加することを確認
        assert delays[0] == 0.1
        assert delays[1] == 0.2
        assert delays[2] == 0.4
        assert delays[3] == 0.8
    
    @pytest.mark.asyncio
    async def test_concurrent_request_limiting(self, processor):
        """正常: 同時リクエスト数制限"""
        texts = [f"Concurrent test {i}" for i in range(20)]
        
        concurrent_count = 0
        max_concurrent = 0
        
        async def mock_process_with_tracking(batch_texts):
            nonlocal concurrent_count, max_concurrent
            concurrent_count += 1
            max_concurrent = max(max_concurrent, concurrent_count)
            
            await asyncio.sleep(0.1)  # 処理時間をシミュレート
            
            concurrent_count -= 1
            return ([Mock(text=text, embedding=[0.1]*1536) for text in batch_texts], [])
        
        with patch.object(processor, '_process_batch_with_retry', new_callable=AsyncMock) as mock_process:
            mock_process.side_effect = mock_process_with_tracking
            
            await processor.process_batch(texts)
            
            # 最大同時実行数が制限内であることを確認
            assert max_concurrent <= processor.rate_limit_config.max_concurrent_requests


class TestMemoryManagement:
    """メモリ管理テスト"""
    
    @pytest.fixture
    def processor(self):
        """メモリテスト用プロセッサー"""
        rate_config = RateLimitConfig(
            requests_per_minute=120,
            tokens_per_minute=2000000,
            max_concurrent_requests=10,
            retry_delays=[0.1, 0.2]
        )
        with patch('services.embeddings.EmbeddingService'):
            return BatchEmbeddingProcessor(
                api_key="sk-test123456789",
                rate_limit_config=rate_config
            )
    
    @pytest.mark.asyncio
    async def test_memory_usage_under_500mb(self, processor):
        """要件: メモリ使用量500MB以下"""
        # 大量のテキストでメモリ使用量をテスト
        texts = [f"Memory test with longer text content {i} " * 100 for i in range(100)]
        
        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB
        
        with patch.object(processor, '_process_batch_with_retry', new_callable=AsyncMock) as mock_process:
            mock_process.return_value = ([Mock(text=text, embedding=[0.1]*1536) for text in texts[:10]], [])
            
            await processor.process_batch(texts)
            
            final_memory = process.memory_info().rss / 1024 / 1024  # MB
            memory_increase = final_memory - initial_memory
            
            # Issue要件: 500MB以下
            assert memory_increase < 500
    
    @pytest.mark.asyncio
    async def test_memory_cleanup_after_processing(self, processor):
        """正常: 処理後のメモリクリーンアップ"""
        texts = [f"Cleanup test {i}" for i in range(50)]
        
        process = psutil.Process(os.getpid())
        before_memory = process.memory_info().rss
        
        with patch.object(processor, '_process_batch_with_retry', new_callable=AsyncMock) as mock_process:
            mock_process.return_value = ([Mock(text=text, embedding=[0.1]*1536) for text in texts], [])
            
            result = await processor.process_batch(texts)
            
            # 処理結果を削除してガベージコレクション
            del result
            import gc
            gc.collect()
            
            after_memory = process.memory_info().rss
            memory_diff = (after_memory - before_memory) / 1024 / 1024  # MB
            
            # メモリリークがないことを確認（差分が小さい）
            assert memory_diff < 50  # 50MB以下の増加


class TestSuccessRateRequirements:
    """成功率要件テスト"""
    
    @pytest.fixture
    def processor(self):
        """成功率テスト用プロセッサー"""
        rate_config = RateLimitConfig(
            requests_per_minute=60,
            tokens_per_minute=1000000,
            max_concurrent_requests=10,
            retry_delays=[0.1, 0.2, 0.4]
        )
        with patch('services.embeddings.EmbeddingService'):
            return BatchEmbeddingProcessor(
                api_key="sk-test123456789",
                rate_limit_config=rate_config
            )
    
    @pytest.mark.asyncio
    async def test_success_rate_over_90_percent(self, processor):
        """要件: 90%以上の成功率"""
        texts = [f"Success rate test {i}" for i in range(100)]
        
        with patch.object(processor, '_process_batch_with_retry', new_callable=AsyncMock) as mock_process:
            # 10%の失敗率をシミュレート
            def side_effect(batch_texts):
                results = []
                failures = []
                for i, text in enumerate(batch_texts):
                    if i % 10 == 0:  # 10件に1件失敗
                        failures.append(Mock(text=text, error_message=f"Simulated failure for {text}", retry_count=3))
                    else:
                        results.append(Mock(text=text, embedding=[0.1]*1536))
                return (results, failures)
            
            mock_process.side_effect = side_effect
            
            result = await processor.process_batch(texts)
            
            success_rate = result.success_count / result.total_processed
            
            # Issue要件: 90%以上の成功率
            assert success_rate >= 0.9
            assert result.success_count >= 90
    
    @pytest.mark.asyncio
    async def test_failed_items_tracking(self, processor):
        """正常: 失敗アイテム追跡"""
        texts = [f"Failure tracking {i}" for i in range(20)]
        
        with patch.object(processor, '_process_batch_with_retry', new_callable=AsyncMock) as mock_process:
            def side_effect(batch_texts):
                results = []
                failures = []
                for text in batch_texts:
                    if "5" in text:
                        failures.append(Mock(text=text, error_message="Specific failure for items containing '5'", retry_count=3))
                    else:
                        results.append(Mock(text=text, embedding=[0.1]*1536))
                return (results, failures)
            
            mock_process.side_effect = side_effect
            
            result = await processor.process_batch(texts)
            
            # 失敗したアイテムが適切に記録されていることを確認
            assert len(result.failed_items) > 0
            assert all(item.error_message for item in result.failed_items)
            assert all(item.text for item in result.failed_items)


class TestAsyncProcessingPatterns:
    """非同期処理パターンテスト"""
    
    @pytest.fixture
    def processor(self):
        """非同期テスト用プロセッサー"""
        rate_config = RateLimitConfig(
            requests_per_minute=60,
            tokens_per_minute=1000000,
            max_concurrent_requests=5,
            retry_delays=[0.1, 0.2]
        )
        with patch('services.embeddings.EmbeddingService'):
            return BatchEmbeddingProcessor(
                api_key="sk-test123456789",
                rate_limit_config=rate_config
            )
    
    @pytest.mark.asyncio
    async def test_async_batch_processing_efficiency(self, processor):
        """正常: 非同期処理効率性"""
        texts = [f"Async efficiency test {i}" for i in range(25)]
        
        with patch.object(processor, '_process_batch_with_retry', new_callable=AsyncMock) as mock_process:
            async def mock_delay(batch_texts):
                await asyncio.sleep(0.1)  # 100ms の処理時間をシミュレート
                return ([Mock(text=text, embedding=[0.1]*1536) for text in batch_texts], [])
            
            mock_process.side_effect = mock_delay
            
            start_time = time.time()
            result = await processor.process_batch(texts)
            end_time = time.time()
            
            processing_time = end_time - start_time
            
            # 並列処理により、逐次処理より高速であることを確認
            sequential_time = len(texts) * 0.1  # 逐次処理想定時間
            parallel_time_expected = (len(texts) / processor.rate_limit_config.max_concurrent_requests) * 0.1
            
            assert processing_time < sequential_time
            assert processing_time >= parallel_time_expected * 0.8  # 80%の効率性
    
    @pytest.mark.asyncio
    async def test_cancellation_handling(self, processor):
        """正常: キャンセル処理対応"""
        texts = [f"Cancellation test {i}" for i in range(20)]
        
        with patch.object(processor, '_process_batch_with_retry', new_callable=AsyncMock) as mock_process:
            async def mock_long_process(batch_texts):
                await asyncio.sleep(1)  # 長い処理時間
                return ([Mock(text=text, embedding=[0.1]*1536) for text in batch_texts], [])
            
            mock_process.side_effect = mock_long_process
            
            # 処理をキャンセル
            task = asyncio.create_task(processor.process_batch(texts))
            await asyncio.sleep(0.1)  # 少し待ってからキャンセル
            task.cancel()
            
            with pytest.raises(asyncio.CancelledError):
                await task


# Integration Test Markers
pytestmark = [
    pytest.mark.unit,
    pytest.mark.batch_processing,
    pytest.mark.tdd_red_phase
]