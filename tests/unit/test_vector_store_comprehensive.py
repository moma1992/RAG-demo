"""
VectorStoreクラスの包括的テストスイート

レビュー結果に基づく修正対応テスト
"""

import pytest
import uuid
import math
from unittest.mock import Mock, patch, MagicMock
from typing import List, Dict, Any

from services.vector_store import (
    VectorStore,
    SearchResult,
    DocumentRecord,
    VectorStoreError,
    validate_embedding_vector,
    validate_search_parameters,
    validate_chunk_data
)


class TestEmbeddingValidation:
    """埋め込みベクトル検証のテスト"""
    
    def test_validate_embedding_vector_valid(self):
        """有効な埋め込みベクトルの検証"""
        valid_embedding = [0.1] * 1536
        # 例外が発生しないことを確認
        validate_embedding_vector(valid_embedding)
    
    def test_validate_embedding_vector_empty(self):
        """空の埋め込みベクトルのテスト"""
        with pytest.raises(VectorStoreError, match="埋め込みベクトルが空です"):
            validate_embedding_vector([])
    
    def test_validate_embedding_vector_wrong_type(self):
        """リスト以外の型のテスト"""
        with pytest.raises(VectorStoreError, match="埋め込みベクトルはリスト形式である必要があります"):
            validate_embedding_vector("not_a_list")
    
    def test_validate_embedding_vector_wrong_dimension(self):
        """間違った次元数のテスト"""
        wrong_dimension = [0.1] * 512  # 1536ではない
        with pytest.raises(VectorStoreError, match="埋め込みベクトルは1536次元である必要があります"):
            validate_embedding_vector(wrong_dimension)
    
    def test_validate_embedding_vector_non_numeric(self):
        """数値以外の値が含まれるテスト"""
        invalid_embedding = [0.1] * 1535 + ["not_numeric"]
        with pytest.raises(VectorStoreError, match="インデックス 1535 の値が数値ではありません"):
            validate_embedding_vector(invalid_embedding)
    
    def test_validate_embedding_vector_nan(self):
        """NaN値が含まれるテスト"""
        invalid_embedding = [0.1] * 1535 + [float('nan')]
        with pytest.raises(VectorStoreError, match="インデックス 1535 にNaN値が含まれています"):
            validate_embedding_vector(invalid_embedding)
    
    def test_validate_embedding_vector_inf(self):
        """無限大値が含まれるテスト"""
        invalid_embedding = [0.1] * 1535 + [float('inf')]
        with pytest.raises(VectorStoreError, match="インデックス 1535 に無限大値が含まれています"):
            validate_embedding_vector(invalid_embedding)


class TestSearchParametersValidation:
    """検索パラメータ検証のテスト"""
    
    def test_validate_search_parameters_valid(self):
        """有効なパラメータの検証"""
        validate_search_parameters(5, 0.7)
    
    def test_validate_search_parameters_invalid_k_type(self):
        """無効なk（型）のテスト"""
        with pytest.raises(VectorStoreError, match="k は正の整数である必要があります"):
            validate_search_parameters("5", 0.7)
    
    def test_validate_search_parameters_invalid_k_value(self):
        """無効なk（値）のテスト"""
        with pytest.raises(VectorStoreError, match="k は正の整数である必要があります"):
            validate_search_parameters(0, 0.7)
    
    def test_validate_search_parameters_k_too_large(self):
        """kが大きすぎるテスト"""
        with pytest.raises(VectorStoreError, match="k は100以下である必要があります"):
            validate_search_parameters(101, 0.7)
    
    def test_validate_search_parameters_invalid_threshold_type(self):
        """無効な類似度閾値（型）のテスト"""
        with pytest.raises(VectorStoreError, match="similarity_threshold は数値である必要があります"):
            validate_search_parameters(5, "0.7")
    
    def test_validate_search_parameters_threshold_out_of_range(self):
        """範囲外の類似度閾値のテスト"""
        with pytest.raises(VectorStoreError, match="similarity_threshold は0.0-1.0の範囲である必要があります"):
            validate_search_parameters(5, 1.5)


