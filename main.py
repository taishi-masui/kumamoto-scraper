from playwright.sync_api import sync_playwright
import time

def main():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        # 行政サイト特有の挙動に対応するため、ポップアップを許可する設定
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        page = context.new_page()

        try:
            print("初期ページにアクセス中...")
            # window.openが実行されるのを待ち構える
            with context.expect_popup() as popup_info:
                page.goto("https://ebid.kumamoto-idc.pref.kumamoto.jp/PPIAccepter/MainServlet?Error=&Message=", timeout=60000)
            
            # 新しく開かれたウィンドウ（本番ページ）を取得
            ppi_page = popup_info.value
            ppi_page.wait_for_load_state("networkidle")
            print("本番ページ（ポップアップ）を捕捉しました。")

            # フレームの読み込み待ち
            ppi_page.wait_for_timeout(3000)

            print("検索ボタンを探しています...")
            # 以降、操作対象は ppi_page になります
            search_frame = ppi_page.frame_locator("frame[name='frmRIGHT']").frame_locator("frame[name='frmTOP']")
            btn_search = search_frame.locator("input[name='btnSearch']")

            btn_search.wait_for(state="visible", timeout=30000)
            btn_search.click()
            
            print("検索実行。結果を待機中...")
            time.sleep(5)

            result_frame = ppi_page.frame_locator("frame[name='frmRIGHT']").frame_locator("frame[name='frmBOTTOM']")
            result_rows = result_frame.locator("#tBody tr")
            
            result_rows.first.wait_for(state="attached", timeout=30000)
            
            all_rows = result_rows.all()
            print(f"成功！ {len(all_rows)} 件のデータが見つかりました。")

            for i, row in enumerate(all_rows):
                if i < 10:
                    text = row.inner_text().strip().replace('\n', ' ').replace('\t', ' ')
                    print(f"Row {i}: {text}")

        except Exception as e:
            print(f"エラー発生: {e}")
            # エラー時は捕捉した ppi_page の方を撮影する
            if 'ppi_page' in locals():
                ppi_page.screenshot(path="debug_error.png")
                with open("debug_page.html", "w", encoding="utf-8") as f:
                    f.write(ppi_page.content())
            else:
                page.screenshot(path="debug_error.png")
        finally:
            browser.close()

if __name__ == "__main__":
    main()
