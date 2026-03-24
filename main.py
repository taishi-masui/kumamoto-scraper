from playwright.sync_api import sync_playwright
import time
import csv

def main():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
            locale="ja-JP"
        )
        page = context.new_page()

        try:
            print("1. 本番システムへアクセス...")
            # セッション確立
            page.goto("https://ebid.kumamoto-idc.pref.kumamoto.jp/PPIAccepter/MainServlet?Error=&Message=", wait_until="networkidle")
            page.goto("https://ebid.kumamoto-idc.pref.kumamoto.jp/PPIAccepter/TopServlet", wait_until="networkidle")
            time.sleep(3)

            print("2. 熊本県を選択 (jsClick(1)を実行)...")
            # 調査で判明した関数を直接実行して確実に遷移させる
            page.evaluate("jsClick(1);")
            
            print("3. メニュー画面のロードを待機...")
            time.sleep(5) 
            
            # --- ここからメニュー操作 ---
            # サイト構造に基づき、右フレーム(frmRIGHT)を捕捉
            frm_right = page.frame_locator('frame[name="frmRIGHT"]')
            
            print("4. 「入札・契約情報の検索」をクリック...")
            # テキストによる特定。念のため複数の候補で試行
            search_menu = frm_right.get_by_text("入札・契約情報の検索").first
            search_menu.click()
            time.sleep(3)

            # --- ここから検索実行 ---
            print("5. 検索実行ボタンをクリック...")
            # 検索ボタンは frmRIGHT 内の frmTOP にある
            frm_top = frm_right.frame_locator('frame[name="frmTOP"]')
            btn_search = frm_top.locator('input[name="btnSearch"]')
            btn_search.click()

            # --- ここからデータ抽出 ---
            print("6. 検索結果を取得中...")
            time.sleep(5)
            # 結果テーブルは frmRIGHT 内の frmBOTTOM にある
            frm_bottom = frm_right.frame_locator('frame[name="frmBOTTOM"]')
            rows_locator = frm_bottom.locator("#tBody tr")
            
            # データ行が出るまで待つ
            rows_locator.first.wait_for(state="attached", timeout=20000)
            
            rows = rows_locator.all()
            scraped_data = []
            print(f"\n--- 取得結果（{len(rows)}件） ---")
            
            for i, row in enumerate(rows):
                cols = row.locator("td").all_text_contents()
                # 余計な空白や改行を除去
                clean_cols = [c.strip().replace('\n', ' ').replace('\t', ' ') for c in cols if c.strip()]
                if clean_cols:
                    scraped_data.append(clean_cols)
                    print(f"Row {i+1}: {clean_cols}")

            if scraped_data:
                with open('result.csv', 'w', encoding='utf-8-sig', newline='') as f:
                    writer = csv.writer(f)
                    writer.writerows(scraped_data)
                print("\n成功：result.csv に保存しました。")

        except Exception as e:
            print(f"\nエラー発生: {e}")
            page.screenshot(path="debug_final.png", full_page=True)
            with open("debug_final.html", "w", encoding="utf-8") as f:
                f.write(page.content())
        finally:
            browser.close()

if __name__ == "__main__":
    main()