class TestChunkDataValidation:
    """チャンクデータ検証のテスト"""
    
    def test_validate_chunk_data_valid(self):
        """有効なチャンクデータの検証"""
        valid_chunk = {
            'content': 'サンプルテキスト',
            'filename': 'test.pdf',
            'page_number': 1,
            'chapter_number': 1,
            'token_count': 10,
            'embedding': [0.1] * 1536
        }
        validate_chunk_data(valid_chunk)
    
    def test_validate_chunk_data_missing_required_field(self):
        """必須フィールド不足のテスト"""
        invalid_chunk = {'filename': 'test.pdf'}  # contentが不足
        with pytest.raises(VectorStoreError, match="必須フィールド 'content' が不足しています"):
            validate_chunk_data(invalid_chunk)
    
    def test_validate_chunk_data_empty_content(self):
        """空のcontentのテスト"""
        invalid_chunk = {'content': '', 'filename': 'test.pdf'}
        with pytest.raises(VectorStoreError, match="contentは空でない文字列である必要があります"):
            validate_chunk_data(invalid_chunk)
    
    def test_validate_chunk_data_content_too_long(self):
        """長すぎるcontentのテスト"""
        invalid_chunk = {
            'content': 'a' * 10001,  # 10KB制限を超過
            'filename': 'test.pdf'
        }
        with pytest.raises(VectorStoreError, match="contentが長すぎます"):
            validate_chunk_data(invalid_chunk)
    
    def test_validate_chunk_data_invalid_page_number(self):
        """無効なpage_numberのテスト"""
        invalid_chunk = {
            'content': 'テスト',
            'filename': 'test.pdf',
            'page_number': 0  # 正の整数でない
        }
        with pytest.raises(VectorStoreError, match="page_numberは正の整数である必要があります"):
            validate_chunk_data(invalid_chunk)


class TestVectorStoreInit:
    """VectorStore初期化のテスト"""
    
    @patch('services.vector_store.create_client')
    def test_init_success(self, mock_create_client):
        """正常な初期化のテスト"""
        mock_client = Mock()
        mock_create_client.return_value = mock_client
        
        store = VectorStore("https://test.supabase.co", "test_key")
        
        assert store.supabase_url == "https://test.supabase.co"
        assert store.supabase_key == "test_key"
        assert store.client == mock_client
        mock_create_client.assert_called_once_with("https://test.supabase.co", "test_key")
    
    @patch('services.vector_store.create_client', side_effect=ImportError)
    def test_init_import_error(self, mock_create_client):
        """インポートエラー時の初期化テスト"""
        store = VectorStore("https://test.supabase.co", "test_key")
        
        assert store.client is None


class TestVectorStoreStoreChunks:
    """store_chunksメソッドのテスト"""
    
    def setup_method(self):
        """テストセットアップ"""
        self.mock_client = Mock()
        self.store = VectorStore("https://test.supabase.co", "test_key")
        self.store.client = self.mock_client
    
    def test_store_chunks_success(self):
        """正常なチャンク保存のテスト"""
        valid_chunks = [
            {
                'content': 'テストコンテンツ1',
                'filename': 'test.pdf',
                'page_number': 1,
                'embedding': [0.1] * 1536
            },
            {
                'content': 'テストコンテンツ2',
                'filename': 'test.pdf',
                'page_number': 2,
                'embedding': [0.2] * 1536
            }
        ]
        document_id = str(uuid.uuid4())
        
        mock_result = Mock()
        self.mock_client.table.return_value.insert.return_value.execute.return_value = mock_result
        
        self.store.store_chunks(valid_chunks, document_id)
        
        # メソッド呼び出しの確認
        self.mock_client.table.assert_called_once_with("document_chunks")
        self.mock_client.table.return_value.insert.assert_called_once()
        self.mock_client.table.return_value.insert.return_value.execute.assert_called_once()
    
    def test_store_chunks_no_client(self):
        """クライアント未初期化のテスト"""
        store = VectorStore("https://test.supabase.co", "test_key")
        store.client = None
        
        with pytest.raises(VectorStoreError, match="Supabaseクライアントが初期化されていません"):
            store.store_chunks([{'content': 'test', 'filename': 'test.pdf'}], "doc_id")
    
    def test_store_chunks_empty_list(self):
        """空のチャンクリストのテスト"""
        with pytest.raises(VectorStoreError, match="チャンクリストが空です"):
            self.store.store_chunks([], "doc_id")
    
    def test_store_chunks_invalid_document_id(self):
        """無効なdocument_idのテスト"""
        valid_chunks = [{'content': 'test', 'filename': 'test.pdf'}]
        
        with pytest.raises(VectorStoreError, match="document_idが無効です"):
            self.store.store_chunks(valid_chunks, "")
    
    def test_store_chunks_invalid_chunk_data(self):
        """無効なチャンクデータのテスト"""
        invalid_chunks = [{'filename': 'test.pdf'}]  # contentが不足
        
        with pytest.raises(VectorStoreError, match="チャンク 0 の検証エラー"):
            self.store.store_chunks(invalid_chunks, "doc_id")


