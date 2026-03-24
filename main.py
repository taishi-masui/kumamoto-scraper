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
            print("1. 自治体選択（熊本県）...")
            page.goto("https://ebid.kumamoto-idc.pref.kumamoto.jp/PPIAccepter/MainServlet?Error=&Message=", wait_until="networkidle")
            page.locator(".ATYPE").first.click()
            time.sleep(3)

            # メイン領域
            frm_right = page.frame_locator('frame[name="frmRIGHT"]')

            print("2. 「入札・契約情報の検索」をクリック...")
            # 最初の画面にあるリンクテキストで特定
            frm_right.get_by_text("入札・契約情報の検索").first.click()
            time.sleep(3)

            print("3. 検索実行（条件なしで検索ボタン押下）...")
            # 検索条件フレーム内の「検索」ボタン
            frm_top = frm_right.frame_locator('frame[name="frmTOP"]')
            btn_search = frm_top.locator('input[name="btnSearch"]')
            btn_search.wait_for(state="visible")
            btn_search.click()
            
            print("4. 検索結果の待機...")
            # 結果が表示される下のフレーム
            frm_bottom = frm_right.frame_locator('frame[name="frmBOTTOM"]')
            
            # テーブルの行（tr）がアタッチされるのを待つ
            # #tBody tr は検索結果一覧の本体部分です
            result_rows_locator = frm_bottom.locator("#tBody tr")
            result_rows_locator.first.wait_for(state="attached", timeout=30000)
            
            # 1ページ分の行をすべて取得
            rows = result_rows_locator.all()
            print(f"--- 1ページ目のデータ（計 {len(rows)} 件）を表示します ---")

            for i, row in enumerate(rows):
                # 行内の各セル(td)のテキストをリスト化
                cols = row.locator("td").all_text_contents()
                # 余計な空白や改行を除去
                clean_cols = [c.strip().replace('\n', ' ').replace('\t', ' ') for c in cols if c.strip()]
                
                if clean_cols:
                    # ログに出力して構造を確認
                    print(f"Row {i+1}: {clean_cols}")

            print("--- 取得テスト完了 ---")

        except Exception as e:
            print(f"エラー発生: {e}")
            # 失敗した時の状態を保存
            page.screenshot(path="debug_error.png", full_page=True)
            with open("debug_page.html", "w", encoding="utf-8") as f:
                f.write(page.content())
        finally:
            browser.close()

if __name__ == "__main__":
    main()
