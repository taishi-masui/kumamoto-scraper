from playwright.sync_api import sync_playwright
import time

def main():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(user_agent="Mozilla/5.0...", locale="ja-JP")
        page = context.new_page()

        try:
            print("1. 検索実行（調査成功時の手順）...")
            page.goto("https://ebid.kumamoto-idc.pref.kumamoto.jp/PPIAccepter/AccepterServlet?kikan_no=0100", wait_until="networkidle")
            time.sleep(5)
            menu_f = next((f for f in page.frames if "PJC001Servlet" in f.url), page)
            menu_f.evaluate("jsLink(1,1);")
            
            # 検索ボタンを探して実行
            search_started = False
            for _ in range(10): 
                for f in page.frames:
                    try:
                        btn = f.locator('input[name="btnSearch"]')
                        if btn.count() > 0:
                            f.evaluate("jsSearch();")
                            search_started = True
                            break
                    except: continue
                if search_started: break
                time.sleep(3)

            print("2. 一覧の出現を待機...")
            time.sleep(15)
            
            # 一覧フレーム特定
            list_f = next((f for f in page.frames if "PJC502Servlet" in f.url), None)
            
            if list_f:
                print("3. 1件目の詳細ボタンをクリック...")
                # 1件目のボタンを狙い撃ち
                detail_btn = list_f.locator('img[onclick*="jsBidInfo(0)"]')
                detail_btn.first.click()
                
                print("4. 詳細画面(PJC503)の出現を待機...")
                time.sleep(10)
                
                detail_f = next((f for f in page.frames if "PJC503Servlet" in f.url), None)
                if detail_f:
                    print("★詳細画面を捕捉しました。")
                    
                    # 証拠保存（詳細画面）
                    page.screenshot(path="debug_detail_open.png")
                    
                    print("5. 『戻る』ボタンの実行 (jsBack()を直接叩く)...")
                    # 提供いただいたHTMLに基づき、jsBack()を確実に実行します
                    detail_f.evaluate("jsBack();")
                    
                    print("6. 一覧への復帰を待機（10秒）...")
                    time.sleep(10)
                    
                    # 一覧が再表示されたか確認
                    if list_f.locator('img[onclick*="jsBidInfo(0)"]').count() > 0:
                        print("★成功：一覧画面に無事戻れました。")
                        page.screenshot(path="debug_returned_list.png")
                    else:
                        print("!! 戻ったはずですが、一覧のボタンが見当たりません。")
                else:
                    print("!! 詳細フレームが見つかりませんでした。")
            else:
                print("!! 一覧フレームが見つかりませんでした。")

        except Exception as e:
            print(f"重大なエラー: {e}")
        finally:
            browser.close()

if __name__ == "__main__":
    main()
