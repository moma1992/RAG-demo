"""
テストユーティリティとヘルパー関数

共通のテスト用関数とヘルパークラス
"""

import tempfile
import json
from pathlib import Path
from typing import List, Dict, Any, Optional
from unittest.mock import Mock


class MockPDFGenerator:
    """テスト用PDF生成ヘルパー"""
    
    @staticmethod
    def create_simple_pdf_bytes(content: str = "テストコンテンツ") -> bytes:
        """シンプルなPDFバイトデータを生成"""
        return f"%PDF-1.4\n{content}\n%%EOF".encode()
    
    @staticmethod
    def create_multi_page_pdf_bytes(page_contents: List[str]) -> bytes:
        """複数ページのPDFバイトデータを生成"""
        content = "\n".join(page_contents)
        return f"%PDF-1.4\n{content}\n%%EOF".encode()
    
    @staticmethod
    def create_large_pdf_bytes(size_mb: float = 1.0) -> bytes:
        """指定サイズの大きなPDFバイトデータを生成"""
        content_size = int(size_mb * 1024 * 1024)  # MB to bytes
        content = "A" * content_size
        return f"%PDF-1.4\n{content}\n%%EOF".encode()


class MockDataFactory:
    """テストデータ生成ファクトリー"""
    
    @staticmethod
    def create_document_chunk(
        content: str = "テストチャンク",
        filename: str = "test.pdf",
        page_number: int = 1,
        **kwargs
    ) -> Dict[str, Any]:
        """DocumentChunk用のテストデータを生成"""
        base_data = {
            "content": content,
            "filename": filename,
            "page_number": page_number,
            "token_count": len(content.split()),
            "chapter_number": None,
            "section_name": None,
            "start_pos": None,
            "end_pos": None,
            "embedding": None
        }
        base_data.update(kwargs)
        return base_data
    
    @staticmethod
    def create_search_result(
        content: str = "検索結果",
        similarity_score: float = 0.85,
        **kwargs
    ) -> Dict[str, Any]:
        """SearchResult用のテストデータを生成"""
        base_data = {
            "content": content,
            "filename": "test.pdf",
            "page_number": 1,
            "similarity_score": similarity_score,
            "metadata": {}
        }
        base_data.update(kwargs)
        return base_data
    
    @staticmethod
    def create_embedding_vector(dimension: int = 1536) -> List[float]:
        """テスト用埋め込みベクトルを生成"""
        return [0.1 + i * 0.001 for i in range(dimension)]


class TestFileManager:
    """テスト用ファイル管理ヘルパー"""
    
    def __init__(self):
        self.temp_files: List[Path] = []
        self.temp_dirs: List[Path] = []
    
    def create_temp_file(
        self, 
        content: str, 
        suffix: str = ".txt", 
        prefix: str = "test_"
    ) -> Path:
        """一時ファイルを作成"""
        temp_file = tempfile.NamedTemporaryFile(
            mode='w', 
            suffix=suffix, 
            prefix=prefix, 
            delete=False
        )
        temp_file.write(content)
        temp_file.close()
        
        temp_path = Path(temp_file.name)
        self.temp_files.append(temp_path)
        return temp_path
    
    def create_temp_pdf_file(self, content: str = "テストPDF") -> Path:
        """一時PDFファイルを作成"""
        pdf_content = MockPDFGenerator.create_simple_pdf_bytes(content)
        temp_file = tempfile.NamedTemporaryFile(
            mode='wb', 
            suffix='.pdf', 
            prefix='test_pdf_', 
            delete=False
        )
        temp_file.write(pdf_content)
        temp_file.close()
        
        temp_path = Path(temp_file.name)
        self.temp_files.append(temp_path)
        return temp_path
    
    def create_temp_dir(self) -> Path:
        """一時ディレクトリを作成"""
        temp_dir = Path(tempfile.mkdtemp(prefix="test_dir_"))
        self.temp_dirs.append(temp_dir)
        return temp_dir
    
    def cleanup(self):
        """一時ファイル・ディレクトリを削除"""
        for temp_file in self.temp_files:
            if temp_file.exists():
                temp_file.unlink()
        
        for temp_dir in self.temp_dirs:
            if temp_dir.exists():
                import shutil
                shutil.rmtree(temp_dir)
        
        self.temp_files.clear()
        self.temp_dirs.clear()


class AssertionHelpers:
    """テスト用アサーションヘルパー"""
    
    @staticmethod
    def assert_valid_uuid(uuid_string: str):
        """UUID形式の検証"""
        import uuid
        try:
            uuid.UUID(uuid_string)
        except ValueError:
            raise AssertionError(f"Invalid UUID format: {uuid_string}")
    
    @staticmethod
    def assert_valid_embedding(embedding: List[float], expected_dimension: int = 1536):
        """埋め込みベクトルの検証"""
        assert isinstance(embedding, list), "埋め込みはリスト形式である必要があります"
        assert len(embedding) == expected_dimension, f"埋め込みの次元数は{expected_dimension}である必要があります"
        assert all(isinstance(val, (int, float)) for val in embedding), "埋め込みの値は数値である必要があります"
    
    @staticmethod
    def assert_japanese_text(text: str):
        """日本語テキストの検証"""
        import re
        japanese_pattern = re.compile(r'[ひらがなカタカナ漢字]')
        assert japanese_pattern.search(text), "日本語文字が含まれている必要があります"
    
    @staticmethod
    def assert_processing_time_reasonable(processing_time: float, max_seconds: float = 30.0):
        """処理時間の妥当性検証"""
        assert processing_time >= 0, "処理時間は0以上である必要があります"
        assert processing_time <= max_seconds, f"処理時間は{max_seconds}秒以内である必要があります"


class MockResponseBuilder:
    """モックレスポンス構築ヘルパー"""
    
    @staticmethod
    def build_openai_embedding_response(embeddings: List[List[float]]):
        """OpenAI埋め込みAPIレスポンスを構築"""
        data = []
        for i, embedding in enumerate(embeddings):
            data.append(Mock(embedding=embedding, index=i))
        
        return Mock(data=data)
    
    @staticmethod
    def build_claude_response(text: str):
        """Claude APIレスポンスを構築"""
        return Mock(content=[Mock(text=text)])
    
    @staticmethod
    def build_supabase_response(data: List[Dict[str, Any]]):
        """Supabaseレスポンスを構築"""
        return Mock(data=data)


class TestConfigManager:
    """テスト設定管理ヘルパー"""
    
    DEFAULT_CONFIG = {
        "chunk_size": 512,
        "chunk_overlap": 0.1,
        "max_file_size_mb": 50,
        "search_top_k": 5,
        "similarity_threshold": 0.7,
        "openai_model": "text-embedding-3-small",
        "claude_model": "claude-3-sonnet-20240229"
    }
    
    @classmethod
    def get_test_config(cls, overrides: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """テスト用設定を取得"""
        config = cls.DEFAULT_CONFIG.copy()
        if overrides:
            config.update(overrides)
        return config
    
    @classmethod
    def create_config_file(cls, config: Dict[str, Any], file_path: Path):
        """設定ファイルを作成"""
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(config, f, ensure_ascii=False, indent=2)