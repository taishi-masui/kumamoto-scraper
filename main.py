from playwright.sync_api import sync_playwright
import time

def main():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        # 行政サイトはCookieや言語設定に敏感なため、日本設定を明示
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
            locale="ja-JP"
        )
        page = context.new_page()

        try:
            print("1. 初期ページにアクセスし、ポップアップを待ち受けます...")
            # window.openが実行されるのを待ち構える
            with context.expect_popup() as popup_info:
                page.goto("https://ebid.kumamoto-idc.pref.kumamoto.jp/PPIAccepter/MainServlet?Error=&Message=", timeout=60000)
            
            # 新しく開かれた本番ウィンドウを取得
            ppi_page = popup_info.value
            ppi_page.wait_for_load_state("networkidle")
            print("本番ページ（ポップアップ）を捕捉しました。")

            # 2. 自治体選択（熊本県）
            print("2. 自治体を選択します...")
            ppi_page.locator(".ATYPE").first.click()
            time.sleep(3)

            # --- 以降、操作対象は ppi_page になる ---
            frm_right = ppi_page.frame_locator('frame[name="frmRIGHT"]')

            print("3. 「入札・契約情報の検索」をクリック...")
            frm_right.get_by_text("入札・契約情報の検索").first.click()
            time.sleep(3)

            print("4. 検索ボタンをクリック...")
            frm_top = frm_right.frame_locator('frame[name="frmTOP"]')
            btn_search = frm_top.locator('input[name="btnSearch"]')
            btn_search.wait_for(state="visible")
            btn_search.click()
            
            print("5. 1ページ目のデータを取得中...")
            time.sleep(5) # サーバーの応答待ち
            
            frm_bottom = frm_right.frame_locator('frame[name="frmBOTTOM"]')
            result_rows = frm_bottom.locator("#tBody tr")
            
            # 結果が出るまで待つ
            result_rows.first.wait_for(state="attached", timeout=30000)
            
            all_rows = result_rows.all()
            print(f"成功！ {len(all_rows)} 件のデータを検出しました。")

            for i, row in enumerate(all_rows):
                # セル内容を取得して整形
                text = row.inner_text().strip().replace('\n', ' ').replace('\t', ' ')
                print(f"Row {i+1}: {text}")

        except Exception as e:
            print(f"エラーが発生しました: {e}")
            # エラー時は ppi_page があればそれを撮影、なければ page を撮影
            target = locals().get('ppi_page', page)
            target.screenshot(path="debug_error.png", full_page=True)
            with open("debug_page.html", "w", encoding="utf-8") as f:
                f.write(target.content())
        finally:
            browser.close()

if __name__ == "__main__":
    main()
