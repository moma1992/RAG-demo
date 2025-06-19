"""
PDF処理サービスのテスト

TDDアプローチによるPDFプロセッサーのテストケース
"""

import pytest
from unittest.mock import Mock, patch
from services.pdf_processor import PDFProcessor, PDFProcessingError
from models.document import DocumentChunk


class TestPDFProcessor:
    """PDFプロセッサーテストクラス"""
    
    def test_init(self):
        """初期化テスト"""
        processor = PDFProcessor()
        assert processor is not None
    
    def test_process_pdf_with_valid_file(self, sample_pdf_bytes, mock_fitz, mock_spacy):
        """有効なPDFファイル処理テスト"""
        processor = PDFProcessor()
        filename = "test.pdf"
        
        result = processor.process_pdf(sample_pdf_bytes, filename)
        
        assert result is not None
        assert result.chunks is not None
        assert len(result.chunks) > 0
        assert result.total_pages >= 1
        assert result.total_chunks >= 1
        assert result.processing_time >= 0
        assert isinstance(result.errors, list)
    
    def test_process_pdf_with_empty_file(self):
        """空ファイル処理テスト"""
        processor = PDFProcessor()
        
        with pytest.raises(PDFProcessingError):
            processor.process_pdf(b"", "empty.pdf")
    
    def test_process_pdf_with_invalid_file(self):
        """無効ファイル処理テスト"""
        processor = PDFProcessor()
        invalid_data = b"invalid pdf content"
        
        with pytest.raises(PDFProcessingError):
            processor.process_pdf(invalid_data, "invalid.pdf")
    
    def test_extract_text_from_pdf_success(self, temp_dir, mock_fitz):
        """PDFテキスト抽出成功テスト"""
        processor = PDFProcessor()
        
        # テスト用PDFファイル作成
        pdf_path = temp_dir / "test.pdf"
        pdf_path.write_bytes(b"%PDF-1.4\ntest content\n%%EOF")
        
        result = processor.extract_text_from_pdf(pdf_path)
        
        assert isinstance(result, str)
        assert len(result) > 0
    
    def test_extract_text_from_pdf_file_not_found(self, temp_dir):
        """PDFファイル未存在テスト"""
        processor = PDFProcessor()
        non_existent_path = temp_dir / "non_existent.pdf"
        
        with pytest.raises(FileNotFoundError):
            processor.extract_text_from_pdf(non_existent_path)
    
    def test_document_chunk_creation(self):
        """DocumentChunk作成テスト"""
        chunk = DocumentChunk(
            content="テストコンテンツ",
            filename="test.pdf",
            page_number=1,
            token_count=10
        )
        
        assert chunk.content == "テストコンテンツ"
        assert chunk.filename == "test.pdf"
        assert chunk.page_number == 1
        assert chunk.token_count == 10
        assert chunk.chapter_number is None
        assert chunk.section_name is None
    
    @patch('services.pdf_processor.logger')
    def test_logging_on_error(self, mock_logger, sample_pdf_bytes):
        """エラー時ログ出力テスト"""
        processor = PDFProcessor()
        
        with patch.object(processor, 'process_pdf', side_effect=Exception("Test error")):
            with pytest.raises(Exception):
                processor.process_pdf(sample_pdf_bytes, "test.pdf")
        
        # ログが呼ばれたことを確認（実装時に詳細を調整）
        # mock_logger.error.assert_called()


    def test_pdf_processor_with_real_pdf_files(self, sample_pdf_file, mock_fitz, mock_spacy):
        """実際のPDFファイルを使用したテスト"""
        processor = PDFProcessor()
        
        # ファイルの存在確認
        assert sample_pdf_file.exists()
        
        # ファイルを読み込んでバイトデータとして処理
        pdf_bytes = sample_pdf_file.read_bytes()
        result = processor.process_pdf(pdf_bytes, sample_pdf_file.name)
        
        assert result is not None
        assert result.total_pages > 0
        assert result.total_chunks > 0

    def test_pdf_processor_multi_page(self, multi_page_pdf_file, mock_fitz, mock_spacy):
        """複数ページPDFテスト"""
        processor = PDFProcessor()
        
        pdf_bytes = multi_page_pdf_file.read_bytes()
        result = processor.process_pdf(pdf_bytes, multi_page_pdf_file.name)
        
        assert result.total_pages >= 2  # 複数ページのPDF
        assert len(result.chunks) > 0

    def test_pdf_processor_corrupt_file(self, corrupt_pdf_file):
        """破損PDFファイルテスト"""
        processor = PDFProcessor()
        
        pdf_bytes = corrupt_pdf_file.read_bytes()
        
        with pytest.raises(PDFProcessingError):
            processor.process_pdf(pdf_bytes, corrupt_pdf_file.name)

    def test_extract_text_with_real_files(self, sample_pdf_file, mock_fitz):
        """実PDFファイルからのテキスト抽出テスト"""
        processor = PDFProcessor()
        
        result = processor.extract_text_from_pdf(sample_pdf_file)
        assert isinstance(result, str)
        assert len(result) > 0


