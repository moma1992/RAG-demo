"""
データモデルテスト

Document, DocumentChunk, その他データクラスのテストケース
"""

import pytest
from datetime import datetime
from models.document import (
    Document,
    DocumentChunk,
    DocumentMetadata,
    ChunkPosition,
    SearchQuery,
    SearchResult,
    SearchResponse
)
import uuid


class TestDocumentMetadata:
    """DocumentMetadataテストクラス"""

    def test_document_metadata_creation(self):
        """DocumentMetadata作成テスト"""
        upload_date = datetime.now()
        
        metadata = DocumentMetadata(
            filename="test.pdf",
            original_filename="テスト文書.pdf",
            file_size=1024000,
            upload_date=upload_date,
            total_pages=25,
            processing_status="completed"
        )
        
        assert metadata.filename == "test.pdf"
        assert metadata.original_filename == "テスト文書.pdf"
        assert metadata.file_size == 1024000
        assert metadata.upload_date == upload_date
        assert metadata.total_pages == 25
        assert metadata.processing_status == "completed"
        assert metadata.error_message is None

    def test_document_metadata_default_status(self):
        """DocumentMetadataデフォルトステータステスト"""
        metadata = DocumentMetadata(
            filename="test.pdf",
            original_filename="test.pdf",
            file_size=1024,
            upload_date=datetime.now(),
            total_pages=1
        )
        
        assert metadata.processing_status == "pending"
        assert metadata.error_message is None

    def test_document_metadata_with_error(self):
        """DocumentMetadataエラー情報テスト"""
        metadata = DocumentMetadata(
            filename="error.pdf",
            original_filename="error.pdf",
            file_size=0,
            upload_date=datetime.now(),
            total_pages=0,
            processing_status="failed",
            error_message="PDFファイルが破損しています"
        )
        
        assert metadata.processing_status == "failed"
        assert metadata.error_message == "PDFファイルが破損しています"


class TestChunkPosition:
    """ChunkPositionテストクラス"""

    def test_chunk_position_creation(self):
        """ChunkPosition作成テスト"""
        position = ChunkPosition(
            x=100.5,
            y=200.0,
            width=300.25,
            height=50.75
        )
        
        assert position.x == 100.5
        assert position.y == 200.0
        assert position.width == 300.25
        assert position.height == 50.75

    def test_chunk_position_zero_values(self):
        """ChunkPositionゼロ値テスト"""
        position = ChunkPosition(x=0, y=0, width=0, height=0)
        
        assert position.x == 0
        assert position.y == 0
        assert position.width == 0
        assert position.height == 0


class TestDocumentChunk:
    """DocumentChunkテストクラス"""

    def test_document_chunk_creation(self):
        """DocumentChunk作成テスト"""
        chunk_id = str(uuid.uuid4())
        document_id = str(uuid.uuid4())
        start_pos = ChunkPosition(x=0, y=100, width=500, height=50)
        end_pos = ChunkPosition(x=0, y=50, width=500, height=50)
        
        chunk = DocumentChunk(
            id=chunk_id,
            document_id=document_id,
            content="これはテストチャンクです。",
            filename="test.pdf",
            page_number=1,
            chapter_number=1,
            section_name="第1章",
            start_pos=start_pos,
            end_pos=end_pos,
            embedding=[0.1] * 1536,
            token_count=25
        )
        
        assert chunk.id == chunk_id
        assert chunk.document_id == document_id
        assert chunk.content == "これはテストチャンクです。"
        assert chunk.filename == "test.pdf"
        assert chunk.page_number == 1
        assert chunk.chapter_number == 1
        assert chunk.section_name == "第1章"
        assert chunk.start_pos == start_pos
        assert chunk.end_pos == end_pos
        assert len(chunk.embedding) == 1536
        assert chunk.token_count == 25
        assert isinstance(chunk.created_at, datetime)

    def test_document_chunk_defaults(self):
        """DocumentChunkデフォルト値テスト"""
        chunk = DocumentChunk()
        
        assert len(chunk.id) == 36  # UUID length
        assert chunk.document_id == ""
        assert chunk.content == ""
        assert chunk.filename == ""
        assert chunk.page_number == 1
        assert chunk.chapter_number is None
        assert chunk.section_name is None
        assert chunk.start_pos is None
        assert chunk.end_pos is None
        assert chunk.embedding is None
        assert chunk.token_count == 0
        assert isinstance(chunk.created_at, datetime)

    def test_document_chunk_minimal(self):
        """DocumentChunk最小構成テスト"""
        chunk = DocumentChunk(
            content="最小チャンク",
            filename="minimal.pdf"
        )
        
        assert chunk.content == "最小チャンク"
        assert chunk.filename == "minimal.pdf"
        assert len(chunk.id) == 36


