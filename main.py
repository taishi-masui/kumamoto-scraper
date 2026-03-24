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
            print("1. 入口にアクセス...")
            page.goto("https://ebid.kumamoto-idc.pref.kumamoto.jp/PPIAccepter/MainServlet?Error=&Message=", wait_until="networkidle")
            
            print("2. 直接遷移で本番画面へ...")
            page.goto("https://ebid.kumamoto-idc.pref.kumamoto.jp/PPIAccepter/TopServlet", wait_until="networkidle")
            time.sleep(2)

            print("3. 自治体（熊本県）を選択...")
            page.locator(".ATYPE").first.click()
            time.sleep(3)

            # --- ここから画像で見えている画面の操作 ---
            # メイン領域のフレーム (frmRIGHT) を指定
            frm_right = page.frame_locator('frame[name="frmRIGHT"]')

            print("4. 「入札・契約情報の検索」をクリック...")
            # 画像の中にある青い背景のボタン（リンク）をクリック
            frm_right.get_by_text("入札・契約情報の検索").first.click()
            time.sleep(3)

            # --- 検索条件画面 (画像2枚目の状態) ---
            print("5. 検索ボタンをクリック...")
            # 検索ボタンは frmRIGHT の中にある frmTOP フレーム内にあります
            frm_top = frm_right.frame_locator('frame[name="frmTOP"]')
            btn_search = frm_top.locator('input[name="btnSearch"]')
            
            # ボタンが見えるまで待ってクリック
            btn_search.wait_for(state="visible", timeout=15000)
            btn_search.click()
            
            # --- 検索結果画面 (画像3枚目の状態) ---
            print("6. 結果を取得中...")
            time.sleep(5) # サーバーの応答を少し長めに待つ

            # 結果リストは frmRIGHT の中にある frmBOTTOM フレーム内にあります
            frm_bottom = frm_right.frame_locator('frame[name="frmBOTTOM"]')
            
            # 検索結果のテーブル行 (#tBody 内の tr) を取得
            result_rows = frm_bottom.locator("#tBody tr")
            
            # 最初のデータが表示されるまで待機
            result_rows.first.wait_for(state="attached", timeout=20000)
            
            rows = result_rows.all()
            print(f"\n===== 1ページ目のデータ（計 {len(rows)} 件）=====")

            for i, row in enumerate(rows):
                # 行内の全セル(td)のテキストを取得
                cols = row.locator("td").all_text_contents()
                # データを掃除（改行除去、空白トリミング）
                clean_cols = [c.strip().replace('\n', ' ').replace('\t', ' ') for c in cols if c.strip()]
                
                if clean_cols:
                    print(f"Row {i+1}: {clean_cols}")

            print("\n==========================================")
            print("おめでとうございます！1ページ目の取得に成功しました。")

        except Exception as e:
            print(f"エラーが発生しました: {e}")
            # 万が一のデバッグ用
            page.screenshot(path="debug_error.png", full_page=True)
            with open("debug_page.html", "w", encoding="utf-8") as f:
                f.write(page.content())
        finally:
            browser.close()

if __name__ == "__main__":
    main()
