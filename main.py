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
            time.sleep(10)

            print("2. 検索ボタンがあるフレームを特定...")
            input_frame = None
            for f in page.frames:
                if f.locator('input[name="btnSearch"]').count() > 0:
                    input_frame = f
                    break
            
            if not input_frame:
                print("検索入力フレームが見つかりません。")
                return

            print("3. 表示件数を100件に設定...")
            input_frame.locator('select[name="ListCount"]').select_option("100")
            time.sleep(2)

            print("4. 検索実行...")
            # エラーの出た全フレーム一斉射撃ではなく、特定したフレームの関数を直接叩く
            input_frame.evaluate("jsSearch();")
            
            all_data = []
            page_num = 1
            
            while True:
                print(f"\n--- ページ {page_num} の待機と解析 ---")
                time.sleep(15) # ページ遷移・構築待ち
                
                # データがあるフレーム(frmMIDDLE)を再特定
                target_f = None
                for f in page.frames:
                    try:
                        if f.evaluate("() => document.querySelectorAll('#tBody tr').length") > 0:
                            target_f = f
                            break
                    except: continue
                
                if not target_f:
                    print("データフレームが見つかりません。終了します。")
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
                # ユーザーから提供されたHTML: <input name="btnNextPage" type="button" value="次頁" onclick="jsNextPage();">
                next_btn = target_f.locator('input[name="btnNextPage"]')
                
                if next_btn.count() > 0 and next_btn.is_enabled():
                    print("「次頁」をクリックします。")
                    # 直接クリックではなく、確実なJS実行で行く（遷移エラー回避のため）
                    target_f.evaluate("jsNextPage();")
                    page_num += 1
                else:
                    print("次頁ボタンがないか、無効（最後のページ）です。")
                    break

            # 保存
            if all_data:
                with open('result.csv', 'w', encoding='utf-8-sig', newline='') as f_csv:
                    writer = csv.writer(f_csv)
                    writer.writerows(all_data)
                print(f"★完了！ 全 {len(all_data)} 件を保存。")

        except Exception as e:
            print(f"エラー発生: {e}")
            page.screenshot(path="debug_error.png")
        finally:
            browser.close()

if __name__ == "__main__":
    main()
