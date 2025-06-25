#!/bin/bash

# E2Eテスト環境セットアップスクリプト
# Usage: ./e2e/scripts/setup_e2e.sh [options]

set -e

# スクリプトのディレクトリを取得
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
E2E_ROOT="$(dirname "$SCRIPT_DIR")"
PROJECT_ROOT="$(dirname "$E2E_ROOT")"

# ヘルプ表示
show_help() {
    cat << EOF
E2Eテスト環境セットアップスクリプト

Usage: $0 [options]

Options:
  --browsers=LIST    インストールするブラウザ（comma-separated）
                    Available: chromium,firefox,webkit,all
                    Default: chromium
  --force           既存の設定を上書き
  --skip-venv       仮想環境の作成をスキップ
  --skip-deps       依存関係のインストールをスキップ
  --skip-browsers   ブラウザのインストールをスキップ
  --help            このヘルプを表示

Examples:
  $0                              # 基本セットアップ（Chromiumのみ）
  $0 --browsers=all              # 全ブラウザをインストール
  $0 --browsers=chromium,firefox # ChromiumとFirefoxのみ
  $0 --force                     # 既存設定を上書きして再セットアップ
EOF
}

# デフォルト設定
BROWSERS="chromium"
FORCE=false
SKIP_VENV=false
SKIP_DEPS=false
SKIP_BROWSERS=false

# 引数解析
while [[ $# -gt 0 ]]; do
    case $1 in
        --help|-h)
            show_help
            exit 0
            ;;
        --browsers=*)
            BROWSERS="${1#*=}"
            shift
            ;;
        --force)
            FORCE=true
            shift
            ;;
        --skip-venv)
            SKIP_VENV=true
            shift
            ;;
        --skip-deps)
            SKIP_DEPS=true
            shift
            ;;
        --skip-browsers)
            SKIP_BROWSERS=true
            shift
            ;;
        *)
            echo "Unknown option: $1"
            echo "Use --help for usage information."
            exit 1
            ;;
    esac
done

# プロジェクトディレクトリに移動
cd "$PROJECT_ROOT"

echo "🚀 E2Eテスト環境セットアップ開始"
echo "プロジェクトディレクトリ: $PROJECT_ROOT"
echo "E2Eディレクトリ: $E2E_ROOT"
echo ""

# Python版本チェック
echo "🐍 Python環境チェック..."
python_version=$(python3 --version 2>&1 | cut -d' ' -f2)
echo "Python版本: $python_version"

# 仮想環境セットアップ
if [ "$SKIP_VENV" = false ]; then
    echo ""
    echo "📦 仮想環境セットアップ..."
    
    if [ -d "venv" ] && [ "$FORCE" = false ]; then
        echo "  ✅ 仮想環境は既に存在します（--force で再作成可能）"
    else
        if [ -d "venv" ] && [ "$FORCE" = true ]; then
            echo "  🗑️  既存の仮想環境を削除中..."
            rm -rf venv
        fi
        
        echo "  🔨 新しい仮想環境を作成中..."
        python3 -m venv venv
        echo "  ✅ 仮想環境作成完了"
    fi
    
    # 仮想環境をアクティベート
    source venv/bin/activate
    echo "  🔄 仮想環境をアクティベート"
fi

# 依存関係インストール
if [ "$SKIP_DEPS" = false ]; then
    echo ""
    echo "📚 依存関係インストール..."
    
    # pipアップグレード
    echo "  ⬆️  pipをアップグレード中..."
    pip install --upgrade pip --quiet
    
    # 基本依存関係
    if [ -f "requirements.txt" ]; then
        echo "  📋 基本依存関係をインストール中..."
        pip install -r requirements.txt --quiet
        echo "  ✅ requirements.txt インストール完了"
    else
        echo "  ⚠️  requirements.txt が見つかりません"
    fi
    
    # テスト依存関係
    if [ -f "requirements-test.txt" ]; then
        echo "  🧪 テスト依存関係をインストール中..."
        pip install -r requirements-test.txt --quiet
        echo "  ✅ requirements-test.txt インストール完了"
    else
        echo "  ⚠️  requirements-test.txt が見つかりません"
    fi
