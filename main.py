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
            print("1. URL1（ポータル）にアクセス...")
            page.goto("http://ebid-portal.kumamoto-idc.pref.kumamoto.jp/", wait_until="networkidle")
            
            print("2. 画像ボタンをクリックしてポップアップ(URL2)を起動...")
            # 画像のソース名でフィルタリングしてクリック
            with context.expect_popup() as popup_info:
                # 'botan02.gif' を含むimg要素をクリック
                page.locator('img[src*="botan02.gif"]').first.click()
            
            # 操作対象を新しく開いたウィンドウに切り替え
            ppi_page = popup_info.value
            ppi_page.wait_for_load_state("networkidle")
            print("3. 本番ウィンドウ(URL2)を捕捉しました。")

            # 4. 自治体（熊本県）を選択
            print("4. 熊本県を選択...")
            # ここでURL3に更新される
            ppi_page.locator(".ATYPE").first.click()
            ppi_page.wait_for_load_state("networkidle")
            time.sleep(3)

            # 5. 「入札・契約情報の検索」をクリック
            print("5. 入札・契約情報の検索メニューへ...")
            # ページ全体からテキストで探す
            search_menu = ppi_page.get_by_text("入札・契約情報の検索").first
            search_menu.wait_for(state="visible", timeout=20000)
            search_menu.click()
            
            # 6. 検索実行
            print("6. 検索実行ボタンをクリック...")
            time.sleep(5)
            # 構造：frmRIGHT > frmTOP
            frm_right = ppi_page.frame_locator('frame[name="frmRIGHT"]')
            frm_top = frm_right.frame_locator('frame[name="frmTOP"]')
            
            btn_search = frm_top.locator('input[name="btnSearch"]')
            btn_search.wait_for(state="visible", timeout=20000)
            btn_search.click()
            
            # 7. データ取得（1ページ目）
            print("7. データを取得中...")
            time.sleep(5)
            frm_bottom = frm_right.frame_locator('frame[name="frmBOTTOM"]')
            result_rows = frm_bottom.locator("#tBody tr")
            result_rows.first.wait_for(state="attached", timeout=30000)
            
            rows = result_rows.all()
            scraped_data = []
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
                print(f"完了：{len(scraped_data)}件を保存しました。")

        except Exception as e:
            print(f"エラー詳細: {e}")
            target = locals().get('ppi_page', page)
            target.screenshot(path="debug_error.png", full_page=True)
            with open("debug_page.html", "w", encoding="utf-8") as f:
                f.write(target.content())
        finally:
            browser.close()

if __name__ == "__main__":
    main()
