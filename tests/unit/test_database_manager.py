"""
DatabaseManagerクラスのテストスイート

レビュー結果対応における追加テスト
"""

import pytest
import os
from unittest.mock import Mock, patch, MagicMock
from typing import List, Dict, Any

from services.database_manager import (
    DatabaseManager,
    DatabaseConfig,
    DatabaseManagerError
)
from services.vector_store import SearchResult, DocumentRecord, VectorStoreError


class TestDatabaseConfig:
    """DatabaseConfigのテスト"""
    
    def test_database_config_creation(self):
        """DatabaseConfig作成のテスト"""
        config = DatabaseConfig(
            supabase_url="https://test.supabase.co",
            supabase_key="test_key",
            max_file_size_mb=100,
            chunk_size=1024,
            chunk_overlap=0.2,
            similarity_threshold=0.8,
            search_top_k=10
        )
        
        assert config.supabase_url == "https://test.supabase.co"
        assert config.supabase_key == "test_key"
        assert config.max_file_size_mb == 100
        assert config.chunk_size == 1024
        assert config.chunk_overlap == 0.2
        assert config.similarity_threshold == 0.8
        assert config.search_top_k == 10
    
    def test_database_config_defaults(self):
        """DatabaseConfigデフォルト値のテスト"""
        config = DatabaseConfig(
            supabase_url="https://test.supabase.co",
            supabase_key="test_key"
        )
        
        assert config.max_file_size_mb == 50
        assert config.chunk_size == 512
        assert config.chunk_overlap == 0.1
        assert config.similarity_threshold == 0.7
        assert config.search_top_k == 5


class TestDatabaseManagerInit:
    """DatabaseManager初期化のテスト"""
    
    @patch('services.database_manager.VectorStore')
    def test_init_with_config(self, mock_vector_store):
        """設定指定での初期化テスト"""
        config = DatabaseConfig(
            supabase_url="https://test.supabase.co",
            supabase_key="test_key"
        )
        
        manager = DatabaseManager(config)
        
        assert manager.config == config
        mock_vector_store.assert_called_once_with(
            supabase_url="https://test.supabase.co",
            supabase_key="test_key"
        )
    
    @patch.dict(os.environ, {
        'SUPABASE_URL': 'https://env.supabase.co',
        'SUPABASE_ANON_KEY': 'env_key',
        'MAX_FILE_SIZE_MB': '100',
        'CHUNK_SIZE': '1024',
        'CHUNK_OVERLAP': '0.2',
        'SIMILARITY_THRESHOLD': '0.8',
        'SEARCH_TOP_K': '10'
    })
    @patch('services.database_manager.VectorStore')
    def test_init_from_env(self, mock_vector_store):
        """環境変数からの初期化テスト"""
        manager = DatabaseManager()
        
        assert manager.config.supabase_url == "https://env.supabase.co"
        assert manager.config.supabase_key == "env_key"
        assert manager.config.max_file_size_mb == 100
        assert manager.config.chunk_size == 1024
        assert manager.config.chunk_overlap == 0.2
        assert manager.config.similarity_threshold == 0.8
        assert manager.config.search_top_k == 10
    
    @patch.dict(os.environ, {}, clear=True)
    def test_init_missing_env_vars(self):
        """必須環境変数不足のテスト"""
        with pytest.raises(ValueError, match="SUPABASE_URLとSUPABASE_ANON_KEYの環境変数が必要です"):
            DatabaseManager()
    
    @patch.dict(os.environ, {
        'SUPABASE_URL': 'https://env.supabase.co',
        'SUPABASE_ANON_KEY': ''  # 空文字
    })
    def test_init_empty_env_vars(self):
        """空の環境変数のテスト"""
        with pytest.raises(ValueError, match="SUPABASE_URLとSUPABASE_ANON_KEYの環境変数が必要です"):
            DatabaseManager()


