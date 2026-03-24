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
            print("1. 入口にアクセス...")
            page.goto("https://ebid.kumamoto-idc.pref.kumamoto.jp/PPIAccepter/MainServlet?Error=&Message=", wait_until="networkidle")
            
            print("2. 直接遷移で本番画面へ...")
            page.goto("https://ebid.kumamoto-idc.pref.kumamoto.jp/PPIAccepter/TopServlet", wait_until="networkidle")
            time.sleep(2)

            print("3. 自治体（熊本県）を選択...")
            # ロゴ部分をクリック
            page.locator(".ATYPE").first.click()
            
            # ★ここが重要：クリック後の画面変化をしっかり待つ
            time.sleep(5)

            print("4. 検索メニューをクリック（ページ全体から検索）...")
            # フレームを指定せず、ページ全体から「入札・契約情報の検索」というリンクを探す
            # 2箇所あるうち、最初に見つかる方（通常はメイン画面側）をクリック
            search_menu = page.get_by_text("入札・契約情報の検索").first
            search_menu.wait_for(state="visible", timeout=20000)
            search_menu.click()
            
            print("5. 検索ボタンをクリック...")
            time.sleep(5)
            # ここからは構造が安定するのでフレーム指定を復活
            frm_right = page.frame_locator('frame[name="frmRIGHT"]')
            frm_top = frm_right.frame_locator('frame[name="frmTOP"]')
            
            btn_search = frm_top.locator('input[name="btnSearch"]')
            btn_search.wait_for(state="visible", timeout=20000)
            btn_search.click()
            
            print("6. データを取得中...")
            time.sleep(5)
            frm_bottom = frm_right.frame_locator('frame[name="frmBOTTOM"]')
            
            # #tBody tr が存在するか確認
            result_rows = frm_bottom.locator("#tBody tr")
            result_rows.first.wait_for(state="attached", timeout=30000)
            
            scraped_data = []
            rows = result_rows.all()
            print(f"\n===== 取得結果：{len(rows)}件 =====")
            
            for i, row in enumerate(rows):
                cols = row.locator("td").all_text_contents()
                clean_cols = [c.strip().replace('\n', ' ').replace('\t', ' ') for c in cols if c.strip()]
                if clean_cols:
                    scraped_data.append(clean_cols)
                    print(f"Row {i+1}: {clean_cols}")

            if scraped_data:
                with open('result.csv', 'w', encoding='utf-8-sig', newline='') as f:
                    writer = csv.writer(f)
                    writer.writerows(scraped_data)
                print("\nresult.csv に保存しました。")

        except Exception as e:
            print(f"エラー発生: {e}")
            page.screenshot(path="debug_error.png", full_page=True)
            with open("debug_page.html", "w", encoding="utf-8") as f:
                f.write(page.content())
        finally:
            browser.close()

if __name__ == "__main__":
    main()
