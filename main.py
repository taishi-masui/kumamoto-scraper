from playwright.sync_api import sync_playwright
import time

def main():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        # コンテキスト作成時にポップアップ関連の制限を緩める設定
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
            locale="ja-JP",
            ignore_https_errors=True # http/https混在対策
        )
        page = context.new_page()

        try:
            print("1. セッション確立のため、ベースURLにアクセスします...")
            # まずはサイトの入り口にアクセスしてCookieを取得
            page.goto("https://ebid.kumamoto-idc.pref.kumamoto.jp/PPIAccepter/MainServlet?Error=&Message=", 
                      wait_until="networkidle", timeout=60000)
            
            print("2. ポップアップをバイパスし、直接本番フレームページへ遷移します...")
            # 本来 window.open で開かれるURLを、現在のタブで直接開く
            page.goto("https://ebid.kumamoto-idc.pref.kumamoto.jp/PPIAccepter/TopServlet", 
                      wait_until="networkidle", timeout=60000)
            
            # ページが安定するまでしっかり待機
            time.sleep(5)

            print("3. フレーム構造を解析し、検索ボタンを特定します...")
            # このサイトは frmRIGHT > frmTOP という二重フレーム構造です
            frm_right = page.frame_locator('frame[name="frmRIGHT"]')
            frm_top = frm_right.frame_locator('frame[name="frmTOP"]')
            
            # 検索ボタン(btnSearch)を探す
            btn_search = frm_top.locator('input[name="btnSearch"]')
            
            # ボタンが表示されるまで最大20秒待つ
            btn_search.wait_for(state="visible", timeout=20000)
            print("検索ボタンを発見しました。クリックします。")
            btn_search.click()

            print("4. 検索結果（下部フレーム）を待機中...")
            time.sleep(5) # サーバーの応答待ち
            
            # 結果は frmRIGHT > frmBOTTOM に表示されます
            frm_bottom = frm_right.frame_locator('frame[name="frmBOTTOM"]')
            # 結果テーブルの行を特定
            rows = frm_bottom.locator("#tBody tr")
            
            # 最初の行がDOMに出現するまで待機
            rows.first.wait_for(state="attached", timeout=30000)
            
            all_rows = rows.all()
            print(f"成功！ {len(all_rows)} 件のデータを検出しました。")

            for i, row in enumerate(all_rows[:10]):
                # セルごとのテキストを取得して整形
                cols = row.locator("td").all_text_contents()
                clean_cols = [c.strip().replace('\n', ' ') for c in cols if c.strip()]
                if clean_cols:
                    print(f"Row {i}: {clean_cols}")

        except Exception as e:
            print(f"エラーが発生しました: {e}")
            # エラー時点の画面とHTMLを保存（これがあれば原因が100%わかります）
            page.screenshot(path="debug_error.png", full_page=True)
            with open("debug_page.html", "w", encoding="utf-8") as f:
                f.write(page.content())
        finally:
            browser.close()

if __name__ == "__main__":
    main()
