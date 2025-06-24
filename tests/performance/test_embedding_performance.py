"""
Embedding Data Model パフォーマンステスト

Issue #53: Embedding Data Model のパフォーマンス要件検証
"""

import pytest
import time
import statistics
from typing import List, Dict, Any
from unittest.mock import Mock, patch

from models.embedding import (
    EmbeddingResult,
    EmbeddingBatch,
    EmbeddingCostCalculator,
    OPENAI_EMBEDDING_DIMENSION
)
from utils.tokenizer import TokenCounter


class TestEmbeddingResultPerformance:
    """EmbeddingResult パフォーマンステスト"""
    
    def test_embedding_result_creation_performance(self):
        """EmbeddingResult 作成性能テスト"""
        # 大量のEmbeddingResultを作成して時間測定
        creation_times = []
        
        for i in range(100):
            text = f"テストテキスト{i}" * 10  # 長めのテキスト
            embedding = [0.1 + i * 0.0001] * OPENAI_EMBEDDING_DIMENSION
            
            start_time = time.time()
            result = EmbeddingResult(
                text=text,
                embedding=embedding,
                token_count=50 + i,
                model="text-embedding-3-small"
            )
            creation_time = time.time() - start_time
            creation_times.append(creation_time)
            
            # オブジェクトが正常に作成されていることを確認
            assert result.text == text
            assert len(result.embedding) == OPENAI_EMBEDDING_DIMENSION
        
        # パフォーマンス要件
        avg_creation_time = statistics.mean(creation_times)
        max_creation_time = max(creation_times)
        
        assert avg_creation_time < 0.01  # 平均10ms以内
        assert max_creation_time < 0.1   # 最大100ms以内
    
    def test_embedding_validation_performance(self):
        """埋め込み検証性能テスト"""
        # 異なるサイズの埋め込みで検証時間測定
        validation_times = []
        
        text = "テスト用テキストデータ"
        embedding = [0.1] * OPENAI_EMBEDDING_DIMENSION
        
        for i in range(50):
            start_time = time.time()
            result = EmbeddingResult(
                text=text,
                embedding=embedding,
                token_count=20,
                model="text-embedding-3-small"
            )
            result.validate()  # 明示的な検証呼び出し
            validation_time = time.time() - start_time
            validation_times.append(validation_time)
        
        # パフォーマンス要件
        avg_validation_time = statistics.mean(validation_times)
        assert avg_validation_time < 0.005  # 平均5ms以内
    
    def test_supabase_format_conversion_performance(self):
        """Supabase形式変換性能テスト"""
        # 大量変換のパフォーマンステスト
        results = []
        
        # テストデータ準備
        for i in range(100):
            result = EmbeddingResult(
                text=f"変換テストテキスト{i}",
                embedding=[0.1 + i * 0.0001] * OPENAI_EMBEDDING_DIMENSION,
                token_count=30 + i,
                model="text-embedding-3-small"
            )
            results.append(result)
        
        # 変換時間測定
        start_time = time.time()
        supabase_data = [result.to_supabase_format() for result in results]
        conversion_time = time.time() - start_time
        
        # パフォーマンス要件
        assert conversion_time < 1.0  # 1秒以内
        assert len(supabase_data) == 100
        
        # 変換結果の正当性確認
        for i, data in enumerate(supabase_data):
            assert "text" in data
            assert "embedding" in data
            assert "token_count" in data
            assert len(data["embedding"]) == OPENAI_EMBEDDING_DIMENSION
    
    def test_cost_calculation_performance(self):
        """コスト計算性能テスト"""
        # 大量のコスト計算性能テスト
        results = []
        
        for i in range(1000):
            result = EmbeddingResult(
                text=f"コスト計算テストテキスト{i}",
                embedding=[0.1] * OPENAI_EMBEDDING_DIMENSION,
                token_count=100 + i,
                model="text-embedding-3-small"
            )
            results.append(result)
        
        # コスト計算時間測定
        start_time = time.time()
        costs = [result.calculate_cost() for result in results]
        calculation_time = time.time() - start_time
        
        # パフォーマンス要件
        assert calculation_time < 0.1  # 100ms以内
        assert len(costs) == 1000
        assert all(cost > 0 for cost in costs)


