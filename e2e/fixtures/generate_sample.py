#!/usr/bin/env python3
"""
E2Eテスト用サンプルPDF生成スクリプト
"""

from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.cidfonts import UnicodeCIDFont
import os

def create_sample_pdf(filename="sample_document.pdf"):
    """サンプルPDFファイルを生成"""
    
    # 日本語フォント登録
    try:
        pdfmetrics.registerFont(UnicodeCIDFont('HeiseiKakuGo-W5'))
        font_name = 'HeiseiKakuGo-W5'
    except:
        font_name = 'Helvetica'  # フォールバック
    
    # PDF作成
    c = canvas.Canvas(filename, pagesize=A4)
    width, height = A4
    
    # タイトルページ
    c.setFont(font_name, 20)
    c.drawString(100, height - 100, "E2Eテスト用サンプル文書")
    
    c.setFont(font_name, 12)
    c.drawString(100, height - 150, "この文書はE2Eテストで使用されます。")
    c.drawString(100, height - 170, "様々な検索テストケースを含んでいます。")
    
    # コンテンツセクション
    y_position = height - 220
    sections = [
        ("1. はじめに", [
            "このシステムは新入社員向けの文書検索システムです。",
            "PDFファイルをアップロードして、自然言語で質問できます。"
        ]),
        ("2. 機能概要", [
            "・PDF文書のアップロード機能",
            "・ベクトル検索による文書検索",
            "・AI回答生成機能",
            "・引用情報の表示"
        ]),
        ("3. 技術仕様", [
            "・Frontend: Streamlit",
            "・Vector DB: Supabase + pgvector", 
            "・LLM: Claude API",
            "・Embeddings: OpenAI text-embedding-3-small"
        ])
    ]
    
    for title, content in sections:
        c.setFont(font_name, 14)
        c.drawString(100, y_position, title)
        y_position -= 25
        
        c.setFont(font_name, 10)
        for line in content:
            c.drawString(120, y_position, line)
            y_position -= 20
        
        y_position -= 10
    
    c.showPage()
    c.save()
    print(f"✅ サンプルPDF作成完了: {filename}")

if __name__ == "__main__":
    # スクリプトのディレクトリに移動
    script_dir = os.path.dirname(os.path.abspath(__file__))
    os.chdir(script_dir)
    
    # サンプルPDF生成
    create_sample_pdf()
    create_sample_pdf("test_document_1.pdf")
    create_sample_pdf("test_document_2.pdf")