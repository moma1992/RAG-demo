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
import re

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
class Section:
    """文書セクションデータクラス"""
    title: str
    level: int  # 階層レベル (1=章, 2=節, 3=項 等)
    start_page: int
    end_page: Optional[int] = None
    start_pos: Optional[Dict[str, float]] = None
    end_pos: Optional[Dict[str, float]] = None
    font_size: Optional[float] = None
    font_name: Optional[str] = None
    confidence: float = 0.0  # 検出信頼度 (0.0-1.0)
    children: List['Section'] = field(default_factory=list)
    parent: Optional['Section'] = None

@dataclass
class DocumentStructure:
    """文書構造データクラス"""
    sections: List[Section]
    toc_detected: bool = False  # 目次が検出されたか
    structure_confidence: float = 0.0  # 全体の構造信頼度
    heading_patterns: List[str] = field(default_factory=list)  # 検出されたパターン
    total_headings: int = 0
    
@dataclass
class ProcessingResult:
    """PDF処理結果データクラス"""
    chunks: List[DocumentChunk]
    total_pages: int
    total_chunks: int
    processing_time: float
    errors: List[str]
    document_structure: Optional[DocumentStructure] = None

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
        
        # 日本語見出しパターン定義
        self.heading_patterns = [
            r'^第\d+章\s+.+',  # 第1章 タイトル
            r'^第\d+節\s+.+',  # 第1節 タイトル
            r'^\d+\.\s+.+',   # 1. タイトル
            r'^\d+\-\d+\s+.+', # 1-1 タイトル
            r'^\(\d+\)\s+.+', # (1) タイトル
            r'^[１-９一二三四五六七八九十]+[．\s]+.+',  # 全角数字
            r'^[あ-ん][．\.\s]+.+',  # ひらがな見出し
            r'^[ア-ン][．\.\s]+.+',  # カタカナ見出し
        ]
    
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
                
                # 文書構造解析
                document_structure = self.analyze_document_structure(document)
                
                # DocumentからDocumentChunkを作成
                chunks = self._convert_document_to_chunks(document)
                
                return ProcessingResult(
                    chunks=chunks,
                    total_pages=document.total_pages,
                    total_chunks=len(chunks),
                    processing_time=0.1,
                    errors=[],
                    document_structure=document_structure
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
            
            # ページ数を事前に取得（document close前）
            page_count = pdf_doc.page_count
            
            # Document作成
            document = Document(
                filename=pdf_path.stem,
                original_filename=pdf_path.name,
                total_pages=page_count,
                pages=pages,
                metadata=metadata,
                processing_status="completed"
            )
            
            pdf_doc.close()
            logger.info(f"PDF処理完了: {pdf_path.name}, {page_count}ページ")
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
    
    def analyze_document_structure(self, document: Document) -> DocumentStructure:
        """
        文書構造を解析してセクション階層を検出
        
        Args:
            document: 解析対象の文書
            
        Returns:
            DocumentStructure: 検出された文書構造
        """
        logger.info(f"文書構造解析開始: {document.filename}")
        
        # 見出し候補を検出
        heading_candidates = self._detect_heading_candidates(document)
        
        # 階層構造を分析
        sections = self._analyze_hierarchy(heading_candidates)
        
        # セクション境界を決定
        sections = self._determine_section_boundaries(sections, document)
        
        # 階層ツリーを構築
        root_sections = self._build_hierarchy_tree(sections)
        
        # 目次検出
        toc_detected = self._detect_table_of_contents(document)
        
        # 構造信頼度を計算
        structure_confidence = self._calculate_structure_confidence(sections, document)
        
        document_structure = DocumentStructure(
            sections=root_sections,
            toc_detected=toc_detected,
            structure_confidence=structure_confidence,
            heading_patterns=[pattern for pattern in self.heading_patterns if any(re.match(pattern, section.title) for section in sections)],
            total_headings=len(sections)
        )
        
        logger.info(f"文書構造解析完了: {len(root_sections)}個のセクション検出, 信頼度: {structure_confidence:.2f}")
        return document_structure
    
    def _detect_heading_candidates(self, document: Document) -> List[Dict[str, Any]]:
        """
        見出し候補を検出
        
        Args:
            document: 対象文書
            
        Returns:
            List[Dict]: 見出し候補リスト
        """
        candidates = []
        
        for page in document.pages:
            # ページ内のテキストブロックをフォントサイズでソート
            sorted_blocks = sorted(page.text_blocks, key=lambda x: x.font_size, reverse=True)
            
            # 平均フォントサイズを計算
            avg_font_size = sum(block.font_size for block in page.text_blocks) / len(page.text_blocks) if page.text_blocks else 12.0
            
            for block in page.text_blocks:
                text = block.content.strip()
                if not text:
                    continue
                
                # 見出しの条件をチェック
                is_heading = False
                confidence = 0.0
                
                # 1. フォントサイズが平均より大きい
                if block.font_size > avg_font_size * 1.2:
                    is_heading = True
                    confidence += 0.3
                
                # 2. パターンマッチング
                for pattern in self.heading_patterns:
                    if re.match(pattern, text):
                        is_heading = True
                        confidence += 0.4
                        break
                
                # 3. 短いテキスト（見出しらしい長さ）
                if len(text) < 100 and len(text.split()) < 15:
                    confidence += 0.2
                
                # 4. 行の最初にある
                if block.bbox["x0"] < 100:  # 左端に近い
                    confidence += 0.1
                
                if is_heading and confidence > 0.3:
                    candidates.append({
                        'text': text,
                        'page_number': page.page_number,
                        'font_size': block.font_size,
                        'font_name': block.font_name,
                        'bbox': block.bbox,
                        'confidence': min(confidence, 1.0)
                    })
        
        logger.info(f"見出し候補検出: {len(candidates)}個")
        return candidates
    
    def _analyze_hierarchy(self, candidates: List[Dict[str, Any]]) -> List[Section]:
        """
        見出し候補から階層レベルを分析
        
        Args:
            candidates: 見出し候補リスト
            
        Returns:
            List[Section]: セクションリスト
        """
        if not candidates:
            return []
        
        # フォントサイズでグループ化
        font_sizes = sorted(set(candidate['font_size'] for candidate in candidates), reverse=True)
        
        sections = []
        for candidate in candidates:
            # フォントサイズから階層レベルを決定
            level = font_sizes.index(candidate['font_size']) + 1
            
            # パターンから階層レベルを調整
            text = candidate['text']
            if re.match(r'^第\d+章', text):
                level = 1
            elif re.match(r'^第\d+節', text):
                level = 2
            elif re.match(r'^\d+\.', text):
                if level > 3:
                    level = 3
            
            section = Section(
                title=text,
                level=level,
                start_page=candidate['page_number'],
                font_size=candidate['font_size'],
                font_name=candidate['font_name'],
                start_pos={'x': candidate['bbox']['x0'], 'y': candidate['bbox']['y0']},
                confidence=candidate['confidence']
            )
            sections.append(section)
        
        return sections
    
    def _determine_section_boundaries(self, sections: List[Section], document: Document) -> List[Section]:
        """
        セクションの境界（終了位置）を決定
        
        Args:
            sections: セクションリスト
            document: 文書
            
        Returns:
            List[Section]: 境界が設定されたセクションリスト
        """
        for i, section in enumerate(sections):
            # 次のセクションがある場合、その直前までを範囲とする
            if i + 1 < len(sections):
                next_section = sections[i + 1]
                section.end_page = next_section.start_page
                if next_section.start_page == section.start_page:
                    # 同じページ内の場合、Y座標で判定
                    section.end_pos = {'x': next_section.start_pos['x'], 'y': next_section.start_pos['y']}
            else:
                # 最後のセクションは文書の最後まで
                section.end_page = document.total_pages
        
        return sections
    
    def _build_hierarchy_tree(self, sections: List[Section]) -> List[Section]:
        """
        セクションの階層ツリーを構築
        
        Args:
            sections: セクションリスト
            
        Returns:
            List[Section]: ルートレベルのセクションリスト
        """
        if not sections:
            return []
        
        # レベルでソート
        sorted_sections = sorted(sections, key=lambda x: (x.start_page, x.level))
        
        root_sections = []
        stack = []  # 親候補のスタック
        
        for section in sorted_sections:
            # 現在のレベルより深い親を除去
            while stack and stack[-1].level >= section.level:
                stack.pop()
            
            # 親が存在する場合
            if stack:
                parent = stack[-1]
                section.parent = parent
                parent.children.append(section)
            else:
                # ルートレベル
                root_sections.append(section)
            
            stack.append(section)
        
        return root_sections
    
    def _detect_table_of_contents(self, document: Document) -> bool:
        """
        目次の存在を検出
        
        Args:
            document: 文書
            
        Returns:
            bool: 目次が検出されたかどうか
        """
        toc_keywords = ['目次', '目録', 'もくじ', 'Contents', 'INDEX']
        
        # 最初の数ページで目次キーワードを検索
        for page in document.pages[:5]:  # 最初の5ページまで
            for block in page.text_blocks:
                text = block.content.strip()
                if any(keyword in text for keyword in toc_keywords):
                    # 目次らしいパターンがあるかチェック
                    full_page_text = ' '.join(b.content for b in page.text_blocks)
                    if re.search(r'\d+\s*$', full_page_text, re.MULTILINE):  # ページ番号らしきもの
                        return True
        
        return False
    
    def _calculate_structure_confidence(self, sections: List[Section], document: Document) -> float:
        """
        文書構造の信頼度を計算
        
        Args:
            sections: 検出されたセクション
            document: 文書
            
        Returns:
            float: 信頼度 (0.0-1.0)
        """
        if not sections:
            return 0.0
        
        confidence_factors = []
        
        # 1. セクション数の妥当性
        section_ratio = len(sections) / document.total_pages
        if 0.1 <= section_ratio <= 2.0:  # 適度なセクション数
            confidence_factors.append(0.3)
        
        # 2. 各セクションの信頼度の平均
        avg_section_confidence = sum(s.confidence for s in sections) / len(sections)
        confidence_factors.append(avg_section_confidence * 0.4)
        
        # 3. 階層構造の一貫性
        levels = [s.level for s in sections]
        if len(set(levels)) > 1:  # 複数レベルが存在
            confidence_factors.append(0.2)
        
        # 4. フォントサイズの一貫性
        font_sizes = [s.font_size for s in sections if s.font_size]
        if font_sizes and len(set(font_sizes)) >= 2:  # 異なるフォントサイズ
            confidence_factors.append(0.1)
        
        return min(sum(confidence_factors), 1.0)

class PDFProcessingError(Exception):
    """PDF処理エラー"""
    pass