class TestDatabaseManagerOperations:
    """DatabaseManager操作のテスト"""
    
    def setup_method(self):
        """テストセットアップ"""
        self.config = DatabaseConfig(
            supabase_url="https://test.supabase.co",
            supabase_key="test_key"
        )
        
        with patch('services.database_manager.VectorStore') as mock_vector_store:
            self.mock_vector_store = Mock()
            mock_vector_store.return_value = self.mock_vector_store
            self.manager = DatabaseManager(self.config)
    
    def test_store_document_success(self):
        """正常な文書保存のテスト"""
        document_data = {"filename": "test.pdf", "file_size": 1024}
        expected_id = "doc-123"
        
        self.mock_vector_store.store_document.return_value = expected_id
        
        result = self.manager.store_document(document_data)
        
        assert result == expected_id
        self.mock_vector_store.store_document.assert_called_once_with(document_data)
    
    def test_store_document_error(self):
        """文書保存エラーのテスト"""
        document_data = {"filename": "test.pdf"}
        
        self.mock_vector_store.store_document.side_effect = VectorStoreError("Database error")
        
        with pytest.raises(DatabaseManagerError, match="文書保存エラー"):
            self.manager.store_document(document_data)
    
    def test_store_document_chunks_success(self):
        """正常なチャンク保存のテスト"""
        chunks = [{"content": "test", "filename": "test.pdf"}]
        document_id = "doc-123"
        
        self.manager.store_document_chunks(chunks, document_id)
        
        self.mock_vector_store.store_chunks.assert_called_once_with(chunks, document_id)
    
    def test_store_document_chunks_error(self):
        """チャンク保存エラーのテスト"""
        chunks = [{"content": "test", "filename": "test.pdf"}]
        document_id = "doc-123"
        
        self.mock_vector_store.store_chunks.side_effect = VectorStoreError("Chunk error")
        
        with pytest.raises(DatabaseManagerError, match="チャンク保存エラー"):
            self.manager.store_document_chunks(chunks, document_id)
    
    def test_search_documents_success(self):
        """正常な文書検索のテスト"""
        query_embedding = [0.1] * 1536
        expected_results = [
            SearchResult(
                content="test content",
                filename="test.pdf",
                page_number=1,
                similarity_score=0.8,
                metadata={}
            )
        ]
        
        self.mock_vector_store.similarity_search.return_value = expected_results
        
        results = self.manager.search_documents(query_embedding)
        
        assert results == expected_results
        self.mock_vector_store.similarity_search.assert_called_once_with(
            query_embedding=query_embedding,
            k=5,  # デフォルト値
            similarity_threshold=0.7  # デフォルト値
        )
    
    def test_search_documents_with_custom_params(self):
        """カスタムパラメータでの検索テスト"""
        query_embedding = [0.1] * 1536
        
        self.manager.search_documents(query_embedding, k=10, similarity_threshold=0.8)
        
        self.mock_vector_store.similarity_search.assert_called_once_with(
            query_embedding=query_embedding,
            k=10,
            similarity_threshold=0.8
        )
    
    def test_search_documents_error(self):
        """検索エラーのテスト"""
        query_embedding = [0.1] * 1536
        
        self.mock_vector_store.similarity_search.side_effect = VectorStoreError("Search error")
        
        with pytest.raises(DatabaseManagerError, match="検索エラー"):
            self.manager.search_documents(query_embedding)
    
    def test_get_all_documents_success(self):
        """正常な文書一覧取得のテスト"""
        expected_documents = [
            DocumentRecord(
                id="doc-1",
                filename="test.pdf",
                original_filename="test.pdf",
                upload_date="2024-01-01T00:00:00Z",
                file_size=1024,
                total_pages=10,
                processing_status="completed"
            )
        ]
        
        self.mock_vector_store.get_documents.return_value = expected_documents
        
        results = self.manager.get_all_documents()
        
        assert results == expected_documents
        self.mock_vector_store.get_documents.assert_called_once()
    
    def test_delete_document_success(self):
        """正常な文書削除のテスト"""
        document_id = "doc-123"
        
        self.manager.delete_document(document_id)
        
        self.mock_vector_store.delete_document.assert_called_once_with(document_id)


