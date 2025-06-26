# Gemini CLI Code Review Integration

## 概要

Gemini CLI を使用した自動コードレビューシステムです。Google の Gemini AI を活用して、Pull Request に対する包括的なコードレビューを自動実行します。

## 特徴

### 🤖 AI駆動レビュー
- **Gemini 2.5 Pro**: 最新のGoogle AI モデルを使用
- **日本語対応**: 日本語でのコメントと解析
- **専門知識**: RAG アプリケーションに特化した知識

### 📊 インテリジェント分析
- **技術スタック自動検出**: Python, Streamlit, Supabase等
- **複雑度スコアリング**: 変更規模に基づく分析
- **フォーカス領域特定**: テスト、セキュリティ、ベクトル検索等

### 🔍 多角的レビュー
- **パフォーマンス分析**: 応答時間とスケーラビリティ
- **セキュリティ評価**: 脆弱性とベストプラクティス
- **アーキテクチャレビュー**: 設計パターンと保守性
- **RAG特化**: ベクトル検索と文書処理に特化

## セットアップ手順

### 1. Gemini API キー取得

1. [Google AI Studio](https://aistudio.google.com/apikey) にアクセス
2. 「Create API Key」をクリック
3. プロジェクトを選択（新規または既存）
4. 生成されたAPIキーをコピー

### 2. GitHub シークレット登録

1. GitHubリポジトリの **Settings** タブ
2. **Secrets and variables** → **Actions**
3. **New repository secret** をクリック
4. 以下を設定：
   - **Name**: `GEMINI_API_KEY`
   - **Secret**: コピーしたAPIキー
5. **Add secret** をクリック

### 3. ワークフロー有効化

ワークフローファイル `.github/workflows/gemini-code-review.yml` は自動的に有効になります。

## 使用方法

### 自動実行トリガー

以下の条件でワークフローが自動実行されます：

```yaml
on:
  pull_request:
    types: [opened, synchronize, reopened]
    paths:
      - "**/*.py"
      - "tests/**/*"
      - "requirements*.txt"
      - "pyproject.toml"
      - "CLAUDE.md"
      - "services/**/*"
      - "components/**/*"
      - "utils/**/*"
```

### レビュープロセス

1. **前処理分析**: 技術スタック・複雑度・フォーカス領域を特定
2. **Gemini CLI実行**: AI による包括的コードレビュー
3. **結果投稿**: PR にレビューコメントを自動投稿
4. **メトリクス収集**: 継続改善のためのデータ蓄積

## レビュー項目

### 🚀 パフォーマンス & スケーラビリティ
- ベクトル検索最適化
- メモリ管理（PDF処理）
- データベースクエリ効率
- 応答時間要件（目標: <500ms）
- キャッシュ戦略

### 🔒 セキュリティ & 信頼性
- 入力検証・サニタイゼーション
- エラーハンドリング
- API キー・認証情報管理
- データプライバシー
- SQLインジェクション防止

### 🧪 テスト & 品質保証
- テストカバレッジ
- モック実装
- エッジケース処理
- 統合テストシナリオ
- エラーシミュレーション

### 🏗️ アーキテクチャ & 設計
- コード構成・モジュール性
- 依存性注入パターン
- 設定管理
- API設計一貫性
- ドキュメント完全性

### 🎯 RAG特化レビュー
- チャンクサイズ・オーバーラップ最適化
- 埋め込みモデル互換性
- ベクトル類似度検索精度
- コンテキストウィンドウ管理
- 引用・ソース追跡

## レビュー出力形式

### 基本構造
```markdown
# 🤖 Gemini CLI Code Review

## 🔬 Code Review Summary
**Overall Assessment**: [Approve/Request Changes/Needs Work]
**Risk Level**: [Low/Medium/High]
**Complexity Score**: [low/medium/high]

## ⚡ Performance Analysis
- **Strengths**: [パフォーマンス改善点]
- **Concerns**: [パフォーマンス課題]
- **Recommendations**: [最適化提案]

## 🛡️ Security Assessment
- **Security Strengths**: [セキュリティ強化点]
- **Security Concerns**: [潜在的脆弱性]
- **Security Recommendations**: [セキュリティ改善提案]

## 📋 Action Items
### 🚨 Critical Issues (Must Fix)
- [ ] [重要課題1]
- [ ] [重要課題2]

### ⚠️ Important Issues (Should Fix)
- [ ] [重要課題1]
- [ ] [重要課題2]

### 💡 Suggestions (Nice to Have)
- [ ] [提案1]
- [ ] [提案2]
```

## 設定オプション

### API 使用制限
- **無料枠**: 毎分60リクエスト、毎日1,000リクエスト
- **プレミアム**: API キー設定で高い制限適用

### ワークフローカスタマイズ

```yaml
# パス フィルタリング調整
paths:
  - "**/*.py"          # Python ファイル
  - "your_custom/**/*" # カスタムパス

# レビュー複雑度調整
complexity-threshold:
  low: 5     # 5ファイル以下
  medium: 10 # 6-10ファイル  
  high: 10+  # 11ファイル以上
```

## トラブルシューティング

### よくある問題

#### API キー エラー
```
Error: GEMINI_API_KEY not found
```
**解決策**: GitHubシークレット `GEMINI_API_KEY` が正しく設定されているか確認

#### API クォータ制限
```
Error: Quota exceeded
```
**解決策**: 
1. API使用量確認
2. 必要に応じてAPI キー アップグレード
3. リクエスト頻度調整

#### ネットワーク エラー
```
Error: Network timeout
```
**解決策**:
1. GitHub Actions ネットワーク状況確認
2. リトライ ロジック追加検討

### デバッグ手順

1. **ワークフロー ログ確認**
   ```bash
   # GitHub Actions タブでログ詳細確認
   ```

2. **ローカル テスト**
   ```bash
   # Gemini CLI 直接実行
   export GEMINI_API_KEY="your-api-key"
   gemini --prompt "Code review test" --output review.md
   ```

3. **設定検証**
   ```bash
   # API キー 動作確認
   curl -H "Authorization: Bearer $GEMINI_API_KEY" \
        https://generativelanguage.googleapis.com/v1/models
   ```

## パフォーマンス最適化

### レビュー時間短縮
- 変更ファイル フィルタリング最適化
- 並列処理活用
- キャッシュ機能利用

### API コスト削減
- プロンプト長最適化
- 不要なファイル除外
- バッチ処理実装

## 継続改善

### メトリクス収集
- レビュー品質スコア
- 実行時間測定
- エラー率監視

### フィードバック ループ
- レビュー精度向上
- プロンプト エンジニアリング改善
- ドメイン知識拡張

## サポートとリソース

### 関連ドキュメント
- [Gemini CLI 公式ドキュメント](https://github.com/google-gemini/gemini-cli)
- [Google AI Studio](https://aistudio.google.com/)
- [GitHub Actions ガイド](https://docs.github.com/actions)

### 参考実装
- Claude Code Review と併用可能
- 他の静的解析ツールとの統合
- カスタム レビュー ルール追加

---

> **注意**: このシステムは自動レビューを提供しますが、重要な変更については人間による最終確認を推奨します。