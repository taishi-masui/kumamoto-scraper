from playwright.sync_api import sync_playwright
import time

def main():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
            locale="ja-JP"
        )
        page = context.new_page()

        try:
            print("1. セッション確立のため、一度ベースURLを叩きます...")
            page.goto("https://ebid.kumamoto-idc.pref.kumamoto.jp/PPIAccepter/MainServlet?Error=&Message=", wait_until="networkidle")
            
            print("2. ポップアップを無視し、同じタブで本番URLへ直接遷移します...")
            # 本来 window.open で開かれるURL（TopServlet）を直接指定
            page.goto("https://ebid.kumamoto-idc.pref.kumamoto.jp/PPIAccepter/TopServlet", wait_until="networkidle")
            time.sleep(5)

            # --- ここで「自治体選択」が出るか、直接「メニュー」が出るか ---
            # もし「自治体選択」画面が出ているならクリック
            if page.locator(".ATYPE").first.is_visible():
                print("自治体選択画面を確認。熊本県をクリックします...")
                page.locator(".ATYPE").first.click()
                time.sleep(3)

            # メイン領域 (frmRIGHT) を特定
            frm_right = page.frame_locator('frame[name="frmRIGHT"]')

            print("3. 「入札・契約情報の検索」をクリック...")
            # テキストで見つける（見つからない場合は構造を再確認）
            search_link = frm_right.get_by_text("入札・契約情報の検索").first
            search_link.wait_for(state="visible", timeout=15000)
            search_link.click()
            time.sleep(3)

            print("4. 検索ボタンをクリック...")
            frm_top = frm_right.frame_locator('frame[name="frmTOP"]')
            btn_search = frm_top.locator('input[name="btnSearch"]')
            btn_search.wait_for(state="visible", timeout=15000)
            btn_search.click()
            
            print("5. 1ページ目のデータを取得中...")
            time.sleep(5)
            frm_bottom = frm_right.frame_locator('frame[name="frmBOTTOM"]')
            
            # 結果の行が出るまで待機
            result_rows = frm_bottom.locator("#tBody tr")
            result_rows.first.wait_for(state="attached", timeout=20000)
            
            all_rows = result_rows.all()
            print(f"成功！ {len(all_rows)} 件のデータを検出しました。")

            for i, row in enumerate(all_rows):
                text = row.inner_text().strip().replace('\n', ' ').replace('\t', ' ')
                print(f"Row {i+1}: {text}")

        except Exception as e:
            print(f"エラー発生: {e}")
            # エラー時点の画面と中身を確実に保存
            page.screenshot(path="debug_error.png", full_page=True)
            with open("debug_page.html", "w", encoding="utf-8") as f:
                f.write(page.content())
        finally:
            browser.close()

if __name__ == "__main__":
    main()
