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

            print("3. 結果一覧の出現を待機中...")
            target_f = None
            for _ in range(10):
                for f in page.frames:
                    try:
                        if f.evaluate("() => document.querySelectorAll('#tBody tr').length") > 0:
                            target_f = f
                            break
                    except: continue
                if target_f: break
                time.sleep(3)
            
            if target_f:
                # 一覧の1件目の基本情報を先に取得
                row = target_f.locator("#tBody tr").first
                base_data = [c.strip().replace('\n', ' ') for c in row.locator("td").all_text_contents() if c.strip()]

                print("4. 1行目の『入札情報』ボタン(jsBidInfo(0))をクリック...")
                target_f.evaluate("jsBidInfo(0);")
                print("クリック完了。15秒待機します...")
                time.sleep(15)
                
                # --- 詳細フレーム特定と抽出 ---
                detail_f = next((f for f in page.frames if "PJC503Servlet" in f.url), None)
                
                if detail_f:
                    print("★詳細フレーム捕捉。データを抽出します。")
                    detail_text = detail_f.evaluate("() => document.body.innerText")
                    
                    # 正規表現で「場所」と「予定価格」を抜き出し
                    place = re.search(r"場所\t([^\n]+)", detail_text)
                    price = re.search(r"予定価格\t([^\n]+)", detail_text)
                    
                    base_data.append(place.group(1).strip() if place else "場所未取得")
                    base_data.append(price.group(1).strip() if price else "価格未取得")
                    
                    # CSV保存
                    with open('result.csv', 'w', encoding='utf-8-sig', newline='') as f:
                        writer = csv.writer(f)
                        writer.writerow(base_data)
                    
                    print(f"★完了！ 1件目のデータ（詳細付き）を保存しました: {base_data}")

                    # 戻る操作の確認
                    print("5. 一覧へ戻ります...")
                    detail_f.evaluate("jsBack();")
                    time.sleep(5)
                else:
                    print("!! 詳細フレームが見つかりませんでした。")
            else:
                print("!! 一覧フレームが見つかりませんでした。")

        except Exception as e:
            print(f"重大なエラー: {e}")
        finally:
            browser.close()

if __name__ == "__main__":
    main()