fi

# ブラウザインストール
if [ "$SKIP_BROWSERS" = false ]; then
    echo ""
    echo "🌐 Playwrightブラウザインストール..."
    
    # ブラウザリストの処理
    if [ "$BROWSERS" = "all" ]; then
        browser_list="chromium firefox webkit"
        echo "  📦 全ブラウザをインストール中..."
    else
        # カンマ区切りをスペース区切りに変換
        browser_list=$(echo "$BROWSERS" | tr ',' ' ')
        echo "  📦 指定ブラウザをインストール中: $browser_list"
    fi
    
    # 各ブラウザをインストール
    for browser in $browser_list; do
        case $browser in
            chromium|firefox|webkit)
                echo "    🔽 $browser をインストール中..."
                playwright install "$browser" --with-deps
                echo "    ✅ $browser インストール完了"
                ;;
            *)
                echo "    ❌ 未知のブラウザ: $browser"
                echo "    📋 利用可能: chromium, firefox, webkit"
                ;;
        esac
    done
fi

# ディレクトリ構造作成
echo ""
echo "📁 E2Eディレクトリ構造作成..."

# 必要なディレクトリを作成
mkdir -p "$E2E_ROOT/results"
mkdir -p "$E2E_ROOT/fixtures"
mkdir -p "$E2E_ROOT/configs"

echo "  📂 $E2E_ROOT/results - テスト結果保存"
echo "  📂 $E2E_ROOT/fixtures - テスト用データ"
echo "  📂 $E2E_ROOT/configs - 設定ファイル"

# .gitignore作成
echo ""
echo "📝 .gitignore設定..."

gitignore_content="# E2E Test Results
results/
*.webm
*.mp4
*.png
*.jpg
test-results/

# Playwright
playwright-report/
playwright/.cache/

# Temporary files
*.tmp
*.temp"

if [ ! -f "$E2E_ROOT/.gitignore" ] || [ "$FORCE" = true ]; then
    echo "$gitignore_content" > "$E2E_ROOT/.gitignore"
    echo "  ✅ $E2E_ROOT/.gitignore 作成完了"
else
    echo "  ✅ $E2E_ROOT/.gitignore は既に存在します"
fi

# サンプルフィクスチャ作成
echo ""
echo "📄 サンプルフィクスチャ作成..."

sample_pdf_script="$E2E_ROOT/fixtures/generate_sample.py"
if [ ! -f "$sample_pdf_script" ] || [ "$FORCE" = true ]; then
    cat > "$sample_pdf_script" << 'EOF'
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
EOF

    echo "  ✅ サンプルフィクスチャ生成スクリプト作成完了"
else
    echo "  ✅ サンプルフィクスチャ生成スクリプトは既に存在します"
fi

# 設定確認
echo ""
echo "🔍 設定確認..."

# Playwrightの確認
if command -v playwright >/dev/null 2>&1; then
    echo "  ✅ Playwright CLI インストール済み"
else
    echo "  ⚠️  Playwright CLI が見つかりません"
fi

# Pythonモジュールの確認
echo "  🐍 Pythonモジュール確認..."
for module in playwright pytest pytest_html; do
    if python3 -c "import $module" 2>/dev/null; then
        echo "    ✅ $module"
    else
        echo "    ❌ $module (未インストール)"
    fi
done

# 完了メッセージ
echo ""
echo "🎉 E2Eテスト環境セットアップ完了！"
echo ""
echo "📋 次のステップ:"
echo "1. Streamlitアプリを起動: streamlit run streamlit_app.py"
echo "2. E2Eテストを実行: ./e2e/scripts/run_e2e_tests.sh"
echo "3. 詳細ガイドを確認: ./e2e/docs/E2E_TEST_GUIDE.md"
echo ""
echo "🗂️  E2Eフォルダ構造:"
echo "e2e/"
echo "├── scripts/           # 実行スクリプト"
echo "├── docs/              # ドキュメント"
echo "├── results/           # テスト結果"
echo "├── fixtures/          # テスト用データ"
echo "└── configs/           # 設定ファイル"