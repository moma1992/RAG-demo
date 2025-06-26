"""
E2Eテスト用PDFファイル生成ユーティリティ
"""

import tempfile
import os
from pathlib import Path
from typing import Optional

def create_simple_test_pdf(content: Optional[str] = None, pages: int = 1) -> str:
    """
    シンプルなテスト用PDFファイルを作成
    
    Args:
        content: PDF内容（デフォルトはテスト用テキスト）
        pages: ページ数
        
    Returns:
        str: 作成されたPDFファイルのパス
    """
    try:
        from reportlab.pdfgen import canvas
        from reportlab.lib.pagesizes import letter
        from reportlab.pdfbase import pdfmetrics
        from reportlab.pdfbase.cidfonts import UnicodeCIDFont
    except ImportError:
        # reportlabがない場合は空のPDFファイルを作成
        return create_dummy_pdf()
    
    # 一時ファイル作成
    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp_file:
        pdf_path = tmp_file.name
    
    try:
        # 日本語フォント登録
        pdfmetrics.registerFont(UnicodeCIDFont('HeiseiMin-W3'))
        
        c = canvas.Canvas(pdf_path, pagesize=letter)
        
        default_content = [
            "新入社員向け研修資料",
            "",
            "第1章: 会社概要",
            "当社は2020年に設立された技術系企業です。",
            "主な事業内容は以下の通りです：",
            "- AIソリューション開発",
            "- データ分析コンサルティング", 
            "- クラウドインフラ構築",
            "",
            "第2章: 業務フロー",
            "新入社員の皆様には以下の流れで業務を進めていただきます：",
            "1. プロジェクトアサイン",
            "2. 要件定義",
            "3. 設計・開発",
            "4. テスト・デバッグ",
            "5. デプロイメント",
            "",
            "第3章: 注意事項",
            "- 情報セキュリティを厳守してください",
            "- チームコミュニケーションを大切にしてください",
            "- 継続的な学習を心がけてください",
            "",
            "質問がある場合は、人事部までお問い合わせください。"
        ]
        
        content_lines = content.split('\n') if content else default_content
        
        for page_num in range(pages):
            if page_num > 0:
                c.showPage()
            
            # ページヘッダー
            c.setFont("HeiseiMin-W3", 16)
            c.drawString(50, 750, f"テスト文書 - ページ {page_num + 1}")
            
            # コンテンツ
            c.setFont("HeiseiMin-W3", 12)
            y_position = 700
            
            for line in content_lines:
                if y_position < 50:  # ページ下部に到達
                    break
                c.drawString(50, y_position, line)
                y_position -= 20
        
        c.save()
        return pdf_path
        
    except Exception as e:
        # フォントエラーなどの場合はダミーファイルを作成
        os.unlink(pdf_path)
        return create_dummy_pdf()

def create_dummy_pdf() -> str:
    """
    reportlabが使用できない場合のダミーPDFファイル作成
    """
    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp_file:
        # 最小限のPDFヘッダーを書き込み
        tmp_file.write(b"""%PDF-1.4
1 0 obj
<< /Type /Catalog /Pages 2 0 R >>
endobj
2 0 obj
<< /Type /Pages /Kids [3 0 R] /Count 1 >>
endobj
3 0 obj
<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] >>
endobj
xref
0 4
0000000000 65535 f 
0000000009 00000 n 
0000000058 00000 n 
0000000115 00000 n 
trailer
<< /Size 4 /Root 1 0 R >>
startxref
190
%%EOF""")
        return tmp_file.name

def create_large_test_pdf(pages: int = 10) -> str:
    """
    大きなテスト用PDFファイルを作成
    
    Args:
        pages: ページ数
        
    Returns:
        str: 作成されたPDFファイルのパス
    """
    content = """大容量テスト文書

これは大容量PDFのテスト用コンテンツです。
複数ページにわたってテキストが含まれています。

詳細な技術仕様:
- システムアーキテクチャについて
- データベース設計について
- API設計について
- セキュリティ要件について
- パフォーマンス要件について

各項目について詳細に記載されており、
新入社員の皆様には重要な情報となります。
時間をかけて十分に理解してください。

追加の学習リソース:
- 社内Wiki
- 技術ブログ
- 研修動画
- メンタリングプログラム

定期的にフォローアップを実施しますので、
不明な点があればお気軽にご相談ください。"""
    
    return create_simple_test_pdf(content, pages)

def setup_test_fixtures():
    """テスト用PDFファイルを固定の場所に作成"""
    fixtures_dir = Path("tests/e2e/fixtures")
    fixtures_dir.mkdir(parents=True, exist_ok=True)
    
    # 小さなPDFファイル
    small_pdf = create_simple_test_pdf()
    small_pdf_dest = fixtures_dir / "sample.pdf"
    os.rename(small_pdf, str(small_pdf_dest))
    
    # 大きなPDFファイル
    large_pdf = create_large_test_pdf(pages=5)
    large_pdf_dest = fixtures_dir / "large_sample.pdf"
    os.rename(large_pdf, str(large_pdf_dest))
    
    print(f"✅ Test PDF fixtures created:")
    print(f"   - {small_pdf_dest}")
    print(f"   - {large_pdf_dest}")

if __name__ == "__main__":
    setup_test_fixtures()