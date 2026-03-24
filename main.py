from playwright.sync_api import sync_playwright
import time

def main():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(user_agent="Mozilla/5.0...", locale="ja-JP")
        page = context.new_page()

        try:
            print("1. ターゲット画面(MainServlet)へ到達...")
            page.goto("https://ebid.kumamoto-idc.pref.kumamoto.jp/PPIAccepter/AccepterServlet?kikan_no=0100", wait_until="networkidle")
            time.sleep(5)

            print("2. 調査で判明した jsLink(1,1) を直接実行...")
            # ターゲットが見つかった frmTOP フレームを取得
            # (frmLEFTでも動くはずですが、メイン画面側のfrmTOPの方が安定します)
            target_frame = page.frame(name="frmTOP") or page.frame(name="frmLEFT")
            
            if target_frame:
                print(f"ターゲットフレーム '{target_frame.name}' で関数を実行します。")
                target_frame.evaluate("jsLink(1,1);")
            else:
                print("!! ターゲットフレームが見つかりません。page全体で試行します。")
                page.evaluate("jsLink(1,1);")

            print("3. 検索条件入力画面(frmRIGHT)の安定を待ちます...")
            time.sleep(7)

            # 4. 最終確認: 検索実行ボタン(btnSearch)が frmRIGHT 内に出現したか
            print("\n=== [最終確認] 検索ボタンの捜索 ===")
            # 構造上、frmRIGHT の中のさらに子フレーム(frmTOPなど)にボタンがある可能性があるため、全フレームを再走査
            found_btn = False
            for f in page.frames:
                btn = f.locator('input[name="btnSearch"]').first
                if btn.count() > 0:
                    print(f"★成功！ フレーム '{f.name}' 内に検索ボタン(btnSearch)を発見しました。")
                    found_btn = True
                    break
            
            if not found_btn:
                print("まだ検索ボタンが見つかりません。")

            # エビデンス保存
            page.screenshot(path="debug_after_click.png", full_page=True)
            with open("debug_page.html", "w", encoding="utf-8") as file:
                file.write(page.content())

        except Exception as e:
            print("実行エラー: " + str(e))
        finally:
            browser.close()

if __name__ == "__main__":
    main()
