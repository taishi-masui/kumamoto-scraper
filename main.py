from playwright.sync_api import sync_playwright
import time

def main():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(user_agent="Mozilla/5.0...", locale="ja-JP")
        page = context.new_page()

        try:
            print("1. 検索画面へ移動中...")
            page.goto("https://ebid.kumamoto-idc.pref.kumamoto.jp/PPIAccepter/AccepterServlet?kikan_no=0100", wait_until="networkidle")
            time.sleep(5)
            menu_f = next((f for f in page.frames if "PJC001Servlet" in f.url), page)
            menu_f.evaluate("jsLink(1,1);")
            time.sleep(10)

            print("2. 100件設定と検索実行...")
            search_started = False
            for f in page.frames:
                try:
                    if f.locator('input[name="btnSearch"]').count() > 0:
                        f.locator('select[name="ListCount"]').select_option("100")
                        f.evaluate("jsSearch();")
                        search_started = True
                        break
                except: continue
            
            if not search_started:
                print("検索を開始できませんでした。")
                return

            print("3. 結果一覧の出現を待機（20秒）...")
            time.sleep(20)

            # データがあるフレーム(frmMIDDLE)を特定
            target_f = None
            for f in page.frames:
                try:
                    if f.evaluate("() => document.querySelectorAll('#tBody tr').length") > 0:
                        target_f = f
                        break
                except: continue
            
            if target_f:
                print("★一覧を捕捉。1行目の『入札情報』ボタンをクリックします...")
                # 最初のボタンを狙い撃ち
                btn = target_f.locator('input[value="入札情報"]').first
                
                try:
                    # クリックと同時に新しいウインドウが開くのを待つ
                    with page.expect_popup(timeout=30000) as popup_info:
                        btn.click()
                    detail_page = popup_info.value
                    
                    print("4. 詳細画面（ポップアップ）を解析中...")
                    detail_page.wait_for_load_state("networkidle")
                    time.sleep(5) # 描画待ち
                    
                    # デバッグ情報の保存
                    detail_page.screenshot(path="debug_detail_view.png", full_page=True)
                    with open("debug_detail.html", "w", encoding="utf-8") as f:
                        f.write(detail_page.content())
                    
                    print(f"★詳細画面の捕捉に成功！ URL: {detail_page.url}")
                    # 画面内の主なテキストを抽出
                    text = detail_page.evaluate("() => document.body.innerText.substring(0, 500)")
                    print(f"--- 詳細内容(冒頭) ---\n{text}\n-------------------")
                    
                    detail_page.close()
                except Exception as e:
                    print(f"ポップアップの取得に失敗しました（同一画面遷移の可能性あり）: {e}")
                    # 同一画面遷移だった場合のバックアップ
                    page.screenshot(path="debug_detail_error.png")
            else:
                print("一覧フレームが見つかりませんでした。")

        except Exception as e:
            print(f"重大なエラー: {e}")
        finally:
            browser.close()

if __name__ == "__main__":
    main()
