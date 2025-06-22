"""
PDF処理サービス

PyMuPDF + spaCyを使用したPDF文書処理機能
"""

from typing import List, Dict, Any, Optional, Tuple
import logging
from pathlib import Path
from dataclasses import dataclass, field
import fitz  # PyMuPDF
import spacy
import time
import uuid
from datetime import datetime
import io

logger = logging.getLogger(__name__)

@dataclass
class TextBlock:
    """テキストブロックデータクラス"""
    content: str
    bbox: Dict[str, float]  # {"x0": 0, "y0": 0, "x1": 100, "y1": 20}
    font_size: float
    font_name: str
    
@dataclass
class Page:
    """ページデータクラス"""
    page_number: int
    text_blocks: List[TextBlock]
    page_size: Dict[str, int]  # {"width": 595, "height": 842}
    
@dataclass
class Document:
    """文書データクラス"""
    filename: str
    pages: List[Page]
    metadata: Optional[Dict[str, Any]] = None
    total_pages: Optional[int] = None
    original_filename: Optional[str] = None
    processing_status: str = "processing"
    document_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())

@dataclass
class DocumentChunk:
    """文書チャンクデータクラス"""
    content: str
    filename: str
    page_number: int
    chapter_number: Optional[int] = None
    section_name: Optional[str] = None
    start_pos: Optional[Dict[str, float]] = None
    end_pos: Optional[Dict[str, float]] = None
    token_count: Optional[int] = None

@dataclass
class ProcessingResult:
    """PDF処理結果データクラス"""
    chunks: List[DocumentChunk]
    total_pages: int
    total_chunks: int
    processing_time: float
    errors: List[str]