class TestVectorStoreSimilaritySearch:
    """similarity_searchメソッドのテスト"""
    
    def setup_method(self):
        """テストセットアップ"""
        self.mock_client = Mock()
        self.store = VectorStore("https://test.supabase.co", "test_key")
        self.store.client = self.mock_client
    
    def test_similarity_search_success(self):
        """正常な類似検索のテスト"""
        query_embedding = [0.1] * 1536
        
        # モックレスポンスデータ
        mock_result = Mock()
        mock_result.data = [
            {
                'id': str(uuid.uuid4()),
                'content': 'テストコンテンツ',
                'filename': 'test.pdf',
                'page_number': 1,
                'chapter_number': 1,
                'section_name': 'はじめに',
                'start_pos': {'x': 0, 'y': 0},
                'end_pos': {'x': 100, 'y': 20},
                'token_count': 10,
                'distance': 0.2
            }
        ]
        self.mock_client.rpc.return_value.execute.return_value = mock_result
        
        results = self.store.similarity_search(query_embedding, k=5, similarity_threshold=0.7)
        
        assert len(results) == 1
        assert isinstance(results[0], SearchResult)
        assert results[0].content == 'テストコンテンツ'
        assert results[0].similarity_score == 0.8  # 1.0 - 0.2
        
        # RPC呼び出しの確認
        self.mock_client.rpc.assert_called_once_with(
            'match_documents',
            {
                'query_embedding': query_embedding,
                'match_threshold': 0.3,  # 1.0 - 0.7
                'match_count': 5
            }
        )
    
    def test_similarity_search_invalid_embedding(self):
        """無効な埋め込みベクトルのテスト"""
        invalid_embedding = [0.1] * 512  # 間違った次元
        
        with pytest.raises(VectorStoreError, match="埋め込みベクトルは1536次元である必要があります"):
            self.store.similarity_search(invalid_embedding)
    
    def test_similarity_search_invalid_parameters(self):
        """無効なパラメータのテスト"""
        valid_embedding = [0.1] * 1536
        
        with pytest.raises(VectorStoreError, match="k は正の整数である必要があります"):
            self.store.similarity_search(valid_embedding, k=0)
    
    def test_similarity_search_empty_result(self):
        """空の検索結果のテスト"""
        query_embedding = [0.1] * 1536
        
        mock_result = Mock()
        mock_result.data = None
        self.mock_client.rpc.return_value.execute.return_value = mock_result
        
        results = self.store.similarity_search(query_embedding)
        
        assert results == []