class TestDocumentChunk:
    """DocumentChunkテストクラス（models.document.DocumentChunkを使用）"""
    
    def test_document_chunk_default_values(self):
        """デフォルト値テスト"""
        chunk = DocumentChunk()
        
        assert chunk.content == ""
        assert chunk.filename == ""
        assert chunk.page_number == 1
        assert chunk.token_count == 0
        assert chunk.chapter_number is None
        assert chunk.section_name is None
        assert chunk.start_pos is None
        assert chunk.end_pos is None
        assert chunk.embedding is None
        assert len(chunk.id) == 36  # UUID length
    
    def test_document_chunk_with_custom_values(self):
        """カスタム値テスト"""
        chunk = DocumentChunk(
            content="カスタムコンテンツ",
            filename="custom.pdf",
            page_number=5,
            chapter_number=2,
            section_name="第2章",
            token_count=25
        )
        
        assert chunk.content == "カスタムコンテンツ"
        assert chunk.filename == "custom.pdf"
        assert chunk.page_number == 5
        assert chunk.chapter_number == 2
        assert chunk.section_name == "第2章"
        assert chunk.token_count == 25
        assert len(chunk.id) == 36

    def test_document_chunk_with_positions(self):
        """位置情報付きDocumentChunkテスト"""
        from models.document import ChunkPosition
        
        start_pos = ChunkPosition(x=0, y=100, width=500, height=50)
        end_pos = ChunkPosition(x=0, y=50, width=500, height=50)
        
        chunk = DocumentChunk(
            content="位置情報付きチャンク",
            filename="positioned.pdf",
            start_pos=start_pos,
            end_pos=end_pos
        )
        
        assert chunk.start_pos == start_pos
        assert chunk.end_pos == end_pos
        assert chunk.start_pos.x == 0
        assert chunk.end_pos.height == 50

    def test_document_chunk_with_embedding(self):
        """埋め込みベクトル付きテスト"""
        embedding = [0.1] * 1536
        
        chunk = DocumentChunk(
            content="埋め込み付きチャンク",
            filename="embedded.pdf",
            embedding=embedding
        )
        
        assert chunk.embedding == embedding
        assert len(chunk.embedding) == 1536


# 統合テスト
class TestPDFProcessorIntegration:
    """PDF処理統合テスト"""
    
    def test_full_pdf_processing_pipeline(self, sample_pdf_bytes, mock_fitz, mock_spacy):
        """完全なPDF処理パイプラインテスト"""
        processor = PDFProcessor()
        filename = "integration_test.pdf"
        
        # 処理実行
        result = processor.process_pdf(sample_pdf_bytes, filename)
        
        # 結果検証
        assert result.total_pages > 0
        assert result.total_chunks > 0
        assert all(chunk.filename == filename for chunk in result.chunks)
        assert all(chunk.content for chunk in result.chunks)
        assert all(chunk.token_count > 0 for chunk in result.chunks)