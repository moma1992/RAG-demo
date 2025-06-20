"""
テキストチャンカーのユニットテスト

spaCyベースの意味的チャンク分割機能のテスト
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from dataclasses import dataclass
from typing import List, Dict, Any, Optional
import uuid

from services.text_chunker import (
    TextChunker, 
    TextChunk, 
    ChunkMetadata, 
    ChunkingError
)


@dataclass
class MockDocument:
    """テスト用のDocumentモック"""
    document_id: str
    filename: str
    pages: List['MockPage']
    metadata: Dict[str, Any]


@dataclass
class MockPage:
    """テスト用のPageモック"""
    page_number: int
    text_blocks: List['MockTextBlock']


@dataclass
class MockTextBlock:
    """テスト用のTextBlockモック"""
    content: str


@dataclass
class MockSection:
    """テスト用のSectionモック"""
    level: int
    title: str
    start_page: int
    end_page: Optional[int] = None


class TestTextChunker:
    """TextChunkerクラステスト"""
    
    @pytest.fixture
    def text_chunker(self):
        """TextChunkerインスタンス"""
        with patch('services.text_chunker.spacy.load'), \
             patch('services.text_chunker.tiktoken.get_encoding'):
            return TextChunker()
    
    @pytest.fixture
    def mock_document(self):
        """テスト用文書"""
        text_block = MockTextBlock(
            content="これは最初の文です。これは2番目の文です。これは3番目の文です。"
                   "これは4番目の文です。これは5番目の文です。"
        )
        page = MockPage(page_number=1, text_blocks=[text_block])
        
        return MockDocument(
            document_id="test-doc-id",
            filename="test.pdf",
            pages=[page],
            metadata={
                "document_structure": Mock(sections=[
                    MockSection(level=1, title="第1章", start_page=1, end_page=2)
                ])
            }
        )
    
    def test_init_default_parameters(self):
        """デフォルトパラメータでの初期化テスト"""
        with patch('services.text_chunker.spacy.load') as mock_spacy, \
             patch('services.text_chunker.tiktoken.get_encoding') as mock_tiktoken:
            
            chunker = TextChunker()
            
            assert chunker.chunk_size == 512
            assert chunker.overlap_size == 51  # 10% of 512
            mock_spacy.assert_called_once_with("ja_core_news_sm")
            mock_tiktoken.assert_called_once_with("cl100k_base")
    
    def test_init_custom_parameters(self):
        """カスタムパラメータでの初期化テスト"""
        with patch('services.text_chunker.spacy.load'), \
             patch('services.text_chunker.tiktoken.get_encoding'):
            
            chunker = TextChunker(chunk_size=256, overlap_ratio=0.2)
            
            assert chunker.chunk_size == 256
            assert chunker.overlap_size == 51  # 20% of 256
    
    @patch('services.text_chunker.spacy.load')
    @patch('services.text_chunker.tiktoken.get_encoding')
    def test_count_tokens(self, mock_tiktoken, mock_spacy):
        """トークン数カウントテスト"""
        # tiktokenエンコーダーのモック設定
        mock_encoder = Mock()
        mock_encoder.encode.return_value = [1, 2, 3, 4, 5]  # 5トークン
        mock_tiktoken.return_value = mock_encoder
        
        chunker = TextChunker()
        
        result = chunker.count_tokens("テストテキスト")
        
        assert result == 5
        mock_encoder.encode.assert_called_once_with("テストテキスト")
    
    @patch('services.text_chunker.spacy.load')
    @patch('services.text_chunker.tiktoken.get_encoding')
    def test_split_text_into_chunks_basic(self, mock_tiktoken, mock_spacy, mock_document):
        """基本的なチャンク分割テスト"""
        # spaCyモックの設定
        mock_nlp = Mock()
        mock_doc = Mock()
        
        # 文境界検出のモック
        mock_sent1 = Mock()
        mock_sent1.text = "これは最初の文です。"
        mock_sent2 = Mock()
        mock_sent2.text = "これは2番目の文です。"
        
        mock_doc.sents = [mock_sent1, mock_sent2]
        mock_nlp.return_value = mock_doc
        mock_spacy.return_value = mock_nlp
        
        # tiktokenモックの設定
        mock_encoder = Mock()
        mock_encoder.encode.return_value = [1, 2, 3, 4, 5]  # 各文5トークン
        mock_tiktoken.return_value = mock_encoder
        
        chunker = TextChunker(chunk_size=10)  # 小さなチャンクサイズ
        
        result = chunker.split_text_into_chunks(mock_document)
        
        assert len(result) > 0
        assert all(isinstance(chunk, TextChunk) for chunk in result)
        assert all(chunk.metadata.filename == "test.pdf" for chunk in result)
        assert all(chunk.metadata.page_number == 1 for chunk in result)
    
    @patch('services.text_chunker.spacy.load')
    @patch('services.text_chunker.tiktoken.get_encoding')
    def test_split_text_into_chunks_with_overlap(self, mock_tiktoken, mock_spacy, mock_document):
        """オーバーラップ付きチャンク分割テスト"""
        # spaCyモックの設定
        mock_nlp = Mock()
        mock_doc = Mock()
        
        # 複数の文を持つモック
        sentences = []
        for i in range(5):
            mock_sent = Mock()
            mock_sent.text = f"これは{i+1}番目の文です。"
            sentences.append(mock_sent)
        
        mock_doc.sents = sentences
        mock_nlp.return_value = mock_doc
        mock_spacy.return_value = mock_nlp
        
        # tiktokenモックの設定（各文5トークン）
        mock_encoder = Mock()
        mock_encoder.encode.return_value = [1, 2, 3, 4, 5]
        mock_tiktoken.return_value = mock_encoder
        
        chunker = TextChunker(chunk_size=15, overlap_ratio=0.2)  # 3文でチャンク
        
        result = chunker.split_text_into_chunks(mock_document)
        
        # 複数のチャンクが生成されることを確認
        assert len(result) >= 2
        
        # オーバーラップが適用されていることを確認（内容が部分的に重複）
        if len(result) >= 2:
            first_chunk_content = result[0].content
            second_chunk_content = result[1].content
            # 2つ目のチャンクには1つ目の内容の一部が含まれる（オーバーラップ）
            assert len(second_chunk_content) > len(first_chunk_content.split("。")[-2] + "。")
    
    @patch('services.text_chunker.spacy.load')
    @patch('services.text_chunker.tiktoken.get_encoding')
    def test_chunk_metadata_generation(self, mock_tiktoken, mock_spacy, mock_document):
        """チャンクメタデータ生成テスト"""
        # spaCyとtiktokenのモック設定
        mock_nlp = Mock()
        mock_doc = Mock()
        
        mock_sent = Mock()
        mock_sent.text = "テストセンテンス。"
        mock_doc.sents = [mock_sent]
        mock_nlp.return_value = mock_doc
        mock_spacy.return_value = mock_nlp
        
        mock_encoder = Mock()
        mock_encoder.encode.return_value = [1, 2, 3]  # 3トークン
        mock_tiktoken.return_value = mock_encoder
        
        chunker = TextChunker()
        
        result = chunker.split_text_into_chunks(mock_document)
        
        assert len(result) > 0
        chunk = result[0]
        
        # メタデータの確認
        assert chunk.metadata.document_id == "test-doc-id"
        assert chunk.metadata.filename == "test.pdf"
        assert chunk.metadata.page_number == 1
        assert chunk.metadata.chapter_number == 1
        assert chunk.metadata.section_name == "第1章"
        assert chunk.metadata.token_count == 3
        assert isinstance(chunk.metadata.start_pos, dict)
        assert isinstance(chunk.metadata.end_pos, dict)
    
    @patch('services.text_chunker.spacy.load')
    @patch('services.text_chunker.tiktoken.get_encoding')
    def test_empty_text_handling(self, mock_tiktoken, mock_spacy):
        """空テキストの処理テスト"""
        # 空のページを持つ文書
        empty_text_block = MockTextBlock(content="")
        empty_page = MockPage(page_number=1, text_blocks=[empty_text_block])
        empty_document = MockDocument(
            document_id="empty-doc",
            filename="empty.pdf",
            pages=[empty_page],
            metadata={}
        )
        
        mock_nlp = Mock()
        mock_doc = Mock()
        mock_doc.sents = []  # 空の文リスト
        mock_nlp.return_value = mock_doc
        mock_spacy.return_value = mock_nlp
        
        mock_encoder = Mock()
        mock_tiktoken.return_value = mock_encoder
        
        chunker = TextChunker()
        
        result = chunker.split_text_into_chunks(empty_document)
        
        # 空のリストまたは空のチャンクが返される
        assert isinstance(result, list)
        if result:  # 空でない場合
            assert all(chunk.content.strip() == "" for chunk in result)
    
    @patch('services.text_chunker.spacy.load')
    @patch('services.text_chunker.tiktoken.get_encoding')
    def test_long_single_sentence_handling(self, mock_tiktoken, mock_spacy):
        """長い単文の処理テスト"""
        long_sentence = "これは" + "非常に長い文章です。" * 100  # 非常に長い文
        
        text_block = MockTextBlock(content=long_sentence)
        page = MockPage(page_number=1, text_blocks=[text_block])
        document = MockDocument(
            document_id="long-doc",
            filename="long.pdf",
            pages=[page],
            metadata={}
        )
        
        # spaCyモック設定
        mock_nlp = Mock()
        mock_doc = Mock()
        mock_sent = Mock()
        mock_sent.text = long_sentence
        mock_doc.sents = [mock_sent]
        mock_nlp.return_value = mock_doc
        mock_spacy.return_value = mock_nlp
        
        # 長い文には多くのトークンがあるとする
        mock_encoder = Mock()
        mock_encoder.encode.return_value = list(range(1000))  # 1000トークン
        mock_tiktoken.return_value = mock_encoder
        
        chunker = TextChunker(chunk_size=512)
        
        result = chunker.split_text_into_chunks(document)
        
        # 長すぎる文でもエラーにならずに処理される
        assert isinstance(result, list)
        if result:
            # トークン制限を超える場合でも適切に処理される
            assert all(isinstance(chunk, TextChunk) for chunk in result)
    
    @patch('services.text_chunker.spacy.load')
    @patch('services.text_chunker.tiktoken.get_encoding')
    def test_processing_error_handling(self, mock_tiktoken, mock_spacy, mock_document):
        """処理エラーハンドリングテスト"""
        # spaCyでエラーが発生する場合
        mock_nlp = Mock()
        mock_nlp.side_effect = Exception("spaCy処理エラー")
        mock_spacy.return_value = mock_nlp
        
        mock_encoder = Mock()
        mock_tiktoken.return_value = mock_encoder
        
        chunker = TextChunker()
        
        with pytest.raises(ChunkingError) as exc_info:
            chunker.split_text_into_chunks(mock_document)
        
        assert "テキストチャンク分割中にエラーが発生しました" in str(exc_info.value)
        assert "spaCy処理エラー" in str(exc_info.value)


class TestTextChunk:
    """TextChunkクラステスト"""
    
    def test_text_chunk_creation(self):
        """TextChunk作成テスト"""
        metadata = ChunkMetadata(
            document_id="test-id",
            filename="test.pdf",
            page_number=1,
            chapter_number=None,
            section_name=None,
            start_pos={"x": 0, "y": 0},
            end_pos={"x": 100, "y": 50},
            token_count=10
        )
        
        chunk = TextChunk(
            content="テストチャンク",
            metadata=metadata
        )
        
        assert chunk.content == "テストチャンク"
        assert chunk.metadata.document_id == "test-id"
        assert chunk.metadata.filename == "test.pdf"
        assert chunk.metadata.token_count == 10
        assert isinstance(chunk.chunk_id, str)
        assert isinstance(chunk.created_at, str)


class TestChunkMetadata:
    """ChunkMetadataクラステスト"""
    
    def test_chunk_metadata_creation(self):
        """ChunkMetadata作成テスト"""
        metadata = ChunkMetadata(
            document_id="doc-123",
            filename="document.pdf",
            page_number=5,
            chapter_number=2,
            section_name="セクション2.1",
            start_pos={"x": 10.5, "y": 20.0},
            end_pos={"x": 200.0, "y": 100.5},
            token_count=256
        )
        
        assert metadata.document_id == "doc-123"
        assert metadata.filename == "document.pdf"
        assert metadata.page_number == 5
        assert metadata.chapter_number == 2
        assert metadata.section_name == "セクション2.1"
        assert metadata.start_pos == {"x": 10.5, "y": 20.0}
        assert metadata.end_pos == {"x": 200.0, "y": 100.5}
        assert metadata.token_count == 256
    
    def test_chunk_metadata_optional_fields(self):
        """ChunkMetadata必須フィールドのみテスト"""
        metadata = ChunkMetadata(
            document_id="doc-456",
            filename="simple.pdf",
            page_number=1,
            chapter_number=None,
            section_name=None,
            start_pos={"x": 0, "y": 0},
            end_pos={"x": 0, "y": 0},
            token_count=50
        )
        
        assert metadata.chapter_number is None
        assert metadata.section_name is None
        assert metadata.token_count == 50


class TestChunkingError:
    """ChunkingErrorクラステスト"""
    
    def test_chunking_error_creation(self):
        """ChunkingError作成テスト"""
        error = ChunkingError("テストエラー")
        
        assert str(error) == "テストエラー"
        assert isinstance(error, Exception)