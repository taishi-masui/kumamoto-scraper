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
            print("1. 自治体選択画面へアクセス...")
            page.goto("https://ebid.kumamoto-idc.pref.kumamoto.jp/PPIAccepter/MainServlet?Error=&Message=", 
                      wait_until="networkidle")
            
            # 「熊本県」のロゴ（jsClick(1)）をクリック
            print("2. 「熊本県」を選択します...")
            # class="ATYPE" の 0番目（熊本県）をクリック
            page.locator(".ATYPE").first.click()
            
            # 画面遷移とフレームの読み込みを待つ
            time.sleep(5)

            # --- ここから検索画面への潜入 ---
            print("3. 検索メニューフレームを探しています...")
            # 自治体選択後は TopServlet の構造（frmRIGHTなど）に切り替わります
            frm_right = page.frame_locator('frame[name="frmRIGHT"]')
            
            # まずは「工事」などのメニューが出るはずなので、
            # 以前のコードで狙っていた「検索ボタン」があるフレームを探します
            frm_top = frm_right.frame_locator('frame[name="frmTOP"]')
            btn_search = frm_top.locator('input[name="btnSearch"]')

            # もし「検索ボタン」がまだ見えない場合、途中で「工事」などのボタンを押す必要があります
            # 一旦、今の状態でボタンが見えるかチェック
            if btn_search.count() > 0:
                print("検索ボタン発見、クリックします。")
                btn_search.click()
            else:
                print("検索ボタンがまだありません。現在の画面をデバッグ保存します。")
                # ここで止まる場合は、メニュー選択（工事/物品など）が必要です
                raise Exception("Search button not found in current frame")

            print("4. 結果取得...")
            time.sleep(5)
            # (以下、以前の取得ロジックへ続く)

        except Exception as e:
            print(f"エラーまたは分岐点: {e}")
            page.screenshot(path="debug_error.png", full_page=True)
            with open("debug_page.html", "w", encoding="utf-8") as f:
                f.write(page.content())
        finally:
            browser.close()

if __name__ == "__main__":
    main()
