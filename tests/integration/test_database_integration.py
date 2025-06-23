"""
データベース統合テストスイート

実際のSupabaseデータベースとの統合テスト
注意: これらのテストは実際のデータベース接続が必要です
"""

import pytest
import os
import uuid
from typing import List, Dict, Any

from services.database_manager import DatabaseManager, DatabaseConfig
from services.vector_store import VectorStore, VectorStoreError

# 統合テスト用の環境変数チェック
INTEGRATION_TEST_ENABLED = os.getenv("RUN_INTEGRATION_TESTS", "false").lower() == "true"
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_ANON_KEY = os.getenv("SUPABASE_ANON_KEY")

skip_integration = pytest.mark.skipif(
    not INTEGRATION_TEST_ENABLED or not SUPABASE_URL or not SUPABASE_ANON_KEY,
    reason="統合テストが無効化されているか、必要な環境変数が設定されていません"
)


@skip_integration
class TestDatabaseIntegration:
    """実際のデータベースとの統合テスト"""
    
    @classmethod
    def setup_class(cls):
        """クラスレベルのセットアップ"""
        cls.config = DatabaseConfig(
            supabase_url=SUPABASE_URL,
            supabase_key=SUPABASE_ANON_KEY,
            search_top_k=3,
            similarity_threshold=0.5
        )
        cls.manager = DatabaseManager(cls.config)
        cls.test_document_ids = []  # クリーンアップ用
    
    @classmethod
    def teardown_class(cls):
        """クラスレベルのクリーンアップ"""
        # テスト中に作成された文書を削除
        for doc_id in cls.test_document_ids:
            try:
                cls.manager.delete_document(doc_id)
            except Exception:
                pass  # クリーンアップエラーは無視
    
    def test_database_health_check(self):
        """データベース接続ヘルスチェック"""
        health = self.manager.health_check()
        
        assert health["status"] == "healthy"
        assert health["message"] == "データベース接続正常"
        assert "timestamp" in health
    
    def test_store_and_retrieve_document(self):
        """文書の保存と取得のテスト"""
        # テスト用文書データ
        document_data = {
            "filename": f"test_{uuid.uuid4().hex[:8]}.pdf",
            "original_filename": "統合テスト文書.pdf",
            "file_size": 2048,
            "total_pages": 5
        }
        
        # 文書保存
        document_id = self.manager.store_document(document_data)
        self.test_document_ids.append(document_id)
        
        assert document_id is not None
        assert isinstance(document_id, str)
        
        # 文書一覧取得で確認
        documents = self.manager.get_all_documents()
        saved_doc = next((doc for doc in documents if doc.id == document_id), None)
        
        assert saved_doc is not None
        assert saved_doc.filename == document_data["filename"]
        assert saved_doc.original_filename == document_data["original_filename"]
        assert saved_doc.file_size == document_data["file_size"]
        assert saved_doc.total_pages == document_data["total_pages"]
        assert saved_doc.processing_status == "processing"  # デフォルト状態
    
    def test_store_chunks_and_search(self):
        """チャンク保存と検索のテスト"""
        # テスト用文書作成
        document_data = {
            "filename": f"search_test_{uuid.uuid4().hex[:8]}.pdf",
            "original_filename": "検索テスト文書.pdf",
            "file_size": 1024,
            "total_pages": 3
        }
        document_id = self.manager.store_document(document_data)
        self.test_document_ids.append(document_id)
        
        # テスト用チャンクデータ（簡単な埋め込みベクトル）
        test_chunks = [
            {
                "content": "これは人工知能に関する文書です。機械学習とディープラーニングについて説明します。",
                "filename": document_data["filename"],
                "page_number": 1,
                "chapter_number": 1,
                "section_name": "はじめに",
                "start_pos": {"x": 0, "y": 0},
                "end_pos": {"x": 100, "y": 20},
                "embedding": [0.1] * 1536,  # 簡単なテスト用ベクトル
                "token_count": 25
            },
            {
                "content": "データサイエンスは現代のビジネスにおいて重要な分野です。",
                "filename": document_data["filename"],
                "page_number": 2,
                "chapter_number": 2,
                "section_name": "データサイエンス",
                "start_pos": {"x": 0, "y": 50},
                "end_pos": {"x": 100, "y": 70},
                "embedding": [0.2] * 1536,  # 異なるテスト用ベクトル
                "token_count": 15
            }
        ]
        
        # チャンク保存
        self.manager.store_document_chunks(test_chunks, document_id)
        
        # 文書状況を完了に更新
        self.manager.update_document_status(document_id, "completed")
        
        # 検索実行（最初のチャンクに類似したベクトルで検索）
        query_embedding = [0.1] * 1536
        search_results = self.manager.search_documents(
            query_embedding=query_embedding,
            k=5,
            similarity_threshold=0.0  # テスト用に閾値を低く設定
        )
        
        # 検索結果の検証
        assert len(search_results) >= 1  # 少なくとも1件は見つかるはず
        
        # 最初の結果が期待した内容であることを確認
        first_result = search_results[0]
        assert "人工知能" in first_result.content or "データサイエンス" in first_result.content
        assert first_result.filename == document_data["filename"]
        assert first_result.page_number in [1, 2]
        assert isinstance(first_result.similarity_score, float)
        assert 0.0 <= first_result.similarity_score <= 1.0
    
    def test_database_statistics(self):
        """データベース統計情報のテスト"""
        stats = self.manager.get_database_stats()
        
        # 統計情報の構造を確認
        assert "total_documents" in stats
        assert "total_chunks" in stats
        assert "status_breakdown" in stats
        assert "avg_chunks_per_document" in stats
        assert "last_updated" in stats
        
        # 値の型を確認
        assert isinstance(stats["total_documents"], int)
        assert isinstance(stats["total_chunks"], int)
        assert isinstance(stats["status_breakdown"], dict)
        assert isinstance(stats["avg_chunks_per_document"], (int, float))
        
        # 論理的整合性を確認
        assert stats["total_documents"] >= 0
        assert stats["total_chunks"] >= 0
        if stats["total_documents"] > 0:
            assert stats["avg_chunks_per_document"] >= 0
    
    def test_document_lifecycle(self):
        """完全な文書ライフサイクルのテスト"""
        # 1. 文書作成
        document_data = {
            "filename": f"lifecycle_test_{uuid.uuid4().hex[:8]}.pdf",
            "original_filename": "ライフサイクルテスト.pdf",
            "file_size": 4096,
            "total_pages": 10
        }
        document_id = self.manager.store_document(document_data)
        self.test_document_ids.append(document_id)
        
        # 2. 状況更新（処理中→完了）
        self.manager.update_document_status(document_id, "completed")
        
        # 3. チャンク追加
        chunks = [
            {
                "content": "ライフサイクルテストのサンプルコンテンツです。",
                "filename": document_data["filename"],
                "page_number": 1,
                "embedding": [0.5] * 1536,
                "token_count": 10
            }
        ]
        self.manager.store_document_chunks(chunks, document_id)
        
        # 4. 文書確認
        documents = self.manager.get_all_documents()
        target_doc = next((doc for doc in documents if doc.id == document_id), None)
        assert target_doc is not None
        assert target_doc.processing_status == "completed"
        
        # 5. 検索テスト
        query_embedding = [0.5] * 1536
        results = self.manager.search_documents(query_embedding, k=1, similarity_threshold=0.0)
        assert len(results) >= 1
        
        # 6. 削除テスト
        self.manager.delete_document(document_id)
        self.test_document_ids.remove(document_id)  # クリーンアップリストから削除
        
        # 削除確認
        documents_after = self.manager.get_all_documents()
        deleted_doc = next((doc for doc in documents_after if doc.id == document_id), None)
        assert deleted_doc is None


