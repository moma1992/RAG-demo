"""
VectorStorageクラスのセキュリティテストスイート

Issue #36: セキュリティ機能のテスト
優先度高対応: セキュリティテストの追加
"""

import pytest
import uuid
from unittest.mock import Mock, patch
from typing import List
from datetime import datetime

from services.vector_storage import (
    VectorStorage,
    ChunkData,
    BatchResult,
    VectorStorageError
)


class TestVectorStorageSecurity:
    """VectorStorageセキュリティテストクラス"""
    
    def setup_method(self):
        """テストセットアップ"""
        self.mock_client = Mock()
        self.storage = VectorStorage("https://test.supabase.co", "test_key", batch_size=50)
        self.storage.client = self.mock_client
    
    def test_sql_injection_prevention(self):
        """SQLインジェクション攻撃の防止テスト"""
        
        # 悪意のあるSQLコンテンツでのチャンク作成を試行
        malicious_contents = [
            "'; DROP TABLE document_chunks; --",
            "UNION SELECT * FROM users",
            "INSERT INTO admin VALUES('hacker', 'password')",
            "DELETE FROM important_data WHERE id > 0"
        ]
        
        for malicious_content in malicious_contents:
            with pytest.raises(VectorStorageError, match="セキュリティ違反"):
                ChunkData(
                    id=str(uuid.uuid4()),
                    document_id=str(uuid.uuid4()),
                    content=malicious_content,
                    filename="test.pdf",
                    page_number=1,
                    embedding=[0.1] * 1536,
                    token_count=10
                )
    
    def test_script_injection_prevention(self):
        """スクリプトインジェクション攻撃の防止テスト"""
        
        malicious_scripts = [
            "javascript:alert('malicious')",
            "vbscript:msgbox('attack')",
            "eval(malicious_code)"
        ]
        
        for script in malicious_scripts:
            with pytest.raises(VectorStorageError, match="セキュリティ違反"):
                ChunkData(
                    id=str(uuid.uuid4()),
                    document_id=str(uuid.uuid4()),
                    content=script,
                    filename="test.pdf",
                    page_number=1,
                    embedding=[0.1] * 1536,
                    token_count=10
                )
        
        # スクリプトタグもセキュリティ検証でキャッチされることを確認
        with pytest.raises(VectorStorageError, match="セキュリティ違反"):
            ChunkData(
                id=str(uuid.uuid4()),
                document_id=str(uuid.uuid4()),
                content="<script>alert('XSS')</script>",  # scriptタグもブロックされる
                filename="test.pdf",
                page_number=1,
                embedding=[0.1] * 1536,
                token_count=10
            )
    
    def test_path_traversal_prevention(self):
        """パストラバーサル攻撃の防止テスト"""
        
        malicious_filenames = [
            "../../../etc/passwd",
            "..\\..\\windows\\system32\\config\\sam",
            "/etc/shadow",
            "C:\\Windows\\System32\\drivers\\etc\\hosts",
            "../../../../root/.ssh/id_rsa"
        ]
        
        for filename in malicious_filenames:
            with pytest.raises(VectorStorageError, match="セキュリティ違反"):
                ChunkData(
                    id=str(uuid.uuid4()),
                    document_id=str(uuid.uuid4()),
                    content="正常なコンテンツ",
                    filename=filename,
                    page_number=1,
                    embedding=[0.1] * 1536,
                    token_count=10
                )
    
    def test_dangerous_file_extension_prevention(self):
        """危険な拡張子の防止テスト"""
        
        dangerous_files = [
            "malware.exe",
            "virus.bat",
            "trojan.cmd",
            "backdoor.vbs",
            "exploit.js",
            "payload.jar",
            "shell.sh"
        ]
        
        for filename in dangerous_files:
            with pytest.raises(VectorStorageError, match="セキュリティ違反"):
                ChunkData(
                    id=str(uuid.uuid4()),
                    document_id=str(uuid.uuid4()),
                    content="正常なコンテンツ",
                    filename=filename,
                    page_number=1,
                    embedding=[0.1] * 1536,
                    token_count=10
                )
    
    def test_dos_attack_prevention(self):
        """DoS攻撃の防止テスト"""
        
        # 異常に長いファイル名
        with pytest.raises(VectorStorageError, match="ファイル名が長すぎます"):
            ChunkData(
                id=str(uuid.uuid4()),
                document_id=str(uuid.uuid4()),
                content="正常なコンテンツ",
                filename="x" * 300,  # 255文字制限を超過
                page_number=1,
                embedding=[0.1] * 1536,
                token_count=10
            )
        
        # 異常に長い反復パターン（閾値を下げてテストを簡略化）
        with pytest.raises(VectorStorageError, match="セキュリティ違反"):
            ChunkData(
                id=str(uuid.uuid4()),
                document_id=str(uuid.uuid4()),
                content="A" * 1500,  # 異常な反復パターン (1000+で検出)
                filename="test.pdf",
                page_number=1,
                embedding=[0.1] * 1536,
                token_count=10
            )
        
        # 異常に長いコンテンツ（反復パターンを使わずに異なる文字でテスト）
        long_content = ''.join([chr(65 + (i % 26)) for i in range(15000)])  # A-Zを繰り返し
        with pytest.raises(VectorStorageError, match="コンテンツが長すぎます"):
            ChunkData(
                id=str(uuid.uuid4()),
                document_id=str(uuid.uuid4()),
                content=long_content,  # 10000文字制限を超過
                filename="test.pdf",
                page_number=1,
                embedding=[0.1] * 1536,
                token_count=10
            )
    
    def test_control_character_prevention(self):
        """制御文字の防止テスト"""
        
        # ファイル名に制御文字
        with pytest.raises(VectorStorageError, match="セキュリティ違反"):
            ChunkData(
                id=str(uuid.uuid4()),
                document_id=str(uuid.uuid4()),
                content="正常なコンテンツ",
                filename="test\x00.pdf",  # NULL文字
                page_number=1,
                embedding=[0.1] * 1536,
                token_count=10
            )
        
        # コンテンツに制御文字
        with pytest.raises(VectorStorageError, match="セキュリティ違反"):
            ChunkData(
                id=str(uuid.uuid4()),
                document_id=str(uuid.uuid4()),
                content="悪意のある\x08コンテンツ",  # バックスペース文字
                filename="test.pdf",
                page_number=1,
                embedding=[0.1] * 1536,
                token_count=10
            )
    
    def test_html_escaping(self):
        """HTMLエスケープのテスト"""
        
        html_content = "<div>テストコンテンツ</div>"
        html_filename = "test<script>.pdf"
        html_section = "<section>テストセクション</section>"
        
        chunk = ChunkData(
            id=str(uuid.uuid4()),
            document_id=str(uuid.uuid4()),
            content=html_content,
            filename="test.pdf",  # 正常なファイル名
            page_number=1,
            section_name=html_section,
            embedding=[0.1] * 1536,
            token_count=10
        )
        
        # HTMLがエスケープされることを確認
        result_dict = chunk.to_dict()
        assert "&lt;div&gt;" in result_dict["content"]
        assert "&lt;section&gt;" in result_dict["section_name"]
    
    def test_embedding_vector_security(self):
        """埋め込みベクトルのセキュリティテスト"""
        
        # NaN値の防止
        with pytest.raises(VectorStorageError, match="NaN値"):
            ChunkData(
                id=str(uuid.uuid4()),
                document_id=str(uuid.uuid4()),
                content="正常なコンテンツ",
                filename="test.pdf",
                page_number=1,
                embedding=[float('nan')] * 1536,
                token_count=10
            )
        
        # 無限大値の防止
        with pytest.raises(VectorStorageError, match="無限大値"):
            ChunkData(
                id=str(uuid.uuid4()),
                document_id=str(uuid.uuid4()),
                content="正常なコンテンツ",
                filename="test.pdf",
                page_number=1,
                embedding=[float('inf')] * 1536,
                token_count=10
            )
        
        # ゼロベクトルの防止
        with pytest.raises(VectorStorageError, match="ノルムがゼロ"):
            ChunkData(
                id=str(uuid.uuid4()),
                document_id=str(uuid.uuid4()),
                content="正常なコンテンツ",
                filename="test.pdf",
                page_number=1,
                embedding=[0.0] * 1536,
                token_count=10
            )
        
        # 異常に大きなベクトルの防止
        with pytest.raises(VectorStorageError, match="異常に大きい"):
            ChunkData(
                id=str(uuid.uuid4()),
                document_id=str(uuid.uuid4()),
                content="正常なコンテンツ",
                filename="test.pdf",
                page_number=1,
                embedding=[1000.0] * 1536,  # 異常に大きなノルム
                token_count=10
            )
    
    def test_datetime_serialization_security(self):
        """日時シリアル化のセキュリティテスト"""
        
        # 正常な日時のシリアル化
        normal_datetime = datetime.now()
        chunk = ChunkData(
            id=str(uuid.uuid4()),
            document_id=str(uuid.uuid4()),
            content="正常なコンテンツ",
            filename="test.pdf",
            page_number=1,
            embedding=[0.1] * 1536,
            token_count=10,
            created_at=normal_datetime
        )
        
        result_dict = chunk.to_dict()
        
        # 日時が安全にシリアル化されることを確認
        assert isinstance(result_dict["created_at"], str)
        assert "Z" in result_dict["created_at"]  # UTC形式
        
        # 危険な文字が含まれていないことを確認
        assert "<script>" not in result_dict["created_at"]
        assert "javascript:" not in result_dict["created_at"]
    
    def test_batch_operation_security(self):
        """バッチ操作のセキュリティテスト"""
        
        # 正常なチャンクと異常なチャンクの混在
        chunks = []
        
        # 正常なチャンク
        for i in range(3):
            chunks.append(ChunkData(
                id=str(uuid.uuid4()),
                document_id=str(uuid.uuid4()),
                content=f"正常なコンテンツ {i}",
                filename="test.pdf",
                page_number=i + 1,
                embedding=[0.1 * (i + 1)] * 1536,
                token_count=10
            ))
        
        # セキュリティ違反によりチャンク作成時にエラーが発生することを確認
        with pytest.raises(VectorStorageError):
            ChunkData(
                id=str(uuid.uuid4()),
                document_id=str(uuid.uuid4()),
                content="'; DROP TABLE document_chunks; --",  # SQLインジェクション
                filename="test.pdf",
                page_number=4,
                embedding=[0.1] * 1536,
                token_count=10
            )
        
        # 正常なチャンクのみでバッチ保存
        self.mock_client.table.return_value.insert.return_value.execute.return_value = Mock()
        
        result = self.storage.save_chunks_batch(chunks)
        
        # 正常なチャンクのみが処理されることを確認
        assert result.success_count == 3
        assert result.failure_count == 0
    
    def test_uuid_validation_security(self):
        """UUID検証のセキュリティテスト"""
        
        malicious_ids = [
            "'; DROP TABLE users; --",
            "<script>alert('XSS')</script>",
            "../../../etc/passwd",
            "not-a-valid-uuid",
            "00000000-0000-0000-0000-000000000000; DELETE FROM data;"
        ]
        
        for malicious_id in malicious_ids:
            with pytest.raises(VectorStorageError, match="無効な.*ID形式"):
                ChunkData(
                    id=malicious_id,
                    document_id=str(uuid.uuid4()),
                    content="正常なコンテンツ",
                    filename="test.pdf",
                    page_number=1,
                    embedding=[0.1] * 1536,
                    token_count=10
                )
            
            with pytest.raises(VectorStorageError, match="無効な.*ID形式"):
                ChunkData(
                    id=str(uuid.uuid4()),
                    document_id=malicious_id,
                    content="正常なコンテンツ",
                    filename="test.pdf",
                    page_number=1,
                    embedding=[0.1] * 1536,
                    token_count=10
                )


