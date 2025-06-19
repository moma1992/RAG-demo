"""
文書データモデル

文書とチャンクのデータ構造定義
"""

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
from datetime import datetime
import uuid

@dataclass
class DocumentMetadata:
    """文書メタデータ"""
    filename: str
    original_filename: str
    file_size: int
    upload_date: datetime
    total_pages: int
    processing_status: str = "pending"  # pending, processing, completed, failed
    error_message: Optional[str] = None

@dataclass
class ChunkPosition:
    """チャンク位置情報"""
    x: float
    y: float
    width: float
    height: float

@dataclass
class DocumentChunk:
    """文書チャンク"""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    document_id: str = ""
    content: str = ""
    filename: str = ""
    page_number: int = 1
    chapter_number: Optional[int] = None
    section_name: Optional[str] = None
    start_pos: Optional[ChunkPosition] = None
    end_pos: Optional[ChunkPosition] = None
    embedding: Optional[List[float]] = None
    token_count: int = 0
    created_at: datetime = field(default_factory=datetime.now)

@dataclass
class Document:
    """文書モデル"""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    metadata: Optional[DocumentMetadata] = None
    chunks: List[DocumentChunk] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    
    def add_chunk(self, chunk: DocumentChunk) -> None:
        """チャンクを追加"""
        chunk.document_id = self.id
        self.chunks.append(chunk)
        self.updated_at = datetime.now()
    
    def get_total_tokens(self) -> int:
        """総トークン数を取得"""
        return sum(chunk.token_count for chunk in self.chunks)
    
    def get_chunks_by_page(self, page_number: int) -> List[DocumentChunk]:
        """指定ページのチャンクを取得"""
        return [chunk for chunk in self.chunks if chunk.page_number == page_number]

@dataclass
class SearchQuery:
    """検索クエリ"""
    query: str
    top_k: int = 5
    similarity_threshold: float = 0.7
    filter_by_filename: Optional[str] = None
    filter_by_page: Optional[int] = None

@dataclass
class SearchResult:
    """検索結果"""
    chunk: DocumentChunk
    similarity_score: float
    rank: int

@dataclass
class SearchResponse:
    """検索レスポンス"""
    query: str
    results: List[SearchResult]
    total_results: int
    search_time: float
    embedding_time: float