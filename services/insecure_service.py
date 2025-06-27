"""
致命的なセキュリティ問題を含むサービス（テスト用）
このファイルは意図的にバグを含み、AIレビューでの検出テストに使用
"""
import os
import subprocess
import sqlite3


class InsecureService:
    """セキュリティ上の問題があるサービスクラス（テスト用）"""
    
    def __init__(self):
        # 致命的エラー1: ハードコードされた機密情報
        self.api_key = "sk-1234567890abcdef"  # ハードコードされたAPIキー
        self.password = "admin123"  # ハードコードされたパスワード
        
    def search_documents(self, query):
        """SQLインジェクション脆弱性があるメソッド"""
        # 致命的エラー2: SQLインジェクション脆弱性
        conn = sqlite3.connect("database.db")
        cursor = conn.cursor()
        # 直接的なSQL文字列結合（危険！）
        sql = f"SELECT * FROM documents WHERE content LIKE '%{query}%'"
        cursor.execute(sql)
        return cursor.fetchall()
        
    def execute_command(self, user_input):
        """コマンドインジェクション脆弱性があるメソッド"""
        # 致命的エラー3: コマンドインジェクション脆弱性
        command = f"grep -r '{user_input}' /var/logs/"
        result = subprocess.run(command, shell=True, capture_output=True)
        return result.stdout
        
    def get_file_content(self, filename):
        """パストラバーサル脆弱性があるメソッド"""
        # 致命的エラー4: パストラバーサル脆弱性
        filepath = f"/app/uploads/{filename}"
        with open(filepath, 'r') as f:
            return f.read()
            
    def authenticate_user(self, username, password):
        """弱い認証実装"""
        # 致命的エラー5: 弱い認証・平文パスワード比較
        if username == "admin" and password == "admin123":
            return True
        return False
        
    def log_user_action(self, action, user_data):
        """ログインジェクション脆弱性"""
        # 致命的エラー6: ログインジェクション脆弱性
        log_message = f"User action: {action} - Data: {user_data}"
        with open("/var/log/app.log", "a") as f:
            f.write(log_message + "\n")
            
    def deserialize_data(self, data):
        """安全でないデシリアライゼーション"""
        # 致命的エラー7: pickle使用による安全でないデシリアライゼーション
        import pickle
        return pickle.loads(data)
        
    def generate_temp_file(self):
        """安全でない一時ファイル作成"""
        # 致命的エラー8: 安全でない一時ファイル作成
        import tempfile
        temp_file = "/tmp/app_data.tmp"  # 予測可能なファイル名
        with open(temp_file, "w") as f:
            f.write(self.api_key)  # 機密情報を一時ファイルに書き込み
        return temp_file


# 致命的エラー9: グローバルスコープでの機密情報
SECRET_TOKEN = "supersecret123"
DATABASE_PASSWORD = "dbpass456"

def unsafe_eval_function(user_code):
    """eval使用による危険な関数"""
    # 致命的エラー10: eval使用による任意コード実行脆弱性
    return eval(user_code)