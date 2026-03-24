from playwright.sync_api import sync_playwright
import time

def main():
    with sync_playwright() as p:
        # GitHub Actions環境では headless=True が必須
        browser = p.chromium.launch(headless=True)
        # ユーザーエージェントを設定して「普通のブラウザ」を装う
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        page = context.new_page()

        print("サイトにアクセス中...")
        # リダイレクト後を見据えて、少し長めに待機
        page.goto("https://ebid.kumamoto-idc.pref.kumamoto.jp/PPIAccepter/MainServlet?Error=&Message=", 
                  wait_until="load", timeout=60000)

        print("フレームの読み込みを待機しています...")
        
        # 1. 最初の大きなフレーム(frmRIGHT)を待つ
        # セレクタが厳しい可能性があるので、frame_locatorで柔軟に取る
        frm_right_locator = page.frame_locator("frame[name='frmRIGHT']")
        
        # 2. その中にある上部フレーム(frmTOP)にある検索ボタンを探す
        # ここで .first を使うのは、複数ヒットによるエラーを防ぐため
        btn_search = frm_right_locator.frame_locator("frame[name='frmTOP']").locator("input[name='btnSearch']")

        try:
            # ボタンが現れるまで最大30秒待つ
            btn_search.wait_for(state="visible", timeout=30000)
            print("検索ボタン発見、クリックします。")
            btn_search.click()
            
            # クリック後の処理待ち（行政サイトはJavaの処理が遅いため少し余裕を持つ）
            time.sleep(3) 

            # 3. 下部フレーム(frmBOTTOM)に結果が出る
            print("結果フレームを確認中...")
            result_rows = frm_right_locator.frame_locator("frame[name='frmBOTTOM']").locator("#tBody tr")
            
            # 結果が出るまで待つ
            result_rows.first.wait_for(state="attached", timeout=30000)
            
            all_rows = result_rows.all()
            print(f"成功！ {len(all_rows)} 件のデータが見つかりました。")

            for i, row in enumerate(all_rows):
                # 最初の5件だけテスト表示
                if i < 5:
                    print(f"Row {i}: {row.inner_text().strip().replace('\\n', ' ')}")

        except Exception as e:
            print(f"エラー発生: {e}")
            # エラー時の画面を保存（これ重要！）
            page.screenshot(path="debug_error.png")
            # ページ全体のHTMLを保存して構造を確認できるようにする
            with open("debug_page.html", "w", encoding="utf-8") as f:
                f.write(page.content())

        browser.close()

if __name__ == "__main__":
    main()
