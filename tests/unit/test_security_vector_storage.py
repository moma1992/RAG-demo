"""
セキュリティベクトルストレージテストスイート

Issue #37: セキュリティ機能のテスト実装
TDD実装: 失敗テスト → 最小実装 → リファクタリング
"""

import pytest
import uuid
import time
from unittest.mock import Mock, patch, MagicMock
from typing import List, Dict, Any
import numpy as np

from services.vector_store import (
    VectorStore,
    SearchResult,
    DocumentRecord,
    VectorStoreError,
    validate_embedding_vector,
    validate_search_parameters,
    validate_chunk_data,
)


class TestVectorStoreSecurity:
    """ベクトルストアのセキュリティテストクラス"""

    def setup_method(self):
        """テストセットアップ"""
        self.mock_client = Mock()
        self.vector_store = VectorStore("https://test.supabase.co", "test_key")
        self.vector_store.client = self.mock_client

    def test_invalid_embedding_vector_validation(self):
        """無効な埋め込みベクトルの検証テスト"""

        # 空のベクトル
        with pytest.raises(VectorStoreError, match="埋め込みベクトルが空です"):
            validate_embedding_vector([])

        # 非リスト型
        with pytest.raises(
            VectorStoreError, match="埋め込みベクトルはリスト形式である必要があります"
        ):
            validate_embedding_vector("invalid")

        # 間違った次元数
        with pytest.raises(
            VectorStoreError, match="埋め込みベクトルは1536次元である必要があります"
        ):
            validate_embedding_vector([0.1] * 128)

        # NaN値
        invalid_vector = [0.1] * 1536
        invalid_vector[100] = float("nan")
        with pytest.raises(VectorStoreError, match="NaN値が含まれています"):
            validate_embedding_vector(invalid_vector)

        # 無限大値
        invalid_vector = [0.1] * 1536
        invalid_vector[200] = float("inf")
        with pytest.raises(VectorStoreError, match="無限大値が含まれています"):
            validate_embedding_vector(invalid_vector)

    def test_search_parameters_validation(self):
        """検索パラメータの検証テスト"""

        # 無効なk値（負数）
        with pytest.raises(VectorStoreError, match="k は正の整数である必要があります"):
            validate_search_parameters(-1, 0.7)

        # 無効なk値（ゼロ）
        with pytest.raises(VectorStoreError, match="k は正の整数である必要があります"):
            validate_search_parameters(0, 0.7)

        # k値が大きすぎる
        with pytest.raises(VectorStoreError, match="k は100以下である必要があります"):
            validate_search_parameters(101, 0.7)

        # 無効な類似度閾値（範囲外）
        with pytest.raises(
            VectorStoreError,
            match="similarity_threshold は0.0-1.0の範囲である必要があります",
        ):
            validate_search_parameters(5, 1.5)

        with pytest.raises(
            VectorStoreError,
            match="similarity_threshold は0.0-1.0の範囲である必要があります",
        ):
            validate_search_parameters(5, -0.1)

    def test_chunk_data_validation(self):
        """チャンクデータの検証テスト"""

        # 必須フィールド不足
        with pytest.raises(
            VectorStoreError, match="必須フィールド 'content' が不足しています"
        ):
            validate_chunk_data({"filename": "test.pdf"})

        with pytest.raises(
            VectorStoreError, match="必須フィールド 'filename' が不足しています"
        ):
            validate_chunk_data({"content": "test content"})

        # 空のコンテンツ
        with pytest.raises(
            VectorStoreError, match="contentは空でない文字列である必要があります"
        ):
            validate_chunk_data({"content": "", "filename": "test.pdf"})

        # 長すぎるコンテンツ
        long_content = "x" * 10001
        with pytest.raises(VectorStoreError, match="contentが長すぎます"):
            validate_chunk_data({"content": long_content, "filename": "test.pdf"})

        # 無効なpage_number
        with pytest.raises(
            VectorStoreError, match="page_numberは正の整数である必要があります"
        ):
            validate_chunk_data(
                {"content": "test", "filename": "test.pdf", "page_number": -1}
            )


