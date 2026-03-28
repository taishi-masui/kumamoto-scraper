from playwright.sync_api import sync_playwright
import time
import csv

def main():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(user_agent="Mozilla/5.0...", locale="ja-JP")
        page = context.new_page()

        try:
            print("1. 検索条件画面を表示...")
            page.goto("https://ebid.kumamoto-idc.pref.kumamoto.jp/PPIAccepter/AccepterServlet?kikan_no=0100", wait_until="networkidle")
            time.sleep(5)
            
            # メニューから検索画面呼び出し
            menu_f = next((f for f in page.frames if "PJC001Servlet" in f.url), page)
            menu_f.evaluate("jsLink(1,1);")
            
            # --- 2. 100件設定 & 検索実行 (リトライ付き) ---
            print("2. 検索ボタンを探して100件設定＆実行...")
            search_started = False
            for _ in range(10): # 最大10回リトライ
                for f in page.frames:
                    try:
                        # セレクトボックスがあれば100件に設定
                        sel = f.locator('select[name="ListCount"]')
                        if sel.count() > 0:
                            sel.select_option("100")
                            print("★100件に設定しました。")
                            
                        # 検索ボタンがあれば実行
                        btn = f.locator('input[name="btnSearch"]')
                        if btn.count() > 0:
                            f.evaluate("jsSearch();")
                            print("★検索を実行しました。")
                            search_started = True
                            break
                    except: continue
                if search_started: break
                time.sleep(3)

            # --- 3. データ抽出ループ ---
            all_data = []
            page_num = 1
            
            while True:
                print(f"\n--- ページ {page_num} 解析中 ---")
                time.sleep(15) # 遷移待ち

                target_f = None
                # データがあるフレームを粘り強く探す
                for _ in range(5):
                    for f in page.frames:
                        try:
                            if f.evaluate("() => document.querySelectorAll('#tBody tr').length") > 0:
                                target_f = f
                                break
                        except: continue
                    if target_f: break
                    time.sleep(3)
                
                if not target_f:
                    print("データが見つかりません。終了します。")
                    break

                # データの抽出
                rows = target_f.locator("#tBody tr").all()
                count = 0
                for r in rows:
                    cols = r.locator("td").all_text_contents()
                    clean_row = [c.strip().replace('\n', ' ') for c in cols if c.strip()]
                    if clean_row:
                        all_data.append(clean_row)
                        count += 1
                
                print(f"ページ {page_num}: {count}件取得 (累計: {len(all_data)}件)")

                # 「次頁」ボタンのチェック
                try:
                    next_btn = target_f.locator('input[name="btnNextPage"]')
                    if next_btn.count() > 0 and next_btn.is_enabled():
                        print("「次頁」をクリックします。")
                        target_f.evaluate("jsNextPage();")
                        page_num += 1
                    else:
                        print("最後のページです。")
                        break
                except:
                    print("ボタン操作中にエラーが発生しました（遷移中）。終了します。")
                    break

            # 保存
            if all_data:
                with open('result.csv', 'w', encoding='utf-8-sig', newline='') as f_csv:
                    writer = csv.writer(f_csv)
                    writer.writerows(all_data)
                print(f"★完了！ 全 {len(all_data)} 件を保存。")

        except Exception as e:
            print(f"重大なエラー: {e}")
            page.screenshot(path="debug_error.png")
        finally:
            browser.close()

if __name__ == "__main__":
    main()