class TestEmbeddingBatchPerformance:
    """EmbeddingBatch パフォーマンステスト"""
    
    def test_batch_creation_performance(self):
        """バッチ作成性能テスト"""
        # 大きなバッチ作成の性能測定
        batch_sizes = [100, 500, 1000]
        
        for batch_size in batch_sizes:
            # テストデータ準備
            results = []
            for i in range(batch_size):
                result = EmbeddingResult(
                    text=f"バッチテストテキスト{i}",
                    embedding=[0.1 + i * 0.0001] * OPENAI_EMBEDDING_DIMENSION,
                    token_count=50 + i,
                    model="text-embedding-3-small"
                )
                results.append(result)
            
            # バッチ作成時間測定
            start_time = time.time()
            batch = EmbeddingBatch(results)
            creation_time = time.time() - start_time
            
            # パフォーマンス要件（バッチサイズに応じて調整）
            expected_max_time = batch_size * 0.001  # 1ms per item
            assert creation_time < expected_max_time
            assert len(batch.results) == batch_size
            assert batch.total_tokens > 0
    
    def test_batch_statistics_performance(self):
        """バッチ統計計算性能テスト"""
        # 大きなバッチの統計計算性能測定
        results = []
        for i in range(500):
            result = EmbeddingResult(
                text=f"統計テストテキスト{i}",
                embedding=[0.1] * OPENAI_EMBEDDING_DIMENSION,
                token_count=80 + i % 50,  # トークン数にバリエーション
                model="text-embedding-3-small"
            )
            results.append(result)
        
        batch = EmbeddingBatch(results)
        
        # 統計計算時間測定
        start_time = time.time()
        stats = batch.get_statistics()
        calculation_time = time.time() - start_time
        
        # パフォーマンス要件
        assert calculation_time < 0.1  # 100ms以内
        assert stats["count"] == 500
        assert stats["total_tokens"] > 0
        assert stats["avg_tokens"] > 0
    
    def test_supabase_bulk_format_performance(self):
        """Supabaseバルク形式変換性能テスト"""
        # 大量データのバルク変換性能測定
        results = []
        for i in range(200):
            result = EmbeddingResult(
                text=f"バルク変換テストテキスト{i}",
                embedding=[0.1] * OPENAI_EMBEDDING_DIMENSION,
                token_count=60 + i,
                model="text-embedding-3-small"
            )
            results.append(result)
        
        batch = EmbeddingBatch(results)
        
        # バルク変換時間測定
        start_time = time.time()
        bulk_data = batch.to_supabase_bulk_format()
        conversion_time = time.time() - start_time
        
        # パフォーマンス要件
        assert conversion_time < 0.5  # 500ms以内
        assert len(bulk_data) == 200
        assert all("embedding" in item for item in bulk_data)
    
    def test_model_breakdown_performance(self):
        """モデル別内訳計算性能テスト"""
        # 複数モデル混在でのパフォーマンステスト
        results = []
        models = ["text-embedding-3-small", "text-embedding-3-large"]
        
        for i in range(300):
            model = models[i % 2]
            dimension = 1536 if model == "text-embedding-3-small" else 3072
            result = EmbeddingResult(
                text=f"モデル別テストテキスト{i}",
                embedding=[0.1] * dimension,
                token_count=70 + i,
                model=model
            )
            results.append(result)
        
        batch = EmbeddingBatch(results)
        
        # 内訳計算時間測定
        start_time = time.time()
        breakdown = batch.get_model_breakdown()
        calculation_time = time.time() - start_time
        
        # パフォーマンス要件
        assert calculation_time < 0.2  # 200ms以内
        assert len(breakdown) == 2  # 2つのモデル
        assert "text-embedding-3-small" in breakdown
        assert "text-embedding-3-large" in breakdown


class TestTokenCounterPerformance:
    """TokenCounter パフォーマンステスト"""
    
    def test_token_counting_performance(self):
        """トークンカウント性能テスト"""
        counter = TokenCounter("text-embedding-3-small")
        
        # 異なる長さのテキストでパフォーマンステスト
        test_texts = [
            "短いテキスト",
            "中程度の長さのテキストです。" * 10,
            "長いテキストのパフォーマンステストです。" * 100,
            "非常に長いテキストでのトークンカウント性能を測定します。" * 500
        ]
        
        counting_times = []
        
        for text in test_texts:
            start_time = time.time()
            token_count = counter.count_tokens(text)
            counting_time = time.time() - start_time
            counting_times.append(counting_time)
            
            assert token_count > 0
            assert isinstance(token_count, int)
        
        # パフォーマンス要件
        assert all(t < 0.1 for t in counting_times)  # 各計算100ms以内
    
    def test_batch_token_counting_performance(self):
        """バッチトークンカウント性能テスト"""
        counter = TokenCounter("text-embedding-3-small")
        
        # 大量テキストのバッチカウント
        texts = [f"バッチテストテキスト{i}です。" for i in range(100)]
        
        start_time = time.time()
        token_counts = counter.count_tokens_batch(texts)
        batch_time = time.time() - start_time
        
        # パフォーマンス要件
        assert batch_time < 1.0  # 1秒以内
        assert len(token_counts) == 100
        assert all(count > 0 for count in token_counts)