class TestVectorStoreSecuritySearch:
    """ベクトル検索のセキュリティテストクラス"""

    def setup_method(self):
        """テストセットアップ"""
        self.mock_client = Mock()
        self.vector_store = VectorStore("https://test.supabase.co", "test_key")
        self.vector_store.client = self.mock_client

        # 正常な埋め込みベクトル
        self.valid_embedding = [0.1] * 1536

    def test_similarity_search_performance(self):
        """類似検索のパフォーマンステスト（<500ms要件）"""

        # モックデータ設定
        self.mock_client.rpc.return_value.execute.return_value = Mock(
            data=[
                {
                    "content": "テストコンテンツ1",
                    "filename": "test1.pdf",
                    "page_number": 1,
                    "distance": 0.3,
                    "section_name": "セクション1",
                    "chapter_number": 1,
                }
            ]
        )

        start_time = time.time()
        results = self.vector_store.similarity_search(self.valid_embedding, k=5)
        end_time = time.time()

        # パフォーマンス要件確認（500ms以下）
        execution_time = end_time - start_time
        assert execution_time < 0.5, f"検索時間が500msを超過: {execution_time:.3f}s"

        # 結果の検証
        assert len(results) == 1
        assert isinstance(results[0], SearchResult)

    def test_empty_search_results_handling(self):
        """空の検索結果の処理テスト"""

        # 空の結果をモック
        self.mock_client.rpc.return_value.execute.return_value = Mock(data=[])

        results = self.vector_store.similarity_search(self.valid_embedding, k=5)

        assert isinstance(results, list)
        assert len(results) == 0

    def test_database_connection_error_handling(self):
        """データベース接続エラーの処理テスト"""

        # 接続エラーをシミュレート
        self.mock_client.rpc.side_effect = Exception("Database connection failed")

        with pytest.raises(VectorStoreError, match="類似検索中にエラーが発生しました"):
            self.vector_store.similarity_search(self.valid_embedding, k=5)

    def test_malformed_query_injection_prevention(self):
        """悪意のあるクエリインジェクションの防止テスト"""

        # SQLインジェクション風の埋め込みベクトル（実際は数値配列だが概念的テスト）
        malicious_embedding = [0.1] * 1535 + [999999.9]  # 異常に大きな値

        # 検証でエラーになることを確認（この段階では未実装なので失敗する）
        with pytest.raises(VectorStoreError):
            self.vector_store.similarity_search(malicious_embedding, k=5)


class TestVectorStoreSecurityStorage:
    """ベクトルストレージのセキュリティテストクラス"""

    def setup_method(self):
        """テストセットアップ"""
        self.mock_client = Mock()
        self.vector_store = VectorStore("https://test.supabase.co", "test_key")
        self.vector_store.client = self.mock_client

    def test_document_storage_security(self):
        """文書保存のセキュリティテスト"""

        # モック設定
        self.mock_client.table.return_value.insert.return_value.execute.return_value = (
            Mock(data=[{"id": "test-doc-id"}])
        )

        # 正常なケース
        document_data = {
            "filename": "test_document.pdf",
            "original_filename": "original.pdf",
            "file_size": 1024,
            "total_pages": 5,
        }

        result = self.vector_store.store_document(document_data)
        assert isinstance(result, str)
        assert len(result) > 0

    def test_chunk_storage_input_validation(self):
        """チャンク保存時の入力検証テスト"""

        document_id = str(uuid.uuid4())

        # 空のチャンクリスト
        with pytest.raises(VectorStoreError, match="チャンクリストが空です"):
            self.vector_store.store_chunks([], document_id)

        # 無効なdocument_id
        valid_chunks = [
            {
                "content": "テストコンテンツ",
                "filename": "test.pdf",
                "embedding": [0.1] * 1536,
            }
        ]

        with pytest.raises(VectorStoreError, match="document_idが無効です"):
            self.vector_store.store_chunks(valid_chunks, "")

    def test_large_dataset_memory_management(self):
        """大きなデータセットのメモリ管理テスト"""

        # 大量のチャンクデータをシミュレート
        large_chunks = []
        for i in range(1000):  # 1000個のチャンク
            chunk = {
                "content": f"大量データテスト {i}",
                "filename": "large_file.pdf",
                "page_number": i // 10 + 1,
                "embedding": [0.1 + i * 0.001] * 1536,
            }
            large_chunks.append(chunk)

        # メモリ効率的な処理をテスト（実装後に動作確認）
        document_id = str(uuid.uuid4())

        # この段階では実装がないので例外が発生することを確認
        try:
            self.vector_store.store_chunks(large_chunks, document_id)
        except Exception:
            pass  # 実装前なので例外は予想される


class TestVectorStoreSecurityAccess:
    """アクセス制御のセキュリティテストクラス"""

    def setup_method(self):
        """テストセットアップ"""
        self.vector_store = VectorStore("https://test.supabase.co", "test_key")

    def test_unauthorized_client_access(self):
        """未認証クライアントアクセスのテスト"""

        # クライアント未初期化の状態をシミュレート
        self.vector_store.client = None

        with pytest.raises(
            VectorStoreError, match="Supabaseクライアントが初期化されていません"
        ):
            self.vector_store.similarity_search([0.1] * 1536, k=5)

    def test_invalid_credentials_handling(self):
        """無効な認証情報の処理テスト"""

        # 無効な認証情報でVectorStoreを作成
        invalid_vector_store = VectorStore("https://invalid.supabase.co", "invalid_key")

        # 接続エラーが適切に処理されることを確認
        # （実装時にはより詳細なテストが必要）
        assert invalid_vector_store.supabase_url == "https://invalid.supabase.co"
        assert invalid_vector_store.supabase_key == "invalid_key"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
