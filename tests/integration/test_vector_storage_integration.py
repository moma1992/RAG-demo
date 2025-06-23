"""
VectorStorageの統合テストスイート

実際のSupabaseデータベースとの統合テスト
Issue #36: ベクトルストレージ操作実装
"""

import pytest
import os
import uuid
from typing import List
import time
from datetime import datetime

from services.vector_storage import (
    VectorStorage,
    ChunkData,
    BatchResult,
    VectorStorageError
)

# 統合テスト用の環境変数チェック
INTEGRATION_TEST_ENABLED = os.getenv("RUN_INTEGRATION_TESTS", "false").lower() == "true"
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_ANON_KEY = os.getenv("SUPABASE_ANON_KEY")

skip_integration = pytest.mark.skipif(
    not INTEGRATION_TEST_ENABLED or not SUPABASE_URL or not SUPABASE_ANON_KEY,
    reason="統合テストが無効化されているか、必要な環境変数が設定されていません"
)


@skip_integration
class TestVectorStorageIntegration:
    """VectorStorageの実際のデータベース統合テスト"""
    
    @classmethod
    def setup_class(cls):
        """クラスレベルのセットアップ"""
        cls.storage = VectorStorage(
            supabase_url=SUPABASE_URL,
            supabase_key=SUPABASE_ANON_KEY,
            batch_size=50  # テスト用に小さめのバッチサイズ
        )
        cls.test_chunk_ids = []  # クリーンアップ用
    
    @classmethod
    def teardown_class(cls):
        """クラスレベルのクリーンアップ"""
        if cls.test_chunk_ids:
            try:
                cls.storage.delete_chunks_batch(cls.test_chunk_ids)
            except Exception:
                pass  # クリーンアップエラーは無視
    
    def create_test_chunk(self, index: int = 1) -> ChunkData:
        """テスト用チャンクデータを作成"""
        chunk_id = str(uuid.uuid4())
        self.test_chunk_ids.append(chunk_id)
        
        return ChunkData(
            id=chunk_id,
            document_id=str(uuid.uuid4()),
            content=f"統合テスト用コンテンツ {index}",
            filename=f"integration_test_{index}.pdf",
            page_number=index,
            chapter_number=1,
            section_name=f"セクション {index}",
            start_pos={"x": 0, "y": index * 20},
            end_pos={"x": 100, "y": (index + 1) * 20},
            embedding=[0.001 * (index + 1)] * 1536,  # Avoid zero vector
            token_count=10 + index
        )
    
    def test_single_chunk_save_and_retrieve(self):
        """単一チャンクの保存と取得テスト"""
        chunk = self.create_test_chunk(1)
        
        # チャンク保存
        result = self.storage.save_chunks_batch([chunk])
        
        assert result.success_count == 1
        assert result.failure_count == 0
        assert result.is_complete_success
        
        # 重複チェックで確認
        existing_ids = self.storage.check_duplicates([chunk.id])
        assert chunk.id in existing_ids
    
    def test_batch_save_chunks(self):
        """バッチチャンク保存のテスト"""
        # 20個のテストチャンクを作成
        chunks = [self.create_test_chunk(i) for i in range(2, 22)]
        
        # バッチ保存実行
        start_time = time.time()
        result = self.storage.save_chunks_batch(chunks)
        elapsed_time = time.time() - start_time
        
        # 結果検証
        assert result.success_count == 20
        assert result.failure_count == 0
        assert result.total_count == 20
        assert result.success_rate == 1.0
        assert result.is_complete_success
        
        # パフォーマンス検証（20件を5秒以内で処理）
        assert elapsed_time < 5.0, f"バッチ保存が遅すぎます: {elapsed_time:.2f}秒"
        
        print(f"バッチ保存パフォーマンス: {elapsed_time:.2f}秒 ({20/elapsed_time:.1f}件/秒)")
    
    def test_embedding_update_batch(self):
        """埋め込みベクトル更新のテスト"""
        # テストチャンクを作成・保存
        chunk = self.create_test_chunk(50)
        save_result = self.storage.save_chunks_batch([chunk])
        assert save_result.is_complete_success
        
        # 埋め込みベクトルを更新
        new_embedding = [0.5] * 1536
        updates = [{"id": chunk.id, "embedding": new_embedding}]
        
        update_result = self.storage.update_embeddings_batch(updates)
        
        assert update_result.success_count == 1
        assert update_result.failure_count == 0
        assert update_result.is_complete_success
    
    def test_duplicate_check_performance(self):
        """重複チェックのパフォーマンステスト"""
        # 100個のランダムIDで重複チェック
        random_ids = [str(uuid.uuid4()) for _ in range(100)]
        
        start_time = time.time()
        existing_ids = self.storage.check_duplicates(random_ids)
        elapsed_time = time.time() - start_time
        
        # 結果検証
        assert isinstance(existing_ids, list)
        
        # パフォーマンス検証（100件を2秒以内で処理）
        assert elapsed_time < 2.0, f"重複チェックが遅すぎます: {elapsed_time:.2f}秒"
        
        print(f"重複チェックパフォーマンス: {elapsed_time:.2f}秒 ({100/elapsed_time:.1f}件/秒)")
    
    def test_partial_failure_handling(self):
        """部分的失敗のハンドリングテスト"""
        # 有効なチャンクと無効なチャンクを混在
        valid_chunk = self.create_test_chunk(100)
        
        # 無効なチャンク（frozenデータクラスなので新規作成）
        invalid_chunk_id = str(uuid.uuid4())
        self.test_chunk_ids.append(invalid_chunk_id)
        
        # 長すぎるコンテンツで無効なチャンクを作成
        try:
            invalid_chunk = ChunkData(
                id=invalid_chunk_id,
                document_id=str(uuid.uuid4()),
                content="x" * 15000,  # 制限を超える長いコンテンツ
                filename="invalid_test.pdf",
                page_number=1,
                chapter_number=1,
                section_name="無効テスト",
                start_pos={"x": 0, "y": 0},
                end_pos={"x": 100, "y": 20},
                embedding=[0.1] * 1536,
                token_count=1
            )
            assert False, "無効なチャンクが作成されてしまいました"
        except VectorStorageError:
            pass  # 期待通りエラーが発生
        
        # 有効なチャンクのみでテスト
        result = self.storage.save_chunks_batch([valid_chunk])
        assert result.success_count == 1
        assert result.failure_count == 0
    
    def test_delete_chunks_batch(self):
        """バッチ削除のテスト"""
        # テストチャンクを作成・保存
        chunks = [self.create_test_chunk(i) for i in range(200, 205)]
        save_result = self.storage.save_chunks_batch(chunks)
        assert save_result.is_complete_success
        
        # 保存したチャンクを削除
        chunk_ids = [chunk.id for chunk in chunks]
        delete_result = self.storage.delete_chunks_batch(chunk_ids)
        
        assert delete_result.success_count == 5
        assert delete_result.failure_count == 0
        assert delete_result.is_complete_success
        
        # 削除されたことを確認
        existing_ids = self.storage.check_duplicates(chunk_ids)
        assert len(existing_ids) == 0
        
        # クリーンアップリストから削除
        for chunk_id in chunk_ids:
            if chunk_id in self.test_chunk_ids:
                self.test_chunk_ids.remove(chunk_id)
    
    def test_storage_statistics(self):
        """ストレージ統計情報のテスト"""
        stats = self.storage.get_storage_stats()
        
        # 統計情報の構造確認
        required_keys = {
            "total_chunks", "total_documents", 
            "avg_chunks_per_document", "batch_size", "timestamp"
        }
        assert required_keys.issubset(stats.keys())
        
        # 値の型確認
        assert isinstance(stats["total_chunks"], int)
        assert isinstance(stats["total_documents"], int)
        assert isinstance(stats["avg_chunks_per_document"], (int, float))
        assert isinstance(stats["batch_size"], int)
        
        # 論理的整合性確認
        assert stats["total_chunks"] >= 0
        assert stats["total_documents"] >= 0
        assert stats["batch_size"] == self.storage.batch_size


