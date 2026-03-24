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
        ppi_page = None

        try:
            print("1. ポータル(URL1)にアクセス...")
            page.goto("http://ebid-portal.kumamoto-idc.pref.kumamoto.jp/", wait_until="networkidle")
            
            print("2. メニュー(rtop)から「入札情報公開」をクリック...")
            # href属性が koukaisystem.html のリンクを狙い撃ち
            page.frame_locator('frame[name="rtop"]').locator('a[href="koukaisystem.html"]').click()
            
            print("3. メイン(rbottom)にボタンが出るのを待機...")
            rbottom = page.frame_locator('frame[name="rbottom"]')
            # 教えていただいたリンク先URLを持つaタグを待機
            target_link = rbottom.locator('a[href*="PPIAccepter/jsp"]').first
            target_link.wait_for(state="visible", timeout=15000)

            print("4. ポップアップを起動...")
            with page.expect_popup() as popup_info:
                target_link.click()
            
            ppi_page = popup_info.value
            ppi_page.wait_for_load_state("networkidle")
            print("5. 本番システム捕捉成功！")

            # --- ここから本番システム内の操作 ---
            print("6. 熊本県を選択...")
            ppi_page.locator(".ATYPE").first.click()
            ppi_page.wait_for_load_state("networkidle")
            time.sleep(3)

            print("7. 検索メニューへ遷移...")
            # ここもフレーム構造なので注意
            frm_right = ppi_page.frame_locator('frame[name="frmRIGHT"]')
            frm_right.get_by_text("入札・契約情報の検索").first.click()
            time.sleep(3)
            
            print("8. 検索実行...")
            frm_top = frm_right.frame_locator('frame[name="frmTOP"]')
            frm_top.locator('input[name="btnSearch"]').click()
            
            print("9. データを取得...")
            time.sleep(5)
            frm_bottom = frm_right.frame_locator('frame[name="frmBOTTOM"]')
            rows_locator = frm_bottom.locator("#tBody tr")
            rows_locator.first.wait_for(state="attached", timeout=30000)
            
            rows = rows_locator.all()
            scraped_data = []
            print(f"\n--- 1ページ目のデータ（{len(rows)}件） ---")
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
            target = ppi_page if ppi_page and not ppi_page.is_closed() else page
            if not target.is_closed():
                target.screenshot(path="debug_error.png", full_page=True)
                with open("debug_page.html", "w", encoding="utf-8") as f:
                    f.write(target.content())
        finally:
            browser.close()

if __name__ == "__main__":
    main()
