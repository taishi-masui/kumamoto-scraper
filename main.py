from playwright.sync_api import sync_playwright
import time
import csv
import re

def extract_detail(frame):
    """詳細フレーム(PJC503Servlet)から項目を抽出"""
    try:
        text = frame.evaluate("() => document.body.innerText")
        # タブ区切りを想定した抽出
        place = re.search(r"場所\t([^\n]+)", text)
        price = re.search(r"予定価格\t([^\n]+)", text)
        status = re.search(r"状態\t([^\n]+)", text)
        period = re.search(r"工期\t([^\n]+)", text)
        
        return [
            place.group(1).strip() if place else "未設定",
            price.group(1).strip() if price else "非公表",
            status.group(1).strip() if status else "不明",
            period.group(1).strip() if period else "未記載"
        ]
    except:
        return ["エラー", "", "", ""]

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
            
            print("2. 検索実行（リトライ付き）...")
            search_started = False
            for _ in range(10): 
                for f in page.frames:
                    try:
                        btn = f.locator('input[name="btnSearch"]')
                        if btn.count() > 0:
                            f.evaluate("jsSearch();")
                            search_started = True
                            break
                    except: continue
                if search_started: break
                time.sleep(3)

            print("3. 結果一覧の出現を粘り強く待機...")
            list_f = None
            for _ in range(10): # 最大30秒待機
                for f in page.frames:
                    try:
                        # 成功実績のある判定ロジック
                        if f.evaluate("() => document.querySelectorAll('#tBody tr').length") > 0:
                            list_f = f
                            break
                    except: continue
                if list_f: break
                time.sleep(3)
            
            if list_f:
                all_results = []
                rows = list_f.locator("#tBody tr").all()
                target_rows = rows[:10]
                print(f"★一覧を捕捉。{len(target_rows)}件の詳細を取得開始...")

                for i, r in enumerate(target_rows):
                    cols = r.locator("td").all_text_contents()
                    base_data = [c.strip().replace('\n', ' ') for c in cols if c.strip()]
                    
                    if base_data:
                        try:
                            # jsBidInfo(index) ボタンを確実にクリック
                            btn = r.locator(f'img[onclick*="jsBidInfo({i})"]')
                            if btn.count() > 0:
                                btn.first.click()
                                time.sleep(5) # 切り替わりをしっかり待つ
                                
                                # 詳細が表示されるフレーム(PJC503Servlet)を探す
                                detail_f = next((f for f in page.frames if "PJC503Servlet" in f.url), None)
                                if detail_f:
                                    detail_data = extract_detail(detail_f)
                                    base_data.extend(detail_data)
                                    print(f"  [{i+1}/10] 詳細取得成功: {base_data[2][:10]}...")
                                else:
                                    base_data.extend(["詳細フレーム未検出", "", "", ""])
                        except Exception as e:
                            print(f"  [{i+1}/10] エラー: {e}")
                            base_data.extend(["エラー発生", "", "", ""])

                        all_results.append(base_data)

                # CSV保存
                if all_results:
                    with open('result.csv', 'w', encoding='utf-8-sig', newline='') as f:
                        writer = csv.writer(f)
                        writer.writerows(all_results)
                    print(f"★完了！ result.csv を生成しました。")
            else:
                print("!! 一覧フレームが時間内に見つかりませんでした。")

        except Exception as e:
            print(f"重大なエラー: {e}")
        finally:
            browser.close()

if __name__ == "__main__":
    main()
