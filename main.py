import json
import os
import urllib.request

def send_to_spreadsheet(data):
    """GASのウェブアプリURLにテストデータを送信する"""
    url = os.environ.get("GAS_WEBAPP_URL")
    if not url:
        print("Error: GAS_WEBAPP_URL が設定されていません。")
        return

    print(f"送信先URL: {url[:30]}...") # セキュリティのため一部表示

    try:
        # テスト用の文字データ（配列の配列形式）
        test_data = [
            ["疎通テスト成功", "2026-03-29", "Pythonから送信されました"]
        ]
        
        req_data = json.dumps(test_data).encode('utf-8')
        req = urllib.request.Request(
            url, 
            data=req_data, 
            method='POST', 
            headers={'Content-Type': 'application/json'}
        )
        
        with urllib.request.urlopen(req) as res:
            response_body = res.read().decode('utf-8')
            print(f"GASからのレスポンス: {response_body}")
            
    except Exception as e:
        print(f"送信エラーが発生しました: {e}")

if __name__ == "__main__":
    send_to_spreadsheet(None)
