#!/bin/bash
# Gemini API Key動作確認スクリプト

echo "🔍 Gemini API キー動作確認開始"
echo "======================================="

# 環境変数確認
if [ -z "$GEMINI_API_KEY" ]; then
    echo "❌ GEMINI_API_KEY環境変数が設定されていません"
    exit 1
else
    echo "✅ GEMINI_API_KEY環境変数が設定されています"
    echo "キー長: ${#GEMINI_API_KEY} 文字"
    echo "キー前缀: ${GEMINI_API_KEY:0:10}..."
fi

echo ""
echo "🧪 Gemini CLI 基本テスト"
echo "======================================="

# 簡単なプロンプトでテスト
echo "Hello world" | timeout 30 gemini --model "gemini-2.5-pro" 2>&1 | head -20

echo ""
echo "📊 テスト完了"