class TestDatabaseManagerAdvancedOperations:
    """DatabaseManager高度な操作のテスト"""
    
    def setup_method(self):
        """テストセットアップ"""
        self.config = DatabaseConfig(
            supabase_url="https://test.supabase.co",
            supabase_key="test_key"
        )
        
        with patch('services.database_manager.VectorStore') as mock_vector_store:
            self.mock_vector_store = Mock()
            mock_vector_store.return_value = self.mock_vector_store
            self.manager = DatabaseManager(self.config)
    
    def test_update_document_status_success(self):
        """正常な文書状況更新のテスト"""
        document_id = "doc-123"
        status = "completed"
        
        # Supabaseクライアントのモック
        mock_client = Mock()
        self.mock_vector_store.client = mock_client
        
        self.manager.update_document_status(document_id, status)
        
        mock_client.table.assert_called_with("documents")
        mock_client.table.return_value.update.assert_called_with({
            "processing_status": status,
            "updated_at": "now()"
        })
        mock_client.table.return_value.update.return_value.eq.assert_called_with("id", document_id)
    
    def test_update_document_status_no_client(self):
        """クライアント未初期化での状況更新テスト"""
        self.mock_vector_store.client = None
        
        with pytest.raises(DatabaseManagerError, match="Supabaseクライアントが初期化されていません"):
            self.manager.update_document_status("doc-123", "completed")
    
    def test_get_database_stats_success(self):
        """正常な統計情報取得のテスト"""
        mock_client = Mock()
        self.mock_vector_store.client = mock_client
        
        # 文書数のモック
        doc_result = Mock()
        doc_result.count = 10
        mock_client.table.return_value.select.return_value.execute.return_value = doc_result
        
        # チャンク数のモック
        chunk_result = Mock()
        chunk_result.count = 50
        
        # ステータス別文書数のモック
        status_result = Mock()
        status_result.data = [
            {"processing_status": "completed"},
            {"processing_status": "completed"},
            {"processing_status": "processing"}
        ]
        
        # table()の呼び出し順序に応じて異なる結果を返す
        mock_client.table.return_value.select.return_value.execute.side_effect = [
            doc_result, chunk_result, status_result
        ]
        
        stats = self.manager.get_database_stats()
        
        assert stats["total_documents"] == 10
        assert stats["total_chunks"] == 50
        assert stats["status_breakdown"]["completed"] == 2
        assert stats["status_breakdown"]["processing"] == 1
        assert stats["avg_chunks_per_document"] == 5.0
        assert "last_updated" in stats
    
    def test_get_database_stats_zero_documents(self):
        """文書数ゼロでの統計情報取得テスト"""
        mock_client = Mock()
        self.mock_vector_store.client = mock_client
        
        # 文書数とチャンク数がゼロのモック
        zero_result = Mock()
        zero_result.count = 0
        
        status_result = Mock()
        status_result.data = []
        
        mock_client.table.return_value.select.return_value.execute.side_effect = [
            zero_result, zero_result, status_result
        ]
        
        stats = self.manager.get_database_stats()
        
        assert stats["total_documents"] == 0
        assert stats["total_chunks"] == 0
        assert stats["avg_chunks_per_document"] == 0
    
    def test_health_check_success(self):
        """正常なヘルスチェックのテスト"""
        mock_client = Mock()
        self.mock_vector_store.client = mock_client
        
        mock_result = Mock()
        mock_client.table.return_value.select.return_value.limit.return_value.execute.return_value = mock_result
        
        result = self.manager.health_check()
        
        assert result["status"] == "healthy"
        assert result["message"] == "データベース接続正常"
        assert "timestamp" in result
    
    def test_health_check_no_client(self):
        """クライアント未初期化でのヘルスチェックテスト"""
        self.mock_vector_store.client = None
        
        result = self.manager.health_check()
        
        assert result["status"] == "error"
        assert "Supabaseクライアントが初期化されていません" in result["message"]
    
    def test_health_check_database_error(self):
        """データベースエラーでのヘルスチェックテスト"""
        mock_client = Mock()
        self.mock_vector_store.client = mock_client
        
        mock_client.table.return_value.select.return_value.limit.return_value.execute.side_effect = Exception("DB Error")
        
        result = self.manager.health_check()
        
        assert result["status"] == "error"
        assert "データベース接続エラー" in result["message"]


class TestDatabaseManagerIntegration:
    """DatabaseManager統合テスト"""
    
    @patch.dict(os.environ, {
        'SUPABASE_URL': 'https://test.supabase.co',
        'SUPABASE_ANON_KEY': 'test_key',
        'SEARCH_TOP_K': '3',
        'SIMILARITY_THRESHOLD': '0.8'
    })
    @patch('services.database_manager.VectorStore')
    def test_full_document_lifecycle(self, mock_vector_store_class):
        """完全な文書ライフサイクルのテスト"""
        mock_vector_store = Mock()
        mock_vector_store_class.return_value = mock_vector_store
        
        # DatabaseManager初期化
        manager = DatabaseManager()
        
        # 1. 文書保存
        document_data = {"filename": "test.pdf", "file_size": 1024}
        mock_vector_store.store_document.return_value = "doc-123"
        document_id = manager.store_document(document_data)
        
        # 2. チャンク保存
        chunks = [{"content": "test content", "filename": "test.pdf"}]
        manager.store_document_chunks(chunks, document_id)
        
        # 3. 文書状況更新
        mock_vector_store.client = Mock()
        manager.update_document_status(document_id, "completed")
        
        # 4. 検索実行
        query_embedding = [0.1] * 1536
        mock_search_results = [Mock()]
        mock_vector_store.similarity_search.return_value = mock_search_results
        
        search_results = manager.search_documents(query_embedding)
        
        # 5. 統計情報取得
        mock_vector_store.client.table.return_value.select.return_value.execute.side_effect = [
            Mock(count=1), Mock(count=1), Mock(data=[{"processing_status": "completed"}])
        ]
        stats = manager.get_database_stats()
        
        # 6. ヘルスチェック
        health = manager.health_check()
        
        # 7. 文書削除
        manager.delete_document(document_id)
        
        # すべての操作が正常に完了することを確認
        assert document_id == "doc-123"
        assert search_results == mock_search_results
        assert stats["total_documents"] == 1
        assert health["status"] == "healthy"
        
        # 各操作が適切に呼び出されたことを確認
        mock_vector_store.store_document.assert_called_once()
        mock_vector_store.store_chunks.assert_called_once()
        mock_vector_store.similarity_search.assert_called_once_with(
            query_embedding=query_embedding,
            k=3,  # 環境変数から
            similarity_threshold=0.8  # 環境変数から
        )
        mock_vector_store.delete_document.assert_called_once_with(document_id)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])