class TestVectorStoreDocumentOperations:
    """文書操作メソッドのテスト"""
    
    def setup_method(self):
        """テストセットアップ"""
        self.mock_client = Mock()
        self.store = VectorStore("https://test.supabase.co", "test_key")
        self.store.client = self.mock_client
    
    def test_store_document_success(self):
        """正常な文書保存のテスト"""
        document_data = {
            "filename": "test.pdf",
            "original_filename": "テスト文書.pdf",
            "file_size": 1024,
            "total_pages": 10
        }
        
        mock_result = Mock()
        self.mock_client.table.return_value.insert.return_value.execute.return_value = mock_result
        
        with patch('uuid.uuid4') as mock_uuid:
            mock_uuid.return_value = "test-doc-id"
            document_id = self.store.store_document(document_data)
        
        assert document_id == "test-doc-id"
        self.mock_client.table.assert_called_with("documents")
    
    def test_get_documents_success(self):
        """正常な文書一覧取得のテスト"""
        mock_result = Mock()
        mock_result.data = [
            {
                'id': 'doc-1',
                'filename': 'test.pdf',
                'original_filename': 'テスト.pdf',
                'upload_date': '2024-01-01T00:00:00Z',
                'file_size': 1024,
                'total_pages': 10,
                'processing_status': 'completed'
            }
        ]
        self.mock_client.table.return_value.select.return_value.order.return_value.execute.return_value = mock_result
        
        documents = self.store.get_documents()
        
        assert len(documents) == 1
        assert isinstance(documents[0], DocumentRecord)
        assert documents[0].id == 'doc-1'
        assert documents[0].filename == 'test.pdf'
    
    def test_delete_document_success(self):
        """正常な文書削除のテスト"""
        document_id = "test-doc-id"
        
        mock_result = Mock()
        self.mock_client.table.return_value.delete.return_value.eq.return_value.execute.return_value = mock_result
        
        self.store.delete_document(document_id)
        
        self.mock_client.table.assert_called_with("documents")
        self.mock_client.table.return_value.delete.return_value.eq.assert_called_with("id", document_id)


class TestVectorStoreErrorHandling:
    """エラーハンドリングのテスト"""
    
    def setup_method(self):
        """テストセットアップ"""
        self.mock_client = Mock()
        self.store = VectorStore("https://test.supabase.co", "test_key")
        self.store.client = self.mock_client
    
    def test_database_error_handling(self):
        """データベースエラーのハンドリングテスト"""
        self.mock_client.table.return_value.insert.return_value.execute.side_effect = Exception("DB Error")
        
        document_data = {"filename": "test.pdf", "original_filename": "test.pdf"}
        
        with pytest.raises(VectorStoreError, match="文書保存中にエラーが発生しました"):
            self.store.store_document(document_data)
    
    def test_network_error_handling(self):
        """ネットワークエラーのハンドリングテスト"""
        self.mock_client.rpc.return_value.execute.side_effect = Exception("Network Error")
        
        query_embedding = [0.1] * 1536
        
        with pytest.raises(VectorStoreError, match="類似検索中にエラーが発生しました"):
            self.store.similarity_search(query_embedding)


class TestVectorStoreIntegration:
    """統合テスト"""
    
    @patch('services.vector_store.create_client')
    def test_full_workflow(self, mock_create_client):
        """完全なワークフローのテスト"""
        mock_client = Mock()
        mock_create_client.return_value = mock_client
        
        # VectorStore初期化
        store = VectorStore("https://test.supabase.co", "test_key")
        
        # 文書保存
        document_data = {"filename": "test.pdf", "original_filename": "test.pdf"}
        with patch('uuid.uuid4', return_value="doc-id"):
            document_id = store.store_document(document_data)
        
        # チャンク保存
        chunks = [
            {
                'content': 'テストコンテンツ',
                'filename': 'test.pdf',
                'page_number': 1,
                'embedding': [0.1] * 1536
            }
        ]
        store.store_chunks(chunks, document_id)
        
        # 類似検索
        query_embedding = [0.1] * 1536
        mock_client.rpc.return_value.execute.return_value.data = []
        results = store.similarity_search(query_embedding)
        
        # 文書削除
        store.delete_document(document_id)
        
        # すべての操作が例外なく完了することを確認
        assert document_id == "doc-id"
        assert results == []


if __name__ == "__main__":
    pytest.main([__file__, "-v"])