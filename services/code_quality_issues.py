"""
コード品質上の致命的問題を含むサービス（テスト用）
このファイルは意図的に型安全性やコード品質の問題を含み、AIレビューでの検出テストに使用
"""

# 致命的エラー1: 必要なimportの欠如
# from typing import List, Dict, Optional が不足


class CodeQualityIssueService:
    """コード品質問題があるサービスクラス（テスト用）"""
    
    def __init__(self):
        pass
        
    def process_data(self, data):  # 致命的エラー2: 型ヒント不足
        """型ヒントがない関数"""
        if data == None:  # 致命的エラー3: 'is None' を使うべき
            return
            
        result = []
        for item in data:
            try:
                value = int(item)
                result.append(value)
            except:  # 致命的エラー4: bare except（具体的な例外を指定すべき）
                pass
                
        return result
        
    def divide_numbers(self, a, b):  # 致命的エラー5: 型ヒント不足
        """ゼロ除算チェックなし"""
        # 致命的エラー6: ゼロ除算エラーの未処理
        return a / b
        
    def get_user_data(self, user_id):  # 致命的エラー7: 型ヒント不足
        """不適切なエラーハンドリング"""
        try:
            # 模擬的なデータベースアクセス
            if user_id < 0:
                raise ValueError("Invalid user ID")
            data = {"id": user_id, "name": "User"}
            return data
        except ValueError as e:
            # 致命的エラー8: エラーを隠蔽（ログもなし）
            return None
        except Exception:
            # 致命的エラー9: すべての例外を同じように処理
            return None
            
    def format_currency(self, amount):  # 致命的エラー10: 型ヒント不足
        """不適切な型変換"""
        # 致命的エラー11: 型チェックなしの変換
        return f"${float(amount):.2f}"
        
    def validate_email(self, email):  # 致命的エラー12: 型ヒント不足
        """不十分なバリデーション"""
        # 致命的エラー13: 不適切な文字列チェック
        if "@" in email:
            return True
        return False
        
    def merge_lists(self, list1, list2):  # 致命的エラー14: 型ヒント不足
        """可変引数の危険な使用"""
        # 致命的エラー15: 元のリストを変更してしまう
        list1.extend(list2)
        return list1
        
    def get_config_value(self, key):  # 致命的エラー16: 型ヒント不足
        """設定値の危険な取得"""
        config = {
            "api_url": "https://api.example.com",
            "timeout": 30
        }
        # 致命的エラー17: KeyErrorの未処理
        return config[key]
        
    def process_file_data(self, filepath):  # 致命的エラー18: 型ヒント不足
        """ファイル処理での不適切なエラーハンドリング"""
        # 致命的エラー19: ファイルハンドルのリーク可能性
        file = open(filepath, 'r')
        data = file.read()
        # ファイルクローズを忘れている
        return data.split('\n')
        
    def calculate_average(self, numbers):  # 致命的エラー20: 型ヒント不足
        """ゼロ除算と型チェックの問題"""
        # 致命的エラー21: 空リストでのゼロ除算
        total = sum(numbers)
        return total / len(numbers)


# 致命的エラー22: グローバル変数の危険な使用
GLOBAL_COUNTER = 0

def increment_counter():  # 致命的エラー23: 型ヒント不足
    """グローバル変数の危険な操作"""
    global GLOBAL_COUNTER
    GLOBAL_COUNTER += 1
    return GLOBAL_COUNTER

def unsafe_dictionary_access(data, key):  # 致命的エラー24: 型ヒント不足
    """辞書アクセスの安全性問題"""
    # 致命的エラー25: KeyErrorの未処理
    return data[key]

def mutable_default_argument(items=[]):  # 致命的エラー26: 可変デフォルト引数
    """可変デフォルト引数の危険な使用"""
    items.append("new_item")
    return items