class TestTransactionSecurity:
    """トランザクションセキュリティテストクラス"""
    
    def setup_method(self):
        """テストセットアップ"""
        self.mock_client = Mock()
        self.storage = VectorStorage("https://test.supabase.co", "test_key", batch_size=50)
        self.storage.client = self.mock_client
    
    def test_transaction_rollback_on_security_violation(self):
        """セキュリティ違反時のトランザクションロールバックテスト"""
        
        # 正常なチャンクを作成
        normal_chunks = [
            ChunkData(
                id=str(uuid.uuid4()),
                document_id=str(uuid.uuid4()),
                content=f"正常なコンテンツ {i}",
                filename="test.pdf",
                page_number=i + 1,
                embedding=[0.1 * (i + 1)] * 1536,
                token_count=10
            )
            for i in range(3)
        ]
        
        # データベースエラーをシミュレート（セキュリティ違反の結果として）
        self.mock_client.table.return_value.insert.return_value.execute.side_effect = Exception("Security violation detected")
        
        # トランザクション付きでバッチ保存
        result = self.storage.save_chunks_batch(normal_chunks, use_transaction=True)
        
        # セキュリティ違反により全件失敗することを確認
        assert result.success_count == 0
        assert result.failure_count == 3
        assert "トランザクションエラー" in result.errors[0]
    
    def test_transaction_vs_non_transaction_security(self):
        """トランザクションありなしでのセキュリティ動作比較テスト"""
        
        normal_chunks = [
            ChunkData(
                id=str(uuid.uuid4()),
                document_id=str(uuid.uuid4()),
                content=f"正常なコンテンツ {i}",
                filename="test.pdf", 
                page_number=i + 1,
                embedding=[0.1 * (i + 1)] * 1536,
                token_count=10
            )
            for i in range(2)
        ]
        
        # 成功ケース
        self.mock_client.table.return_value.insert.return_value.execute.return_value = Mock()
        
        # トランザクションありで実行
        result_with_tx = self.storage.save_chunks_batch(normal_chunks, use_transaction=True)
        assert result_with_tx.success_count == 2
        
        # トランザクションなしで実行  
        result_without_tx = self.storage.save_chunks_batch(normal_chunks, use_transaction=False)
        assert result_without_tx.success_count == 2


if __name__ == "__main__":
    pytest.main([__file__, "-v"])