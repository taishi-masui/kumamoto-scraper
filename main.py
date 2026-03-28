from playwright.sync_api import sync_playwright
import time

def main():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(user_agent="Mozilla/5.0...", locale="ja-JP")
        page = context.new_page()

        try:
            print("1. 一覧画面（100件表示状態）まで移動...")
            page.goto("https://ebid.kumamoto-idc.pref.kumamoto.jp/PPIAccepter/AccepterServlet?kikan_no=0100", wait_until="networkidle")
            time.sleep(5)
            menu_f = next((f for f in page.frames if "PJC001Servlet" in f.url), page)
            menu_f.evaluate("jsLink(1,1);")
            time.sleep(10)

            # 検索実行
            for f in page.frames:
                try:
                    if f.locator('input[name="btnSearch"]').count() > 0:
                        f.locator('select[name="ListCount"]').select_option("100")
                        f.evaluate("jsSearch();")
                        break
                except: continue
            
            print("2. 検索結果の出現を待機...")
            time.sleep(15)
            
            # データがあるフレームを特定
            target_f = None
            for f in page.frames:
                if f.evaluate("() => document.querySelectorAll('#tBody tr').length") > 0:
                    target_f = f
                    break
            
            if target_f:
                print("3. 1行目の「入札情報」ボタンをクリック...")
                # 最初の行にある「入札情報」ボタン（input[value="入札情報"]）を特定
                detail_btn = target_f.locator('input[value="入札情報"]').first
                
                # 新しいウィンドウが開くタイプか、同一画面遷移かを判定するために
                # クリックと同時に「新しいページの出現」を待機する設定で動かします
                with page.expect_popup() as popup_info:
                    detail_btn.click()
                
                detail_page = popup_info.value
                detail_page.wait_for_load_state("networkidle")
                time.sleep(5)
                
                print(f"★詳細画面を捕捉！ URL: {detail_page.url}")
                
                # 詳細画面の内容をスキャン
                detail_content = detail_page.evaluate("() => document.body.innerText.substring(0, 500)")
                print(f"詳細画面の冒頭内容:\n{detail_content}")
                
                # 証拠保存
                detail_page.screenshot(path="debug_detail_view.png", full_page=True)
                with open("debug_detail.html", "w", encoding="utf-8") as f:
                    f.write(detail_page.content())
                
                detail_page.close()
            else:
                print("一覧データが見つかりませんでした。")

        except Exception as e:
            print(f"調査エラー: {e}")
        finally:
            browser.close()

if __name__ == "__main__":
    main()
