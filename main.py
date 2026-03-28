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
            menu_f = next((f for f in page.frames if "PJC001Servlet" in f.url), page)
            menu_f.evaluate("jsLink(1,1);")
            time.sleep(10)

            print("2. 表示件数を100件に設定...")
            for f in page.frames:
                try:
                    target_select = f.locator('select[name="ListCount"]')
                    if target_select.count() > 0:
                        f.evaluate('() => { document.querySelector("select[name=\\"ListCount\\"]").value = "100"; }')
                        print(f"★100件設定完了")
                        break
                except: continue

            print("3. 検索実行...")
            page.evaluate('for(let f of window.frames) { if(f.jsSearch) f.jsSearch(); }')
            
            all_data = []
            page_num = 1
            
            while True:
                print(f"\n--- ページ {page_num} の解析開始 ---")
                # 遷移直後はフレームが不安定なため、しっかり待機
                time.sleep(15)
                
                target_f = None
                # データが入っているフレーム(frmMIDDLEなど)を探す
                for f in page.frames:
                    try:
                        if f.evaluate("() => document.querySelectorAll('#tBody tr').length") > 0:
                            target_f = f
                            break
                    except: continue
                
                if not target_f:
                    print("データが見つからないため、終了します。")
                    break

                # データの抽出
                rows = target_f.locator("#tBody tr").all()
                p_data_count = 0
                for r in rows:
                    cols = r.locator("td").all_text_contents()
                    clean_row = [c.strip().replace('\n', ' ').replace('\t', ' ') for c in cols if c.strip()]
                    if clean_row:
                        all_data.append(clean_row)
                        p_data_count += 1
                
                print(f"ページ {page_num}: {p_data_count}件取得 (累計: {len(all_data)}件)")

                # 「次頁」ボタンの調査とクリック
                # 構造から name="btnNextPage" を狙い撃ちします
                next_btn = target_f.locator('input[name="btnNextPage"]')
                
                # ボタンが存在し、かつ disabled でないことを確認
                if next_btn.count() > 0 and next_btn.is_enabled():
                    print("「次頁」ボタンを発見。クリックして次へ進みます。")
                    next_btn.click()
                    page_num += 1
                else:
                    print("「次頁」ボタンがないか、無効化されています。全件取得完了です。")
                    break

            # 最終的なCSV保存
            if all_data:
                with open('result.csv', 'w', encoding='utf-8-sig', newline='') as f_csv:
                    writer = csv.writer(f_csv)
                    writer.writerows(all_data)
                print(f"\n★成功！ 全 {len(all_data)} 件を result.csv に保存しました。")

        except Exception as e:
            print(f"実行中にエラー: {e}")
        finally:
            browser.close()

if __name__ == "__main__":
    main()
