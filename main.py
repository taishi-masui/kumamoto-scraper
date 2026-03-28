from playwright.sync_api import sync_playwright
import time
import csv
import re

def main():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(user_agent="Mozilla/5.0...", locale="ja-JP")
        page = context.new_page()

        try:
            print("1. 検索条件画面を表示...")
            page.goto("https://ebid.kumamoto-idc.pref.kumamoto.jp/PPIAccepter/AccepterServlet?kikan_no=0100", wait_until="networkidle")
            time.sleep(5)
            menu_f = next((f for f in page.frames if "PJC001Servlet" in f.url), page)
            menu_f.evaluate("jsLink(1,1);")
            
            # --- 2. 検索実行 (全件取得で成功したリトライ方式) ---
            print("2. 検索ボタンを探して実行...")
            search_started = False
            for _ in range(10): 
                for f in page.frames:
                    try:
                        btn = f.locator('input[name="btnSearch"]')
                        if btn.count() > 0:
                            f.evaluate("jsSearch();")
                            print("★検索を実行しました。")
                            search_started = True
                            break
                    except: continue
                if search_started: break
                time.sleep(3)

            # --- 3. 結果一覧の出現を待機 ---
            print("3. 結果一覧の出現を待機中...")
            target_f = None
            for _ in range(10): # 30秒ほど粘る
                for f in page.frames:
                    try:
                        if f.evaluate("() => document.querySelectorAll('#tBody tr').length") > 0:
                            target_f = f
                            break
                    except: continue
                if target_f: break
                time.sleep(3)
            
            if target_f:
                # 一覧の1件目の情報を取得
                row = target_f.locator("#tBody tr").first
                base_data = [c.strip().replace('\n', ' ') for c in row.locator("td").all_text_contents() if c.strip()]

                print("4. 1行目の『入札情報』ボタン(jsBidInfo(0))をクリック...")
                bid_info_btn = target_f.locator('img[onclick*="jsBidInfo(0)"], input[onclick*="jsBidInfo(0)"]')
                
                if bid_info_btn.count() > 0:
                    bid_info_btn.first.click()
                    print("クリック完了。画面の切り替えを待ちます（15秒）...")
                    time.sleep(15)
                    
                    # --- 5. 遷移後の全フレーム調査 (成功したコードをそのまま再現) ---
                    print("\n=== [遷移後のフレーム構造スキャン] ===")
                    detail_f = None # あとで使うために器だけ用意
                    for i, f in enumerate(page.frames):
                        try:
                            res = f.evaluate('''() => {
                                return {
                                    url: window.location.href,
                                    text: document.body.innerText.substring(0, 500).replace(/\\n/g, ' '),
                                    tables: document.querySelectorAll('table').length
                                }
                            }''')
                            print(f"Frame[{i}] URL: {res['url']}")
                            print(f"  内容: {res['text']}...")

                            # 成功した時、詳細が出ていた Frame[6] (PJC503Servlet) を特定
                            if "PJC503Servlet" in res['url']:
                                detail_f = f
                        except: continue

                    # --- スキャンの「後」で抽出と戻るを実行 ---
                    if detail_f:
                        print("\n★詳細フレームを特定。データを保存して戻ります。")
                        full_text = detail_f.evaluate("() => document.body.innerText")
                        
                        # 正規表現で抽出
                        place = re.search(r"場所\t([^\n]+)", full_text)
                        price = re.search(r"予定価格\t([^\n]+)", full_text)
                        
                        base_data.append(place.group(1).strip() if place else "場所取得失敗")
                        base_data.append(price.group(1).strip() if price else "価格取得失敗")

                        with open('result.csv', 'w', encoding='utf-8-sig', newline='') as csvfile:
                            writer = csv.writer(csvfile)
                            writer.writerow(base_data)
                        
                        # ご提示の onclick="jsBack();" を実行
                        detail_f.evaluate("jsBack();")
                        print("jsBack() を実行しました。")
                    
                    # 証拠保存
                    page.screenshot(path="debug_detail_frame.png", full_page=True)
                    print("\n調査ファイルを保存しました。")
                else:
                    print("!! 詳細ボタンが見つかりませんでした。")
            else:
                print("!! 一覧フレームが見つかりませんでした。")

        except Exception as e:
            print(f"重大なエラー: {e}")
        finally:
            browser.close()

if __name__ == "__main__":
    main()
