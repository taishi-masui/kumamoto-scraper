# --- 前半の関数部分は変更なし ---

def main():
    targets = [
        {
            "name": "熊本県", 
            "code": "0100",
            "filters": {
                "nyusatsu_type": "1002011",
                "gyosyu_list": ["0100010", "0100130", "0100050"],
                "hachu_tanto": "25"
            }
        }
    ]
    
    all_data_rows = []

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(user_agent="Mozilla/5.0...", locale="ja-JP")
        page = context.new_page()

        try:
            for target in targets:
                t_name = target["name"]
                t_code = target["code"]
                f_conf = target["filters"]

                for gyosyu_val in f_conf["gyosyu_list"]:
                    log(f"--- {t_name} (業種コード:{gyosyu_val}) 検索開始 ---")
                    page.goto(f"https://ebid.kumamoto-idc.pref.kumamoto.jp/PPIAccepter/AccepterServlet?kikan_no={t_code}")
                    
                    # 【重要】メニューフレームが現れるのを待つ
                    log("メニュー画面の読み込みを待機中...")
                    menu_f = None
                    for _ in range(15): # 最大15秒待機
                        menu_f = next((f for f in page.frames if "PJC001Servlet" in f.url), None)
                        if menu_f: break
                        time.sleep(1)
                    
                    if not menu_f:
                        log("エラー: メニューフレームが見つかりませんでした。")
                        continue

                    # メニュー内の関数(jsLink)が定義されるまで少し待機して実行
                    time.sleep(2) 
                    try:
                        menu_f.evaluate("jsLink(1,1);")
                    except Exception as e:
                        log(f"jsLink実行失敗、再試行します...: {e}")
                        time.sleep(3)
                        menu_f.evaluate("jsLink(1,1);")
                    
                    # --- 以降の検索処理・取得処理は変更なし ---
