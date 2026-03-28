from playwright.sync_api import sync_playwright
import time

def main():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(user_agent="Mozilla/5.0...", locale="ja-JP")
        page = context.new_page()

        try:
            print("1. 検索条件画面を表示...")
            page.goto("https://ebid.kumamoto-idc.pref.kumamoto.jp/PPIAccepter/AccepterServlet?kikan_no=0100", wait_until="networkidle")
            time.sleep(5)
            menu_f = next((f for f in page.frames if "PJC001Servlet" in f.url), page)
            menu_f.evaluate("jsLink(1,1);")
            
            # --- 2. 検索実行 (全件取得で成功したリトライ方式) ---
            print("2. 検索ボタンを探して実行...")
            search_started = False
            for _ in range(10): 
                for f in page.frames:
                    try:
                        btn = f.locator('input[name="btnSearch"]')
                        if btn.count() > 0:
                            f.evaluate("jsSearch();")
                            print("★検索を実行しました。")
                            search_started = True
                            break
                    except: continue
                if search_started: break
                time.sleep(3)

            # --- 3. 結果一覧の出現を待機 ---
            print("3. 結果一覧の出現を待機中...")
            target_f = None
            for _ in range(10): # 30秒ほど粘る
                for f in page.frames:
                    try:
                        if f.evaluate("() => document.querySelectorAll('#tBody tr').length") > 0:
                            target_f = f
                            break
                    except: continue
                if target_f: break
                time.sleep(3)
            
            if target_f:
                print("4. 1行目の『入札情報』ボタン(jsBidInfo(0))をクリック...")
                bid_info_btn = target_f.locator('img[onclick*="jsBidInfo(0)"], input[onclick*="jsBidInfo(0)"]')
                
                if bid_info_btn.count() > 0:
                    bid_info_btn.first.click()
                    print("クリック完了。画面の切り替えを待ちます（15秒）...")
                    time.sleep(15)
                    
                    # --- 5. 遷移後の全フレーム調査と「戻る」実行 ---
                    print("\n=== [遷移後のフレーム構造スキャン] ===")
                    for i, f in enumerate(page.frames):
                        try:
                            res = f.evaluate('''() => {
                                return {
                                    url: window.location.href,
                                    text: document.body.innerText.substring(0, 500).replace(/\\n/g, ' '),
                                    tables: document.querySelectorAll('table').length
                                }
                            }''')
                            print(f"Frame[{i}] URL: {res['url']}")
                            print(f"  内容: {res['text']}...")

                            # PJC503Servlet（詳細画面）が見つかったら「戻る」を実行
                            if "PJC503Servlet" in res['url']:
                                print(f"★Frame[{i}]で『戻る』を実行します。")
                                f.evaluate("jsBack();")
                        except: continue

                    # 証拠保存
                    time.sleep(5) # 戻り待ち
                    page.screenshot(path="debug_detail_frame.png", full_page=True)
                    with open("debug_detail_frame.html", "w", encoding="utf-8") as file:
                        file.write(page.content())
                    print("\n調査ファイルを保存しました。")
                else:
                    print("!! 詳細ボタンが見つかりませんでした。")
                    page.screenshot(path="debug_not_found.png")
            else:
                print("!! 一覧フレームが見つかりませんでした。")

        except Exception as e:
            print(f"重大なエラー: {e}")
        finally:
            browser.close()

if __name__ == "__main__":
    main()
