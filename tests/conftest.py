"""
pytest設定とフィクスチャ

テスト用の共通設定とモックフィクスチャ
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from typing import Generator, Dict, Any
import tempfile
import os
from pathlib import Path

# テスト用環境変数設定
@pytest.fixture(autouse=True)
def setup_test_env():
    """テスト環境設定"""
    test_env = {
        "OPENAI_API_KEY": "test-openai-key",
        "ANTHROPIC_API_KEY": "test-anthropic-key",
        "SUPABASE_URL": "https://test.supabase.co",
        "SUPABASE_ANON_KEY": "test-supabase-key"
    }
    
    with patch.dict(os.environ, test_env):
        yield

# OpenAI APIモック
@pytest.fixture
def mock_openai_client():
    """OpenAI クライアントモック"""
    with patch('openai.OpenAI') as mock_client:
        # 埋め込み生成モック
        mock_embeddings = Mock()
        mock_embeddings.create.return_value = Mock(
            data=[Mock(embedding=[0.1] * 1536)]
        )
        mock_client.return_value.embeddings = mock_embeddings
        yield mock_client

# Claude APIモック
@pytest.fixture
def mock_claude_client():
    """Claude クライアントモック"""
    with patch('anthropic.Anthropic') as mock_client:
        # メッセージ生成モック
        mock_messages = Mock()
        mock_messages.create.return_value = Mock(
            content=[Mock(text="テスト応答です。")]
        )
        mock_client.return_value.messages = mock_messages
        yield mock_client

# Supabaseモック
@pytest.fixture
def mock_supabase_client():
    """Supabase クライアントモック"""
    with patch('supabase.create_client') as mock_create_client:
        mock_client = Mock()
        
        # テーブル操作モック
        mock_table = Mock()
        mock_table.insert.return_value.execute.return_value = Mock(
            data=[{"id": "test-id"}]
        )
        mock_table.select.return_value.execute.return_value = Mock(
            data=[{"id": "test-id", "content": "テストデータ"}]
        )
        mock_table.delete.return_value.execute.return_value = Mock()
        
        mock_client.table.return_value = mock_table
        mock_create_client.return_value = mock_client
        yield mock_client

# spaCyモック
@pytest.fixture
def mock_spacy():
    """spaCy モック"""
    with patch('spacy.load') as mock_load:
        mock_nlp = Mock()
        mock_doc = Mock()
        mock_doc.sents = [Mock(text="テスト文1。"), Mock(text="テスト文2。")]
        mock_nlp.return_value = mock_doc
        mock_load.return_value = mock_nlp
        yield mock_nlp

@pytest.fixture
def mock_spacy_nlp():
    """spaCy NLPパイプライン詳細モック"""
    mock_nlp = Mock()
    
    # 文書解析結果のモック
    def process_text(text):
        mock_doc = Mock()
        # 文章境界の検出（句点で分割）
        sentences = text.split('。')
        mock_sents = []
        for i, sent in enumerate(sentences):
            if sent.strip():
                mock_sent = Mock()
                mock_sent.text = sent.strip() + '。'
                mock_sent.start = text.find(sent)
                mock_sent.end = text.find(sent) + len(sent)
                mock_sents.append(mock_sent)
        
        mock_doc.sents = mock_sents
        mock_doc.text = text
        return mock_doc
    
    mock_nlp.side_effect = process_text
    return mock_nlp

# PyMuPDFモック
@pytest.fixture
def mock_fitz():
    """PyMuPDF (fitz) モック"""
    with patch('fitz.open') as mock_open:
        mock_doc = Mock()
        mock_page = Mock()
        def mock_get_text(mode="text"):
            if mode == "dict":
                return {
                    "blocks": [
                        {
                            "lines": [
                                {
                                    "spans": [
                                        {
                                            "text": "サンプルPDFテキスト",
                                            "bbox": [100, 750, 500, 770],
                                            "size": 12.0,
                                            "font": "Arial"
                                        }
                                    ]
                                }
                            ]
                        }
                    ]
                }
            else:
                return "サンプルPDFテキスト"
        
        mock_page.get_text = mock_get_text
        mock_page.number = 0
        mock_page.rect = Mock(width=595, height=842)
        mock_page.get_text_blocks.return_value = [
            (100, 750, 500, 770, "テストテキスト1", 0, 0),
            (100, 700, 500, 720, "テストテキスト2", 0, 1)
        ]
        mock_doc.__len__ = Mock(return_value=1)
        mock_doc.__getitem__ = Mock(return_value=mock_page)
        mock_doc.page_count = 1
        mock_doc.metadata = {
            "title": "テスト文書",
            "author": "テスト作成者",
            "subject": "テスト用PDF"
        }
        mock_open.return_value = mock_doc
        
        # close メソッドのモック
        mock_doc.close = Mock()
        
        yield mock_doc

@pytest.fixture 
def mock_fitz_document():
    """PyMuPDF Document詳細モック"""
    mock_doc = Mock()
    mock_doc.page_count = 3
    mock_doc.metadata = {
        'title': 'テスト文書',
        'author': 'テスト著者',
        'subject': 'PDF処理テスト',
        'creator': 'pytest'
    }
    
    # 複数ページのモック
    pages = []
    for i in range(3):
        mock_page = Mock()
        mock_page.number = i
        mock_page.rect = Mock(width=595, height=842)
        mock_page.get_text.return_value = f"ページ{i+1}のテキスト内容です。"
        mock_page.get_text_blocks.return_value = [
            (100, 750-j*30, 500, 770-j*30, f"ページ{i+1}のブロック{j+1}", 0, j)
            for j in range(3)
        ]
        pages.append(mock_page)
    
    mock_doc.__getitem__ = lambda self, idx: pages[idx]
    mock_doc.__len__ = lambda self: len(pages)
    
    return mock_doc

# テスト用PDFファイル
@pytest.fixture
def sample_pdf_bytes():
    """サンプルPDFバイトデータ"""
    # 最小限のPDFヘッダー（実際のPDF処理テストには適さないが、ファイル形式テストには使用可能）
    return b"%PDF-1.4\n%Test PDF content\n%%EOF"

@pytest.fixture
def real_sample_pdf_bytes():
    """実際のPDFファイル生成（reportlab使用）"""
    from tests.fixtures.sample_data import PDFSampleGenerator
    return PDFSampleGenerator.create_simple_pdf()

@pytest.fixture
def multi_page_pdf_bytes():
    """複数ページPDFファイル生成"""
    from tests.fixtures.sample_data import PDFSampleGenerator
    return PDFSampleGenerator.create_multi_page_pdf()

@pytest.fixture
def test_pdf_files(temp_dir):
    """テスト用PDFファイル一式"""
    from tests.fixtures.sample_data import create_test_pdf_files
    return create_test_pdf_files(temp_dir)

# テスト用一時ディレクトリ
@pytest.fixture
def temp_dir():
    """一時ディレクトリ"""
    with tempfile.TemporaryDirectory() as tmp_dir:
        yield Path(tmp_dir)

# テスト用設定
@pytest.fixture
def test_config():
    """テスト用設定"""
    return {
        "chunk_size": 512,
        "chunk_overlap": 0.1,
        "max_file_size_mb": 50,
        "search_top_k": 5,
        "similarity_threshold": 0.7
    }

# モックStreamlitセッション
@pytest.fixture
def mock_streamlit_session():
    """Streamlit セッション状態モック"""
    with patch('streamlit.session_state') as mock_session:
        mock_session.chat_history = []
        mock_session.current_document = None
        yield mock_session

# 外部API呼び出しを全てモック化
@pytest.fixture(autouse=True)
def mock_external_apis(mock_openai_client, mock_claude_client, mock_supabase_client):
    """全テストで外部API呼び出しをモック化"""
    # spaCyの初期化もモック化
    with patch('spacy.load') as mock_spacy_load, \
         patch('spacy.blank') as mock_spacy_blank:
        
        # spaCy モックNLPオブジェクト作成
        mock_nlp = Mock()
        mock_nlp.return_value = Mock()
        mock_spacy_load.return_value = mock_nlp
        mock_spacy_blank.return_value = mock_nlp
        yield