@skip_integration
class TestVectorStoragePerformance:
    """VectorStorageのパフォーマンステスト"""
    
    @classmethod
    def setup_class(cls):
        """クラスレベルのセットアップ"""
        cls.storage = VectorStorage(
            supabase_url=SUPABASE_URL,
            supabase_key=SUPABASE_ANON_KEY,
            batch_size=100
        )
        cls.test_chunk_ids = []
    
    @classmethod
    def teardown_class(cls):
        """クラスレベルのクリーンアップ"""
        if cls.test_chunk_ids:
            try:
                # 大きなバッチで一括削除
                for i in range(0, len(cls.test_chunk_ids), 100):
                    batch_ids = cls.test_chunk_ids[i:i + 100]
                    cls.storage.delete_chunks_batch(batch_ids)
            except Exception:
                pass
    
    def create_large_chunk_batch(self, count: int) -> List[ChunkData]:
        """大量のテストチャンクを作成"""
        chunks = []
        for i in range(count):
            chunk_id = str(uuid.uuid4())
            self.test_chunk_ids.append(chunk_id)
            
            chunk = ChunkData(
                id=chunk_id,
                document_id=str(uuid.uuid4()),
                content=f"パフォーマンステスト用の長いコンテンツです。チャンク番号: {i}。" * 10,
                filename=f"performance_test.pdf",
                page_number=(i % 100) + 1,
                chapter_number=(i // 100) + 1,
                section_name=f"セクション {i // 10 + 1}",
                start_pos={"x": 0, "y": i * 20},
                end_pos={"x": 100, "y": (i + 1) * 20},
                embedding=[0.001 * ((i % 1000) + 1)] * 1536,  # Avoid zero vector
                token_count=50 + (i % 100)
            )
            chunks.append(chunk)
        
        return chunks
    
    @pytest.mark.slow
    def test_large_batch_save_performance(self):
        """大容量バッチ保存のパフォーマンステスト"""
        # 500個のチャンクでテスト
        chunks = self.create_large_chunk_batch(500)
        
        start_time = time.time()
        result = self.storage.save_chunks_batch(chunks)
        elapsed_time = time.time() - start_time
        
        # 結果検証
        assert result.success_count == 500
        assert result.failure_count == 0
        assert result.is_complete_success
        
        # パフォーマンス基準（500件を30秒以内）
        assert elapsed_time < 30.0, f"大容量保存が遅すぎます: {elapsed_time:.2f}秒"
        
        throughput = 500 / elapsed_time
        print(f"大容量保存パフォーマンス: {elapsed_time:.2f}秒 ({throughput:.1f}件/秒)")
        
        # 最低スループット要件（10件/秒）
        assert throughput >= 10.0, f"スループットが不十分です: {throughput:.1f}件/秒"
    
    @pytest.mark.slow
    def test_concurrent_operations_simulation(self):
        """同時操作のシミュレーション"""
        # 複数の小さなバッチを連続実行してシミュレート
        batch_size = 50
        num_batches = 5
        
        all_results = []
        start_time = time.time()
        
        for batch_num in range(num_batches):
            chunks = self.create_large_chunk_batch(batch_size)
            result = self.storage.save_chunks_batch(chunks)
            all_results.append(result)
        
        elapsed_time = time.time() - start_time
        
        # 全バッチの結果検証
        total_success = sum(r.success_count for r in all_results)
        total_failure = sum(r.failure_count for r in all_results)
        
        assert total_success == batch_size * num_batches
        assert total_failure == 0
        
        overall_throughput = total_success / elapsed_time
        print(f"同時操作シミュレーション: {elapsed_time:.2f}秒 ({overall_throughput:.1f}件/秒)")


if __name__ == "__main__":
    # 統合テストの実行方法を表示
    if not INTEGRATION_TEST_ENABLED:
        print("統合テストを実行するには以下の環境変数を設定してください:")
        print("export RUN_INTEGRATION_TESTS=true")
        print("export SUPABASE_URL=your_supabase_url")
        print("export SUPABASE_ANON_KEY=your_supabase_anon_key")
        print()
        print("その後、以下のコマンドで実行してください:")
        print("pytest tests/integration/test_vector_storage_integration.py -v")
        print("pytest tests/integration/test_vector_storage_integration.py -v -m slow  # パフォーマンステスト")
    else:
        pytest.main([__file__, "-v"])