class TestDocument:
    """Documentテストクラス"""

    def test_document_creation(self):
        """Document作成テスト"""
        document_id = str(uuid.uuid4())
        metadata = DocumentMetadata(
            filename="test.pdf",
            original_filename="テスト.pdf",
            file_size=1024,
            upload_date=datetime.now(),
            total_pages=5
        )
        
        document = Document(
            id=document_id,
            metadata=metadata
        )
        
        assert document.id == document_id
        assert document.metadata == metadata
        assert document.chunks == []
        assert isinstance(document.created_at, datetime)
        assert isinstance(document.updated_at, datetime)

    def test_document_defaults(self):
        """Documentデフォルト値テスト"""
        document = Document()
        
        assert len(document.id) == 36
        assert document.metadata is None
        assert document.chunks == []
        assert isinstance(document.created_at, datetime)
        assert isinstance(document.updated_at, datetime)

    def test_document_add_chunk(self):
        """Document add_chunkテスト"""
        document = Document()
        chunk = DocumentChunk(
            content="テストチャンク",
            filename="test.pdf"
        )
        
        original_updated_at = document.updated_at
        document.add_chunk(chunk)
        
        assert len(document.chunks) == 1
        assert document.chunks[0] == chunk
        assert chunk.document_id == document.id
        assert document.updated_at > original_updated_at

    def test_document_get_total_tokens(self):
        """Document get_total_tokensテスト"""
        document = Document()
        
        chunk1 = DocumentChunk(content="チャンク1", token_count=10)
        chunk2 = DocumentChunk(content="チャンク2", token_count=15)
        chunk3 = DocumentChunk(content="チャンク3", token_count=20)
        
        document.add_chunk(chunk1)
        document.add_chunk(chunk2)
        document.add_chunk(chunk3)
        
        assert document.get_total_tokens() == 45

    def test_document_get_chunks_by_page(self):
        """Document get_chunks_by_pageテスト"""
        document = Document()
        
        chunk1 = DocumentChunk(content="ページ1-1", page_number=1)
        chunk2 = DocumentChunk(content="ページ1-2", page_number=1)
        chunk3 = DocumentChunk(content="ページ2-1", page_number=2)
        
        document.add_chunk(chunk1)
        document.add_chunk(chunk2)
        document.add_chunk(chunk3)
        
        page1_chunks = document.get_chunks_by_page(1)
        page2_chunks = document.get_chunks_by_page(2)
        page3_chunks = document.get_chunks_by_page(3)
        
        assert len(page1_chunks) == 2
        assert len(page2_chunks) == 1
        assert len(page3_chunks) == 0
        assert chunk1 in page1_chunks
        assert chunk2 in page1_chunks
        assert chunk3 in page2_chunks


class TestSearchQuery:
    """SearchQueryテストクラス"""

    def test_search_query_creation(self):
        """SearchQuery作成テスト"""
        query = SearchQuery(
            query="新入社員研修",
            top_k=10,
            similarity_threshold=0.8,
            filter_by_filename="training.pdf",
            filter_by_page=1
        )
        
        assert query.query == "新入社員研修"
        assert query.top_k == 10
        assert query.similarity_threshold == 0.8
        assert query.filter_by_filename == "training.pdf"
        assert query.filter_by_page == 1

    def test_search_query_defaults(self):
        """SearchQueryデフォルト値テスト"""
        query = SearchQuery(query="テストクエリ")
        
        assert query.query == "テストクエリ"
        assert query.top_k == 5
        assert query.similarity_threshold == 0.7
        assert query.filter_by_filename is None
        assert query.filter_by_page is None


class TestSearchResult:
    """SearchResultテストクラス"""

    def test_search_result_creation(self):
        """SearchResult作成テスト"""
        chunk = DocumentChunk(
            content="検索結果チャンク",
            filename="result.pdf"
        )
        
        result = SearchResult(
            chunk=chunk,
            similarity_score=0.95,
            rank=1
        )
        
        assert result.chunk == chunk
        assert result.similarity_score == 0.95
        assert result.rank == 1


class TestSearchResponse:
    """SearchResponseテストクラス"""

    def test_search_response_creation(self):
        """SearchResponse作成テスト"""
        chunk = DocumentChunk(content="レスポンスチャンク")
        result = SearchResult(chunk=chunk, similarity_score=0.9, rank=1)
        
        response = SearchResponse(
            query="テストクエリ",
            results=[result],
            total_results=1,
            search_time=0.15,
            embedding_time=0.05
        )
        
        assert response.query == "テストクエリ"
        assert len(response.results) == 1
        assert response.results[0] == result
        assert response.total_results == 1
        assert response.search_time == 0.15
        assert response.embedding_time == 0.05


# 統合テスト
class TestDataModelsIntegration:
    """データモデル統合テスト"""

    def test_full_document_workflow(self):
        """完全文書ワークフロー統合テスト"""
        # 1. メタデータ作成
        metadata = DocumentMetadata(
            filename="integration_test.pdf",
            original_filename="統合テスト.pdf",
            file_size=2048000,
            upload_date=datetime.now(),
            total_pages=10,
            processing_status="completed"
        )
        
        # 2. 文書作成
        document = Document(metadata=metadata)
        
        # 3. チャンク作成・追加
        for i in range(5):
            chunk = DocumentChunk(
                content=f"統合テストチャンク{i+1}",
                filename="integration_test.pdf",
                page_number=(i % 3) + 1,
                chapter_number=1,
                section_name="統合テスト章",
                token_count=20 + i * 5,
                embedding=[0.1 + i * 0.01] * 1536
            )
            document.add_chunk(chunk)
        
        # 4. 検証
        assert document.metadata.processing_status == "completed"
        assert len(document.chunks) == 5
        assert document.get_total_tokens() == 110  # 20+25+30+35+40
        assert len(document.get_chunks_by_page(1)) == 2
        assert len(document.get_chunks_by_page(2)) == 2
        assert len(document.get_chunks_by_page(3)) == 1
        
        # 5. 検索クエリ・結果テスト
        query = SearchQuery(
            query="統合テスト",
            top_k=3,
            filter_by_filename="integration_test.pdf"
        )
        
        search_results = [
            SearchResult(chunk=document.chunks[0], similarity_score=0.95, rank=1),
            SearchResult(chunk=document.chunks[1], similarity_score=0.88, rank=2)
        ]
        
        response = SearchResponse(
            query=query.query,
            results=search_results,
            total_results=2,
            search_time=0.25,
            embedding_time=0.08
        )
        
        assert response.query == "統合テスト"
        assert len(response.results) == 2
        assert response.results[0].similarity_score > response.results[1].similarity_score