class PDFProcessor:
    """PDF処理メインクラス"""
    
    def __init__(self) -> None:
        """初期化"""
        logger.info("PDFProcessor初期化中")
        try:
            # spaCy日本語モデルの初期化
            self.nlp = spacy.load("ja_core_news_sm")
            logger.info("spaCy日本語モデル初期化完了")
        except OSError:
            try:
                logger.warning("spaCy日本語モデルが見つかりません。英語モデルを使用します。")
                self.nlp = spacy.load("en_core_web_sm")
            except OSError:
                logger.warning("spaCyモデルが見つかりません。ブランクモデルを使用します。")
                self.nlp = spacy.blank("ja")
        
        self.logger = logger
    
    def process_pdf(self, pdf_bytes: bytes, filename: str) -> ProcessingResult:
        """
        PDFファイルを処理してチャンクに分割
        
        Args:
            pdf_bytes: PDFファイルのバイトデータ
            filename: ファイル名
            
        Returns:
            ProcessingResult: 処理結果
            
        Raises:
            PDFProcessingError: PDF処理エラーの場合
        """
        logger.info(f"PDF処理開始: {filename}")
        
        # 空ファイルチェック
        if not pdf_bytes or len(pdf_bytes) == 0:
            raise PDFProcessingError("PDFファイルが空です")
        
        # 無効PDFファイルチェック（PDFヘッダーの確認）
        if not pdf_bytes.startswith(b'%PDF-'):
            raise PDFProcessingError("無効なPDFファイルです")
        
        try:
            # TODO: 実装
            # 1. PyMuPDFでPDF読み込み
            # 2. spaCyで文書構造解析
            # 3. チャンク分割
            # 4. メタデータ抽出
            
            # 現在はダミーデータを返す
            dummy_chunk = DocumentChunk(
                content="サンプルテキストです。",
                filename=filename,
                page_number=1,
                token_count=10
            )
            
            # バイトデータから一時ファイルを作成してDocument形式で処理
            with io.BytesIO(pdf_bytes) as pdf_stream:
                # PyMuPDFでバイトデータを直接処理
                pdf_doc = fitz.open(stream=pdf_stream, filetype="pdf")
                
                # 基本メタデータを取得
                metadata = self._extract_metadata(pdf_doc)
                
                # ページごとにテキストを抽出
                pages = []
                for page_num in range(pdf_doc.page_count):
                    page = self._extract_page_text(pdf_doc[page_num], page_num + 1)
                    pages.append(page)
                
                # Documentを作成
                document = Document(
                    filename=filename,
                    original_filename=filename,
                    total_pages=pdf_doc.page_count,
                    pages=pages,
                    metadata=metadata,
                    processing_status="completed"
                )
                
                pdf_doc.close()
                
                # DocumentからDocumentChunkを作成
                chunks = self._convert_document_to_chunks(document)
                
                return ProcessingResult(
                    chunks=chunks,
                    total_pages=document.total_pages,
                    total_chunks=len(chunks),
                    processing_time=0.1,
                    errors=[]
                )
            
        except Exception as e:
            logger.error(f"PDF処理エラー: {str(e)}", exc_info=True)
            raise PDFProcessingError(f"PDFの処理中にエラーが発生しました: {str(e)}") from e
    
    def extract_text_from_pdf(self, pdf_path: Path) -> Document:
        """
        PDFからテキストを抽出してDocument形式で返す
        
        Args:
            pdf_path: PDFファイルのパス
            
        Returns:
            Document: 抽出されたテキストとメタデータ
            
        Raises:
            FileNotFoundError: ファイルが存在しない場合
            PDFProcessingError: PDF処理エラーの場合
        """
        if not pdf_path.exists():
            raise FileNotFoundError(f"PDFファイルが見つかりません: {pdf_path}")
        
        logger.info(f"PDF処理開始: {pdf_path}")
        
        try:
            # PDF文書を開く
            pdf_doc = fitz.open(pdf_path)
            
            # 基本メタデータを取得
            metadata = self._extract_metadata(pdf_doc)
            
            # ページごとにテキストを抽出
            pages = []
            for page_num in range(pdf_doc.page_count):
                page = self._extract_page_text(pdf_doc[page_num], page_num + 1)
                pages.append(page)
            
            # Document作成
            document = Document(
                filename=pdf_path.stem,
                original_filename=pdf_path.name,
                total_pages=pdf_doc.page_count,
                pages=pages,
                metadata=metadata,
                processing_status="completed"
            )
            
            pdf_doc.close()
            logger.info(f"PDF処理完了: {pdf_path.name}, {pdf_doc.page_count}ページ")
            return document
            
        except Exception as e:
            logger.error(f"PDF処理エラー: {str(e)}", exc_info=True)
            raise PDFProcessingError(f"PDF処理中にエラーが発生しました: {str(e)}") from e

    def _extract_metadata(self, pdf_doc: fitz.Document) -> Dict[str, Any]:
        """PDFメタデータを抽出"""
        metadata = pdf_doc.metadata or {}
        return {
            "title": metadata.get("title", ""),
            "author": metadata.get("author", ""),
            "subject": metadata.get("subject", ""), 
            "creator": metadata.get("creator", ""),
            "producer": metadata.get("producer", ""),
            "creation_date": metadata.get("creationDate", ""),
            "modification_date": metadata.get("modDate", ""),
            "page_count": pdf_doc.page_count
        }
    
    def _extract_page_text(self, page: fitz.Page, page_number: int) -> Page:
        """ページからテキストブロックを抽出"""
        # ページサイズを取得
        page_rect = page.rect
        page_size = {"width": page_rect.width, "height": page_rect.height}
        
        # テキストブロックを取得
        text_blocks = []
        
        try:
            # 詳細なテキスト情報を取得（フォント情報含む）
            blocks = page.get_text("dict")["blocks"]
            
            for block in blocks:
                if "lines" in block:  # テキストブロックの場合
                    for line in block["lines"]:
                        for span in line["spans"]:
                            if span["text"].strip():  # 空でないテキスト
                                text_block = TextBlock(
                                    content=span["text"],
                                    bbox={
                                        "x0": span["bbox"][0],
                                        "y0": span["bbox"][1], 
                                        "x1": span["bbox"][2],
                                        "y1": span["bbox"][3]
                                    },
                                    font_size=span["size"],
                                    font_name=span["font"]
                                )
                                text_blocks.append(text_block)
        except Exception as e:
            logger.warning(f"ページ{page_number}のテキスト抽出でエラー: {str(e)}")
            # フォールバック: シンプルなテキスト抽出
            simple_text = page.get_text()
            if simple_text.strip():
                text_block = TextBlock(
                    content=simple_text,
                    bbox={"x0": 0, "y0": 0, "x1": page_rect.width, "y1": page_rect.height},
                    font_size=12.0,
                    font_name="unknown"
                )
                text_blocks.append(text_block)
        
        return Page(
            page_number=page_number,
            text_blocks=text_blocks,
            page_size=page_size
        )
    
    def _convert_document_to_chunks(self, document: Document) -> List[DocumentChunk]:
        """DocumentからDocumentChunkのリストを作成"""
        chunks = []
        
        for page in document.pages:
            for i, text_block in enumerate(page.text_blocks):
                if text_block.content.strip():  # 空でないテキストのみ
                    chunk = DocumentChunk(
                        content=text_block.content,
                        filename=document.filename,
                        page_number=page.page_number,
                        start_pos={"x": text_block.bbox["x0"], "y": text_block.bbox["y0"]},
                        end_pos={"x": text_block.bbox["x1"], "y": text_block.bbox["y1"]},
                        token_count=len(text_block.content.split())  # 簡易的なトークン数
                    )
                    chunks.append(chunk)
        
        return chunks

class PDFProcessingError(Exception):
    """PDF処理エラー"""
    pass