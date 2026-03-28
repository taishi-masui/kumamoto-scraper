from playwright.sync_api import sync_playwright
import time

def main():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(user_agent="Mozilla/5.0...", locale="ja-JP")
        page = context.new_page()

        try:
            print("1. 検索実行（成功ルート再現）...")
            page.goto("https://ebid.kumamoto-idc.pref.kumamoto.jp/PPIAccepter/AccepterServlet?kikan_no=0100", wait_until="networkidle")
            time.sleep(5)
            menu_f = next((f for f in page.frames if "PJC001Servlet" in f.url), page)
            menu_f.evaluate("jsLink(1,1);")
            
            for _ in range(10): 
                for f in page.frames:
                    try:
                        btn = f.locator('input[name="btnSearch"]')
                        if btn.count() > 0:
                            f.evaluate("jsSearch();")
                            print("★検索を実行しました。")
                            break
                    except: continue
                else:
                    time.sleep(3)
                    continue
                break

            print("2. 一覧の出現を待機...")
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
                print("3. 1行目のボタンをクリック(jsBidInfo(0))...")
                target_f.evaluate("jsBidInfo(0);")
                print("15秒待機して詳細画面の生成を待ちます...")
                time.sleep(15)
                
                # --- 核心部：詳細フレームを特定して戻るを実行 ---
                print("4. 詳細フレーム(PJC503Servlet)を特定...")
                detail_f = next((f for f in page.frames if "PJC503Servlet" in f.url), None)
                
                if detail_f:
                    print(f"★詳細フレーム捕捉成功。URL: {detail_f.url}")
                    # ご提示いただいた構成に基づき jsBack() を実行
                    print("5. 戻るボタンの関数『jsBack();』を実行します...")
                    detail_f.evaluate("jsBack();")
                    
                    print("一覧への復帰を確認中（15秒待機）...")
                    time.sleep(15)

                    # target_f（一覧フレーム）のデータが生きているか確認
                    if target_f.evaluate("() => document.querySelectorAll('#tBody tr').length") > 0:
                        print("★大成功：一覧画面に戻ることに成功しました！")
                    else:
                        print("!! 戻りましたが、一覧のデータが消失または未描画です。")
                else:
                    print("!! 詳細フレーム(PJC503Servlet)が見つかりません。")
            else:
                print("!! 一覧フレームが見つかりませんでした。")

        except Exception as e:
            print(f"重大なエラー: {e}")
        finally:
            browser.close()

if __name__ == "__main__":
    main()
