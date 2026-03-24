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
            
            # --- ステップ2：メニューがあるフレームを指定 ---
            print("2. メニューフレーム(rtop)から「入札情報公開」を探してクリック...")
            # rtopフレームを特定
            rtop_frame = page.frame_locator('frame[name="rtop"]')
            
            # フレーム内の「入札情報公開」をクリック
            # ※「入札情報公開サービス」ではなく、画像上の表記「入札情報公開」を狙います
            menu_item = rtop_frame.get_by_text("入札情報公開").first
            menu_item.wait_for(state="visible", timeout=15000)
            menu_item.click()
            
            # --- ステップ3：メインフレーム(rbottom)に画像ボタンが出るのを待つ ---
            print("3. メインフレーム(rbottom)の画像ボタンを待機...")
            rbottom_frame = page.frame_locator('frame[name="rbottom"]')
            img_button = rbottom_frame.locator('img[src*="botan02.gif"]').first
            
            # ボタンが表示されるまでしっかり待つ
            img_button.wait_for(state="visible", timeout=15000)

            print("4. 画像ボタンをクリックしてポップアップ(URL2)を起動...")
            # popupを待機する対象は page です
            with page.expect_popup() as popup_info:
                img_button.click()
            
            # 以降、操作対象は新しく開いたウィンドウ(ppi_page)
            ppi_page = popup_info.value
            ppi_page.wait_for_load_state("networkidle")
            print("5. 本番ウィンドウ(URL2)を捕捉しました。")

            # --- ステップ6以降：以前の成功ルート ---
            print("6. 熊本県を選択...")
            ppi_page.locator(".ATYPE").first.click()
            ppi_page.wait_for_load_state("networkidle")
            time.sleep(3)

            print("7. 入札・契約情報の検索メニューへ...")
            search_menu = ppi_page.get_by_text("入札・契約情報の検索").first
            search_menu.wait_for(state="visible", timeout=20000)
            search_menu.click()
            
            print("8. 検索実行ボタンをクリック...")
            time.sleep(5)
            frm_right = ppi_page.frame_locator('frame[name="frmRIGHT"]')
            frm_top = frm_right.frame_locator('frame[name="frmTOP"]')
            
            btn_search = frm_top.locator('input[name="btnSearch"]')
            btn_search.wait_for(state="visible", timeout=20000)
            btn_search.click()
            
            print("9. データを取得中...")
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
            # 現在の全ページの構造をデバッグ出力
            with open("debug_page.html", "w", encoding="utf-8") as f:
                f.write(target.content())
        finally:
            browser.close()

if __name__ == "__main__":
    main()
