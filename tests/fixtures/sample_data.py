"""
サンプルテストデータ

テストで使用するサンプルデータの定義
"""

from typing import List, Dict, Any


# サンプルPDFテキストデータ
SAMPLE_PDF_TEXTS = {
    "simple": "これはシンプルなテストPDFです。",
    "multi_page": [
        "第1ページ: 会社概要について説明します。",
        "第2ページ: 新入社員研修の内容を紹介します。",
        "第3ページ: 福利厚生について詳しく説明します。"
    ],
    "japanese_business": """
        新入社員研修マニュアル
        
        第1章: 会社概要
        当社は1995年に設立され、IT分野での革新的なソリューションを提供しています。
        
        第2章: 研修プログラム
        新入社員研修は3週間の集中プログラムです。
        - 第1週: 基礎知識習得
        - 第2週: 実践研修
        - 第3週: プロジェクト実習
        
        第3章: 評価基準
        研修期間中の評価は以下の基準で行われます。
        - 出席率: 30%
        - 課題提出: 40%
        - 最終プレゼンテーション: 30%
    """,
    "long_document": "この文書は長いテキストのテストです。" * 1000
}

# サンプル文書チャンクデータ
SAMPLE_CHUNKS = [
    {
        "content": "会社概要について説明します。当社は1995年に設立されました。",
        "filename": "company_overview.pdf",
        "page_number": 1,
        "chapter_number": 1,
        "section_name": "会社概要",
        "token_count": 25,
        "embedding": [0.1 + i * 0.001 for i in range(1536)]
    },
    {
        "content": "新入社員研修は3週間の集中プログラムです。",
        "filename": "training_manual.pdf", 
        "page_number": 2,
        "chapter_number": 2,
        "section_name": "研修プログラム",
        "token_count": 15,
        "embedding": [0.2 + i * 0.001 for i in range(1536)]
    },
    {
        "content": "福利厚生について詳しく説明します。",
        "filename": "benefits_guide.pdf",
        "page_number": 1,
        "chapter_number": 1,
        "section_name": "福利厚生",
        "token_count": 12,
        "embedding": [0.3 + i * 0.001 for i in range(1536)]
    }
]

# サンプル検索結果データ
SAMPLE_SEARCH_RESULTS = [
    {
        "content": "新入社員研修は3週間実施されます。",
        "filename": "training_manual.pdf",
        "page_number": 2,
        "similarity_score": 0.95,
        "metadata": {
            "section": "研修プログラム",
            "chapter": 2
        }
    },
    {
        "content": "研修期間中の評価は出席率、課題提出、プレゼンテーションで行われます。",
        "filename": "training_manual.pdf",
        "page_number": 3,
        "similarity_score": 0.88,
        "metadata": {
            "section": "評価基準",
            "chapter": 3
        }
    }
]

# サンプル文書レコードデータ
SAMPLE_DOCUMENTS = [
    {
        "id": "doc-001",
        "filename": "company_overview.pdf",
        "original_filename": "会社概要.pdf",
        "upload_date": "2024-01-15T10:00:00Z",
        "file_size": 1024000,
        "total_pages": 5,
        "processing_status": "completed"
    },
    {
        "id": "doc-002", 
        "filename": "training_manual.pdf",
        "original_filename": "新入社員研修マニュアル.pdf",
        "upload_date": "2024-01-16T14:30:00Z",
        "file_size": 2048000,
        "total_pages": 25,
        "processing_status": "completed"
    },
    {
        "id": "doc-003",
        "filename": "benefits_guide.pdf",
        "original_filename": "福利厚生ガイド.pdf", 
        "upload_date": "2024-01-17T09:15:00Z",
        "file_size": 512000,
        "total_pages": 8,
        "processing_status": "processing"
    }
]

# サンプル質問・回答データ
SAMPLE_QA_PAIRS = [
    {
        "question": "新入社員研修はどのくらいの期間ですか？",
        "expected_answer": "新入社員研修は3週間の集中プログラムです。",
        "context_chunks": [
            "新入社員研修は3週間の集中プログラムです。",
            "研修プログラムは基礎知識習得、実践研修、プロジェクト実習の3段階で構成されています。"
        ]
    },
    {
        "question": "会社の設立年はいつですか？",
        "expected_answer": "当社は1995年に設立されました。",
        "context_chunks": [
            "当社は1995年に設立され、IT分野での革新的なソリューションを提供しています。"
        ]
    },
    {
        "question": "研修の評価基準を教えてください。",
        "expected_answer": "出席率30%、課題提出40%、最終プレゼンテーション30%で評価されます。",
        "context_chunks": [
            "研修期間中の評価は以下の基準で行われます。出席率30%、課題提出40%、最終プレゼンテーション30%"
        ]
    }
]

# エラーケース用データ
ERROR_CASES = {
    "invalid_pdf": b"invalid pdf content",
    "empty_file": b"",
    "corrupted_pdf": b"%PDF-1.4\ncorrupted content without proper ending",
    "large_file": b"%PDF-1.4\n" + b"A" * (100 * 1024 * 1024) + b"\n%%EOF",  # 100MB
    "non_utf8_text": "invalid\xff\xfe text",
    "malformed_json": '{"invalid": json content}',
    "sql_injection": "'; DROP TABLE documents; --",
    "xss_content": "<script>alert('test')</script>"
}

# パフォーマンステスト用データ
PERFORMANCE_TEST_DATA = {
    "small_dataset": {
        "document_count": 10,
        "chunks_per_document": 20,
        "expected_search_time": 1.0  # seconds
    },
    "medium_dataset": {
        "document_count": 100,
        "chunks_per_document": 50,
        "expected_search_time": 3.0  # seconds
    },
    "large_dataset": {
        "document_count": 1000,
        "chunks_per_document": 100,
        "expected_search_time": 10.0  # seconds
    }
}

# 設定データ
TEST_CONFIGS = {
    "default": {
        "chunk_size": 512,
        "chunk_overlap": 0.1,
        "max_file_size_mb": 50,
        "search_top_k": 5,
        "similarity_threshold": 0.7
    },
    "high_performance": {
        "chunk_size": 1024,
        "chunk_overlap": 0.05,
        "max_file_size_mb": 100,
        "search_top_k": 10,
        "similarity_threshold": 0.8
    },
    "memory_efficient": {
        "chunk_size": 256,
        "chunk_overlap": 0.2,
        "max_file_size_mb": 25,
        "search_top_k": 3,
        "similarity_threshold": 0.6
    }
}