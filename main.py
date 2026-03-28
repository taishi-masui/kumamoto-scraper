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

            print("3. 結果一覧の出現を待機中...")
            target_f = None
            for _ in range(10):
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
                    print("クリック完了。詳細フレームの生成を待ちます...")
                    
                    # --- 変更点：PJC503Servletが出るまで粘り強く待機 ---
                    detail_f = None
                    for _ in range(10):
                        time.sleep(3)
                        detail_f = next((f for f in page.frames if "PJC503Servlet" in f.url), None)
                        if detail_f: break
                    
                    if detail_f:
                        print(f"★詳細フレーム捕捉成功: {detail_f.url}")
                        print("5. 『戻る』を実行 (jsBack)...")
                        detail_f.evaluate("jsBack();")
                        
                        print("一覧への復帰を確認中（15秒待機）...")
                        time.sleep(15)

                        # target_f（一覧フレーム）が有効か再確認
                        if target_f.locator('img[onclick*="jsBidInfo(0)"]').count() > 0:
                            print("★成功：一覧画面に戻りました。")
                        else:
                            print("!! 一覧のボタンが見当たりません。")
                    else:
                        print("!! 詳細フレーム(PJC503)が時間内に生成されませんでした。")
                else:
                    print("!! 詳細ボタンが見つかりませんでした。")
            else:
                print("!! 一覧フレームが見つかりませんでした。")

        except Exception as e:
            print(f"重大なエラー: {e}")
        finally:
            browser.close()

if __name__ == "__main__":
    main()