class TestEmbeddingCostCalculatorPerformance:
    """EmbeddingCostCalculator パフォーマンステスト"""
    
    def test_cost_calculation_performance(self):
        """コスト計算性能テスト"""
        calculator = EmbeddingCostCalculator()
        
        # 大量のコスト計算
        calculations = []
        for i in range(1000):
            token_count = 100 + i
            model = "text-embedding-3-small"
            
            start_time = time.time()
            cost = calculator.calculate_cost(token_count, model)
            calc_time = time.time() - start_time
            calculations.append(calc_time)
            
            assert cost > 0
            assert isinstance(cost, float)
        
        # パフォーマンス要件
        avg_calc_time = statistics.mean(calculations)
        assert avg_calc_time < 0.001  # 平均1ms以内
    
    def test_batch_cost_calculation_performance(self):
        """バッチコスト計算性能テスト"""
        calculator = EmbeddingCostCalculator()
        
        # 大きなバッチのコスト計算
        batch_items = []
        for i in range(500):
            batch_items.append({
                "tokens": 100 + i,
                "model": "text-embedding-3-small"
            })
        
        start_time = time.time()
        total_cost = calculator.calculate_batch_cost(batch_items)
        calc_time = time.time() - start_time
        
        # パフォーマンス要件
        assert calc_time < 0.5  # 500ms以内
        assert total_cost > 0
        assert isinstance(total_cost, float)
    
    def test_estimate_batch_cost_performance(self):
        """バッチコスト推定性能テスト"""
        calculator = EmbeddingCostCalculator()
        
        # 大量テキストのコスト推定
        texts = [f"コスト推定テストテキスト{i}です。" * 5 for i in range(100)]
        
        start_time = time.time()
        cost_estimate = calculator.estimate_batch_cost(texts, "text-embedding-3-small")
        estimation_time = time.time() - start_time
        
        # パフォーマンス要件
        assert estimation_time < 2.0  # 2秒以内（トークンカウント含む）
        assert cost_estimate["texts_count"] == 100
        assert cost_estimate["estimated_cost_usd"] > 0
        assert len(cost_estimate["token_breakdown"]) == 100


class TestMemoryEfficiency:
    """メモリ効率性テスト"""
    
    def test_large_batch_memory_efficiency(self):
        """大きなバッチのメモリ効率テスト"""
        # Streamlit Cloud制約: 1GB メモリ
        # 大きなバッチでもメモリ効率的に動作するかテスト
        
        batch_sizes = [1000, 2000, 5000]
        
        for batch_size in batch_sizes:
            try:
                results = []
                for i in range(batch_size):
                    result = EmbeddingResult(
                        text=f"メモリテストテキスト{i}",
                        embedding=[0.1] * OPENAI_EMBEDDING_DIMENSION,
                        token_count=50,
                        model="text-embedding-3-small"
                    )
                    results.append(result)
                
                # バッチ処理
                batch = EmbeddingBatch(results)
                stats = batch.get_statistics()
                bulk_data = batch.to_supabase_bulk_format()
                
                # メモリエラーが発生しないことを確認
                assert stats["count"] == batch_size
                assert len(bulk_data) == batch_size
                
            except MemoryError:
                pytest.fail(f"バッチサイズ {batch_size} でメモリ不足エラーが発生")
    
    def test_embedding_vector_memory_efficiency(self):
        """埋め込みベクトルメモリ効率テスト"""
        # 大きな埋め込みベクトルでのメモリ使用量テスト
        
        try:
            large_embeddings = []
            for i in range(100):
                # text-embedding-3-large (3072次元) をシミュレート
                embedding = [0.1 + i * 0.0001] * 3072
                result = EmbeddingResult(
                    text=f"大きな埋め込みテストテキスト{i}",
                    embedding=embedding,
                    token_count=100,
                    model="text-embedding-3-large"
                )
                large_embeddings.append(result)
            
            # バッチ処理でもメモリ効率的に動作
            batch = EmbeddingBatch(large_embeddings)
            assert batch.total_tokens > 0
            
        except MemoryError:
            pytest.fail("大きな埋め込みベクトルでメモリ不足エラーが発生")


# パフォーマンステスト用のマーカー
pytestmark = pytest.mark.performance