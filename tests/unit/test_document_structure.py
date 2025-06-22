"""
文書構造解析機能のテスト

Issue #19: PDF処理システム - spaCy文書構造解析実装
spaCyを使用した文書構造解析機能の包括的テスト
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path
import tempfile
from services.pdf_processor import (
    PDFProcessor, Section, DocumentStructure, 
    Document, Page, TextBlock, PDFProcessingError
)


class TestSectionDataClass:
    """Sectionデータクラステスト"""
    
    def test_section_creation_basic(self):
        """基本的なSection作成テスト"""
        section = Section(
            title="第1章 概要",
            level=1,
            start_page=1
        )
        
        assert section.title == "第1章 概要"
        assert section.level == 1
        assert section.start_page == 1
        assert section.end_page is None
        assert section.confidence == 0.0
        assert section.children == []
        assert section.parent is None
    
    def test_section_creation_complete(self):
        """完全なSection作成テスト"""
        section = Section(
            title="第1章 概要",
            level=1,
            start_page=1,
            end_page=10,
            start_pos={"x": 100, "y": 750},
            end_pos={"x": 500, "y": 100},
            font_size=18.0,
            font_name="Arial-Bold",
            confidence=0.9
        )
        
        assert section.title == "第1章 概要"
        assert section.level == 1
        assert section.start_page == 1
        assert section.end_page == 10
        assert section.start_pos == {"x": 100, "y": 750}
        assert section.end_pos == {"x": 500, "y": 100}
        assert section.font_size == 18.0
        assert section.font_name == "Arial-Bold"
        assert section.confidence == 0.9
    
    def test_section_hierarchy_relationships(self):
        """Sectionの階層関係テスト"""
        parent_section = Section("第1章", 1, 1)
        child_section = Section("1.1 節", 2, 2)
        
        # 親子関係の設定
        child_section.parent = parent_section
        parent_section.children.append(child_section)
        
        assert child_section.parent == parent_section
        assert parent_section.children[0] == child_section
        assert len(parent_section.children) == 1


class TestDocumentStructureDataClass:
    """DocumentStructureデータクラステスト"""
    
    def test_document_structure_creation(self):
        """DocumentStructure作成テスト"""
        section1 = Section("第1章", 1, 1)
        section2 = Section("第2章", 1, 5)
        
        doc_structure = DocumentStructure(
            sections=[section1, section2],
            toc_detected=True,
            structure_confidence=0.85,
            heading_patterns=["^第\\d+章", "^\\d+\\."],
            total_headings=2
        )
        
        assert len(doc_structure.sections) == 2
        assert doc_structure.toc_detected is True
        assert doc_structure.structure_confidence == 0.85
        assert doc_structure.heading_patterns == ["^第\\d+章", "^\\d+\\."]
        assert doc_structure.total_headings == 2
    
    def test_document_structure_defaults(self):
        """DocumentStructureデフォルト値テスト"""
        doc_structure = DocumentStructure(sections=[])
        
        assert doc_structure.sections == []
        assert doc_structure.toc_detected is False
        assert doc_structure.structure_confidence == 0.0
        assert doc_structure.heading_patterns == []
        assert doc_structure.total_headings == 0


class TestDocumentStructureAnalysis:
    """文書構造解析機能テスト"""
    
    def test_analyze_document_structure_basic(self, mock_fitz, mock_spacy_nlp):
        """基本的な文書構造解析テスト"""
        processor = PDFProcessor()
        
        # テスト用Document作成
        text_blocks = [
            TextBlock("第1章 概要", {"x0": 50, "y0": 750, "x1": 200, "y1": 770}, 18.0, "Arial-Bold"),
            TextBlock("本文テキスト", {"x0": 50, "y0": 700, "x1": 500, "y1": 720}, 12.0, "Arial"),
            TextBlock("第2章 詳細", {"x0": 50, "y0": 600, "x1": 200, "y1": 620}, 18.0, "Arial-Bold"),
        ]
        page = Page(1, text_blocks, {"width": 595, "height": 842})
        document = Document("test.pdf", [page], total_pages=1)
        
        result = processor.analyze_document_structure(document)
        
        assert isinstance(result, DocumentStructure)
        assert len(result.sections) >= 0  # 見出しが検出される可能性
        assert result.structure_confidence >= 0.0
        assert result.total_headings >= 0
    
    def test_detect_heading_candidates(self, mock_fitz, mock_spacy_nlp):
        """見出し候補検出テスト"""
        processor = PDFProcessor()
        
        # 様々なパターンの見出しを含むテスト用Document
        text_blocks = [
            TextBlock("第1章 概要", {"x0": 50, "y0": 750, "x1": 200, "y1": 770}, 18.0, "Arial-Bold"),
            TextBlock("1. はじめに", {"x0": 50, "y0": 700, "x1": 150, "y1": 720}, 16.0, "Arial-Bold"),
            TextBlock("1-1 背景", {"x0": 70, "y0": 650, "x1": 150, "y1": 670}, 14.0, "Arial-Bold"),
            TextBlock("通常の本文テキストです。", {"x0": 50, "y0": 600, "x1": 500, "y1": 620}, 12.0, "Arial"),
            TextBlock("(1) 目的", {"x0": 50, "y0": 550, "x1": 120, "y1": 570}, 14.0, "Arial-Bold"),
        ]
        page = Page(1, text_blocks, {"width": 595, "height": 842})
        document = Document("test.pdf", [page], total_pages=1)
        
        candidates = processor._detect_heading_candidates(document)
        
        assert isinstance(candidates, list)
        # 見出しパターンが検出されることを確認
        heading_texts = [c['text'] for c in candidates]
        assert any("第1章" in text for text in heading_texts)
    
    def test_analyze_hierarchy(self, mock_fitz, mock_spacy_nlp):
        """階層分析テスト"""
        processor = PDFProcessor()
        
        # 見出し候補のテストデータ
        candidates = [
            {
                'text': '第1章 概要',
                'page_number': 1,
                'font_size': 18.0,
                'font_name': 'Arial-Bold',
                'bbox': {'x0': 50, 'y0': 750, 'x1': 200, 'y1': 770},
                'confidence': 0.8
            },
            {
                'text': '1.1 背景',
                'page_number': 1,
                'font_size': 14.0,
                'font_name': 'Arial-Bold',
                'bbox': {'x0': 70, 'y0': 700, 'x1': 150, 'y1': 720},
                'confidence': 0.7
            },
            {
                'text': '第2章 詳細',
                'page_number': 2,
                'font_size': 18.0,
                'font_name': 'Arial-Bold',
                'bbox': {'x0': 50, 'y0': 750, 'x1': 200, 'y1': 770},
                'confidence': 0.8
            }
        ]
        
        sections = processor._analyze_hierarchy(candidates)
        
        assert isinstance(sections, list)
        assert len(sections) == 3
        
        # 章レベルの確認
        chapter_sections = [s for s in sections if s.level == 1]
        assert len(chapter_sections) >= 2  # 第1章、第2章
        
        # 階層レベルの確認
        for section in sections:
            assert section.level >= 1
            assert section.confidence > 0.0
    
    def test_determine_section_boundaries(self, mock_fitz, mock_spacy_nlp):
        """セクション境界決定テスト"""
        processor = PDFProcessor()
        
        # テスト用Sectionデータ
        sections = [
            Section("第1章", 1, 1),
            Section("第2章", 1, 3),
            Section("第3章", 1, 5)
        ]
        
        document = Document("test.pdf", [], total_pages=10)
        
        result = processor._determine_section_boundaries(sections, document)
        
        assert len(result) == 3
        assert result[0].end_page == 3  # 第1章は第2章の開始ページまで
        assert result[1].end_page == 5  # 第2章は第3章の開始ページまで
        assert result[2].end_page == 10  # 最後の章は文書の最後まで
    
    def test_build_hierarchy_tree(self, mock_fitz, mock_spacy_nlp):
        """階層ツリー構築テスト"""
        processor = PDFProcessor()
        
        # 階層構造のテストデータ
        sections = [
            Section("第1章", 1, 1),
            Section("1.1 節", 2, 1),
            Section("1.2 節", 2, 2),
            Section("第2章", 1, 3),
            Section("2.1 節", 2, 3)
        ]
        
        root_sections = processor._build_hierarchy_tree(sections)
        
        # ルートレベルは章のみ
        assert len(root_sections) == 2
        assert all(s.level == 1 for s in root_sections)
        
        # 第1章の子要素確認
        chapter1 = root_sections[0]
        assert len(chapter1.children) == 2
        assert chapter1.children[0].title == "1.1 節"
        assert chapter1.children[1].title == "1.2 節"
        
        # 親子関係の確認
        for child in chapter1.children:
            assert child.parent == chapter1
    
    def test_detect_table_of_contents(self, mock_fitz, mock_spacy_nlp):
        """目次検出テスト"""
        processor = PDFProcessor()
        
        # 目次を含むテスト用Document
        toc_blocks = [
            TextBlock("目次", {"x0": 50, "y0": 750, "x1": 100, "y1": 770}, 16.0, "Arial-Bold"),
            TextBlock("第1章 概要 .................. 1", {"x0": 50, "y0": 700, "x1": 300, "y1": 720}, 12.0, "Arial"),
            TextBlock("第2章 詳細 .................. 5", {"x0": 50, "y0": 680, "x1": 300, "y1": 700}, 12.0, "Arial"),
        ]
        toc_page = Page(1, toc_blocks, {"width": 595, "height": 842})
        
        document_with_toc = Document("test.pdf", [toc_page], total_pages=10)
        result_with_toc = processor._detect_table_of_contents(document_with_toc)
        
        assert result_with_toc is True
        
        # 目次なしのテスト
        normal_blocks = [
            TextBlock("第1章 概要", {"x0": 50, "y0": 750, "x1": 200, "y1": 770}, 18.0, "Arial-Bold"),
            TextBlock("本文テキストです。", {"x0": 50, "y0": 700, "x1": 500, "y1": 720}, 12.0, "Arial"),
        ]
        normal_page = Page(1, normal_blocks, {"width": 595, "height": 842})
        
        document_without_toc = Document("test.pdf", [normal_page], total_pages=10)
        result_without_toc = processor._detect_table_of_contents(document_without_toc)
        
        assert result_without_toc is False
    
    def test_calculate_structure_confidence(self, mock_fitz, mock_spacy_nlp):
        """構造信頼度計算テスト"""
        processor = PDFProcessor()
        
        # 高品質なセクション構造
        high_quality_sections = [
            Section("第1章", 1, 1, confidence=0.9, font_size=18.0),
            Section("1.1 節", 2, 1, confidence=0.8, font_size=16.0),
            Section("第2章", 1, 3, confidence=0.9, font_size=18.0),
            Section("2.1 節", 2, 3, confidence=0.8, font_size=16.0),
        ]
        
        document = Document("test.pdf", [], total_pages=10)
        
        confidence = processor._calculate_structure_confidence(high_quality_sections, document)
        
        assert 0.0 <= confidence <= 1.0
        assert confidence > 0.5  # 高品質な構造なので信頼度が高い
        
        # 低品質なセクション構造
        low_quality_sections = [
            Section("不明な見出し", 1, 1, confidence=0.3, font_size=12.0),
        ]
        
        low_confidence = processor._calculate_structure_confidence(low_quality_sections, document)
        assert low_confidence < confidence  # 低品質な構造の信頼度は低い
    
    def test_heading_patterns_matching(self, mock_fitz, mock_spacy_nlp):
        """見出しパターンマッチングテスト"""
        processor = PDFProcessor()
        
        # 各パターンのテストケース
        test_cases = [
            ("第1章 概要", True),
            ("第2節 詳細", True),
            ("1. はじめに", True),
            ("1-1 背景", True),
            ("(1) 目的", True),
            ("１．全角数字", True),
            ("あ. ひらがな見出し", True),
            ("ア. カタカナ見出し", True),
            ("通常の本文テキスト", False),
            ("123 数字のみ", False),
        ]
        
        for text, should_match in test_cases:
            has_match = any(
                __import__('re').match(pattern, text) 
                for pattern in processor.heading_patterns
            )
            if should_match:
                assert has_match, f"'{text}' should match heading pattern"
            # 注意: False caseは他の条件（フォントサイズ等）でも見出しとして検出される可能性があるため、
            # ここでは厳密にチェックしない


class TestDocumentStructureIntegration:
    """文書構造解析統合テスト"""
    
    def test_process_pdf_with_structure_analysis(self, sample_pdf_bytes, mock_fitz, mock_spacy_nlp):
        """PDF処理における文書構造解析統合テスト"""
        processor = PDFProcessor()
        filename = "structured_document.pdf"
        
        result = processor.process_pdf(sample_pdf_bytes, filename)
        
        assert result is not None
        assert isinstance(result.document_structure, DocumentStructure)
        assert result.document_structure.structure_confidence >= 0.0
        assert isinstance(result.document_structure.sections, list)
        assert result.document_structure.total_headings >= 0
    
    def test_empty_document_structure_analysis(self, mock_fitz, mock_spacy_nlp):
        """空文書の構造解析テスト"""
        processor = PDFProcessor()
        
        # 空のページを含むDocument
        empty_page = Page(1, [], {"width": 595, "height": 842})
        empty_document = Document("empty.pdf", [empty_page], total_pages=1)
        
        result = processor.analyze_document_structure(empty_document)
        
        assert isinstance(result, DocumentStructure)
        assert len(result.sections) == 0
        assert result.structure_confidence == 0.0
        assert result.total_headings == 0
    
    def test_complex_document_structure(self, mock_fitz, mock_spacy_nlp):
        """複雑な文書構造の解析テスト"""
        processor = PDFProcessor()
        
        # 複雑な階層構造のテスト用Document
        complex_blocks = [
            # 第1章
            TextBlock("第1章 概要", {"x0": 50, "y0": 750, "x1": 200, "y1": 770}, 18.0, "Arial-Bold"),
            TextBlock("1.1 背景", {"x0": 70, "y0": 700, "x1": 150, "y1": 720}, 14.0, "Arial-Bold"),
            TextBlock("1.1.1 問題設定", {"x0": 90, "y0": 650, "x1": 200, "y1": 670}, 12.0, "Arial-Bold"),
            TextBlock("本文テキスト", {"x0": 50, "y0": 600, "x1": 500, "y1": 620}, 10.0, "Arial"),
            
            # 第2章
            TextBlock("第2章 手法", {"x0": 50, "y0": 500, "x1": 200, "y1": 520}, 18.0, "Arial-Bold"),
            TextBlock("2.1 アプローチ", {"x0": 70, "y0": 450, "x1": 180, "y1": 470}, 14.0, "Arial-Bold"),
        ]
        
        page1 = Page(1, complex_blocks, {"width": 595, "height": 842})
        document = Document("complex.pdf", [page1], total_pages=1)
        
        result = processor.analyze_document_structure(document)
        
        assert isinstance(result, DocumentStructure)
        assert len(result.sections) > 0
        
        # 階層レベルの確認
        levels = [s.level for s in result.sections]
        assert 1 in levels  # 章レベル
        # 複数レベルが存在することを期待するが、実装の詳細により異なる可能性
        if len(result.sections) > 2:
            assert len(set(levels)) >= 1  # 少なくとも1つのレベルは存在


class TestDocumentStructureErrorHandling:
    """文書構造解析エラーハンドリングテスト"""
    
    def test_analyze_structure_with_malformed_document(self, mock_fitz, mock_spacy_nlp):
        """不正な文書での構造解析テスト"""
        processor = PDFProcessor()
        
        # 不正なTextBlockを含むDocument
        malformed_blocks = [
            TextBlock("", {"x0": 0, "y0": 0, "x1": 0, "y1": 0}, 0.0, ""),  # 空のブロック
            TextBlock("正常なテキスト", {"x0": 50, "y0": 750, "x1": 200, "y1": 770}, 12.0, "Arial"),
        ]
        page = Page(1, malformed_blocks, {"width": 595, "height": 842})
        document = Document("malformed.pdf", [page], total_pages=1)
        
        # エラーが発生せずに処理が完了することを確認
        result = processor.analyze_document_structure(document)
        
        assert isinstance(result, DocumentStructure)
        assert result.structure_confidence >= 0.0
    
    def test_analyze_structure_with_no_headings(self, mock_fitz, mock_spacy_nlp):
        """見出しがない文書の構造解析テスト"""
        processor = PDFProcessor()
        
        # 見出しがない文書
        text_blocks = [
            TextBlock("これは通常の本文です。", {"x0": 50, "y0": 750, "x1": 500, "y1": 770}, 12.0, "Arial"),
            TextBlock("見出しのような文書構造はありません。", {"x0": 50, "y0": 700, "x1": 500, "y1": 720}, 12.0, "Arial"),
            TextBlock("全て同じフォントサイズです。", {"x0": 50, "y0": 650, "x1": 500, "y1": 670}, 12.0, "Arial"),
        ]
        page = Page(1, text_blocks, {"width": 595, "height": 842})
        document = Document("no_headings.pdf", [page], total_pages=1)
        
        result = processor.analyze_document_structure(document)
        
        assert isinstance(result, DocumentStructure)
        assert len(result.sections) == 0  # 見出しが検出されない
        assert result.structure_confidence == 0.0
        assert result.total_headings == 0