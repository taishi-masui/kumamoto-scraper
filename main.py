from playwright.sync_api import sync_playwright
import time

def main():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        page = context.new_page()

        try:
            print("サイトにアクセス中...")
            page.goto("https://ebid.kumamoto-idc.pref.kumamoto.jp/PPIAccepter/MainServlet?Error=&Message=", 
                      wait_until="load", timeout=60000)

            # フレームの階層が深いため、少し待機
            page.wait_for_timeout(3000)

            print("検索ボタンを探しています...")
            # frame_locatorを使い、frmRIGHT > frmTOP の順にアクセス
            search_frame = page.frame_locator("frame[name='frmRIGHT']").frame_locator("frame[name='frmTOP']")
            btn_search = search_frame.locator("input[name='btnSearch']")

            btn_search.wait_for(state="visible", timeout=30000)
            btn_search.click()
            
            print("検索実行。結果を待機中...")
            time.sleep(5) # サーバーの応答待ち

            # 結果は frmRIGHT > frmBOTTOM に出る
            result_frame = page.frame_locator("frame[name='frmRIGHT']").frame_locator("frame[name='frmBOTTOM']")
            result_rows = result_frame.locator("#tBody tr")
            
            # 最初の行が出るまで待つ
            result_rows.first.wait_for(state="attached", timeout=30000)
            
            all_rows = result_rows.all()
            print(f"成功！ {len(all_rows)} 件のデータが見つかりました。")

            for i, row in enumerate(all_rows):
                if i < 10:
                    # バックスラッシュをf-stringの外に出してエラー回避
                    raw_text = row.inner_text()
                    clean_text = raw_text.strip().replace('\n', ' ').replace('\t', ' ')
                    print(f"Row {i}: {clean_text}")

        except Exception as e:
            print(f"エラーが発生しました: {e}")
            # エラー発生時の状態を保存
            page.screenshot(path="debug_error.png")
            with open("debug_page.html", "w", encoding="utf-8") as f:
                f.write(page.content())
        finally:
            browser.close()

if __name__ == "__main__":
    main()