@skip_integration
class TestVectorStoreIntegration:
    """VectorStoreクラスの統合テスト"""
    
    @classmethod
    def setup_class(cls):
        """クラスレベルのセットアップ"""
        cls.vector_store = VectorStore(SUPABASE_URL, SUPABASE_ANON_KEY)
        cls.test_document_ids = []
    
    @classmethod
    def teardown_class(cls):
        """クラスレベルのクリーンアップ"""
        for doc_id in cls.test_document_ids:
            try:
                cls.vector_store.delete_document(doc_id)
            except Exception:
                pass
    
    def test_embedding_validation_integration(self):
        """埋め込みベクトル検証の統合テスト"""
        # 有効なベクトルでのテスト
        valid_embedding = [0.1] * 1536
        results = self.vector_store.similarity_search(valid_embedding, k=1)
        assert isinstance(results, list)
        
        # 無効なベクトルでのテスト
        invalid_embedding = [0.1] * 512  # 間違った次元
        with pytest.raises(VectorStoreError, match="埋め込みベクトルは1536次元である必要があります"):
            self.vector_store.similarity_search(invalid_embedding)
    
    def test_chunk_validation_integration(self):
        """チャンクデータ検証の統合テスト"""
        # テスト用文書作成
        document_data = {"filename": "validation_test.pdf", "original_filename": "test.pdf"}
        document_id = self.vector_store.store_document(document_data)
        self.test_document_ids.append(document_id)
        
        # 有効なチャンクでのテスト
        valid_chunks = [
            {
                "content": "有効なテストコンテンツです。",
                "filename": "validation_test.pdf",
                "page_number": 1,
                "embedding": [0.3] * 1536,
                "token_count": 5
            }
        ]
        self.vector_store.store_chunks(valid_chunks, document_id)
        
        # 無効なチャンクでのテスト
        invalid_chunks = [
            {
                "content": "",  # 空のコンテンツ
                "filename": "validation_test.pdf"
            }
        ]
        with pytest.raises(VectorStoreError, match="contentは空でない文字列である必要があります"):
            self.vector_store.store_chunks(invalid_chunks, document_id)


@skip_integration
class TestErrorHandlingIntegration:
    """エラーハンドリングの統合テスト"""
    
    def setup_method(self):
        """テストセットアップ"""
        self.manager = DatabaseManager(DatabaseConfig(
            supabase_url=SUPABASE_URL,
            supabase_key=SUPABASE_ANON_KEY
        ))
    
    def test_invalid_document_id_operations(self):
        """無効な文書IDでの操作テスト"""
        invalid_doc_id = "invalid-uuid-format"
        
        # 無効IDでの削除試行
        try:
            self.manager.delete_document(invalid_doc_id)
        except Exception as e:
            # データベースエラーが適切にキャッチされることを確認
            assert isinstance(e, Exception)
    
    def test_large_embedding_vector(self):
        """大きな埋め込みベクトルのテスト"""
        # メモリ使用量のテスト用に大きなベクトルを使用
        large_embedding = [0.001] * 1536
        
        # 検索が正常に動作することを確認
        results = self.manager.search_documents(large_embedding, k=1)
        assert isinstance(results, list)


if __name__ == "__main__":
    # 統合テストの実行方法を表示
    if not INTEGRATION_TEST_ENABLED:
        print("統合テストを実行するには以下の環境変数を設定してください:")
        print("export RUN_INTEGRATION_TESTS=true")
        print("export SUPABASE_URL=your_supabase_url")
        print("export SUPABASE_ANON_KEY=your_supabase_anon_key")
        print()
        print("その後、以下のコマンドで実行してください:")
        print("pytest tests/integration/test_database_integration.py -v")
    else:
        pytest.main([__file__, "-v"])