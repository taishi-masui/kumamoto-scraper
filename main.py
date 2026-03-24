from playwright.sync_api import sync_playwright
import time

def main():
    with sync_playwright() as p:
        # headlessでも動きやすいよう設定
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            viewport={'width': 1280, 'height': 800}
        )
        page = context.new_page()

        try:
            print("本番URLへ直接アクセスを試みます...")
            # window.open の遷移先である TopServlet へ直接アクセスすることで
            # ポップアップ地獄をバイパスできる可能性があります
            target_url = "https://ebid.kumamoto-idc.pref.kumamoto.jp/PPIAccepter/TopServlet"
            
            # もし直接がダメな場合のために、一応ポップアップ待機も仕込む
            with context.expect_popup(timeout=60000) as popup_info:
                page.goto("https://ebid.kumamoto-idc.pref.kumamoto.jp/PPIAccepter/MainServlet?Error=&Message=", wait_until="load")
            
            ppi_page = popup_info.value
            ppi_page.wait_for_load_state("networkidle")
            print("本番ページを捕捉しました。")

            # 画面が安定するまで少し待機
            time.sleep(5)

            # --- ここからがフレーム操作 ---
            # 構造: frmRIGHT (メイン) > frmTOP (検索ボタンがある上部)
            print("検索フレームを探しています...")
            
            # frame_locator を使い、まず frmRIGHT を特定
            frm_right = ppi_page.frame_locator('frame[name="frmRIGHT"]')
            
            # その中の frmTOP を特定し、検索ボタン(btnSearch)をクリック
            # 念のため、要素が見えるまでしっかり待つ
            btn_search = frm_right.frame_locator('frame[name="frmTOP"]').locator('input[name="btnSearch"]')
            
            print("検索ボタンを待機中...")
            btn_search.wait_for(state="visible", timeout=30000)
            btn_search.click()
            
            print("検索実行。結果を待機中...")
            time.sleep(5) # 反応が遅いので固定待機

            # 結果は frmRIGHT > frmBOTTOM に表示される
            frm_bottom = frm_right.frame_locator('frame[name="frmBOTTOM"]')
            
            # テーブルの行(#tBody tr)が出るまで待機
            result_rows = frm_bottom.locator("#tBody tr")
            result_rows.first.wait_for(state="attached", timeout=30000)
            
            all_rows = result_rows.all()
            print(f"成功！ {len(all_rows)} 件のデータが見つかりました。")

            for i, row in enumerate(all_rows[:10]): # 最初の10件
                text = row.inner_text().strip().replace('\n', ' ').replace('\t', ' ')
                print(f"Row {i}: {text}")

        except Exception as e:
            print(f"エラーが発生しました: {e}")
            # エラー時に「どのページ」を撮るべきか判断
            target = locals().get('ppi_page', page)
            target.screenshot(path="debug_error.png", full_page=True)
            with open("debug_page.html", "w", encoding="utf-8") as f:
                f.write(target.content())
        finally:
            browser.close()

if __name__ == "__main__":
    main()
