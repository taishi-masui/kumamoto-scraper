from playwright.sync_api import sync_playwright
import time

def main():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(user_agent="Mozilla/5.0...", locale="ja-JP")
        page = context.new_page()

        try:
            print("1. 検索実行（デフォルト件数）...")
            page.goto("https://ebid.kumamoto-idc.pref.kumamoto.jp/PPIAccepter/AccepterServlet?kikan_no=0100", wait_until="networkidle")
            time.sleep(5)
            menu_f = next((f for f in page.frames if "PJC001Servlet" in f.url), page)
            menu_f.evaluate("jsLink(1,1);")
            time.sleep(10)

            # 検索実行
            for f in page.frames:
                try:
                    if f.locator('input[name="btnSearch"]').count() > 0:
                        f.evaluate("jsSearch();")
                        break
                except: continue
            
            print("2. 結果一覧の出現を待機...")
            time.sleep(15)

            target_f = None
            for f in page.frames:
                try:
                    if f.evaluate("() => document.querySelectorAll('#tBody tr').length") > 0:
                        target_f = f
                        break
                except: continue
            
            if target_f:
                print("3. 1行目の『入札情報』ボタン(jsBidInfo(0))をクリック...")
                # 確実に1行目のimgタグを特定してクリック
                bid_info_btn = target_f.locator('img[onclick*="jsBidInfo(0)"]')
                
                if bid_info_btn.count() > 0:
                    bid_info_btn.click()
                    print("クリック完了。詳細画面への切り替えを待ちます（15秒）...")
                    time.sleep(15)
                    
                    # 画面が切り替わった後の全フレームを再スキャン
                    print("\n=== [遷移後のフレーム構造スキャン] ===")
                    for i, f in enumerate(page.frames):
                        try:
                            # フォームやテーブルの数を調査
                            info = f.evaluate('''() => {
                                return {
                                    url: window.location.href,
                                    text: document.body.innerText.substring(0, 300).replace(/\\n/g, ' '),
                                    tables: document.querySelectorAll('table').length,
                                    inputs: document.querySelectorAll('input').length
                                }
                            }''')
                            print(f"Frame[{i}] URL: {info['url']}")
                            print(f"  内容冒頭: {info['text']}...")
                            print(f"  テーブル数: {info['tables']} | 入力要素数: {info['inputs']}")
                        except: continue

                    # 証拠保存（この画像に詳細画面が映っているはずです）
                    page.screenshot(path="debug_detail_frame.png", full_page=True)
                    with open("debug_detail_frame.html", "w", encoding="utf-8") as file:
                        file.write(page.content())
                else:
                    print("!! ボタンが見つかりませんでした。")
            else:
                print("!! 一覧が見つかりませんでした。")

        except Exception as e:
            print(f"重大なエラー: {e}")
        finally:
            browser.close()

if __name__ == "__main__":
    main()
