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
            
            # --- 2. 検索実行 (成功ルートそのまま) ---
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
                # --- 一覧情報をそのまま確保 ---
                row_el = target_f.locator("#tBody tr").nth(0)
                base_data = [c.inner_text().strip().replace('\n', ' ') for c in row_el.locator("td").all()]

                print("4. 1行目の『入札情報』ボタン(jsBidInfo(0))をクリック...")
                target_f.evaluate("jsBidInfo(0);")
                print("クリック完了。画面の切り替えを待ちます（15秒）...")
                time.sleep(15)
                
                # --- 5. 遷移後の全フレーム調査 (成功したコードを完全再現) ---
                print("\n=== [遷移後のフレーム構造スキャン] ===")
                detail_f = None
                detail_txt = ""
                for i, f in enumerate(page.frames):
                    try:
                        res = f.evaluate('''() => {
                            return {
                                url: window.location.href,
                                text: document.body.innerText.substring(0, 500).replace(/\\n/g, ' '),
                                tables: document.querySelectorAll('table').length
                            }
                        }''')
                        # あなたが以前「うまくいった」と仰った時のログ出力をそのまま維持
                        print(f"Frame[{i}] URL: {res['url']}")
                        print(f"  内容: {res['text']}...")
                        
                        if "PJC503Servlet" in res['url']:
                            detail_f = f
                            detail_txt = f.evaluate("() => document.body.innerText")
                    except: continue

                # --------------------------------------------------
                # スキャンの「後」で、詳細情報を抽出
                # --------------------------------------------------
                if detail_f:
                    print("\n★詳細情報の抽出を開始...")
                    
                    def get_v(label):
                        # ラベルの後の値を抽出
                        m = re.search(rf"{label}\s*([^\n\r]+)", detail_txt)
                        if not m: return ""
                        v = m.group(1).strip()
                        # 価格は指定通り数値化
                        if "価格" in label:
                            v = v.split('(')[0].replace('円', '').replace(',', '').strip()
                        return v

                    detail_fields = [
                        get_v("電子入札案件番号"),
                        get_v("工事・業務名"),
                        get_v("場所"),
                        get_v("予定価格"),
                        get_v("最低制限価格"),
                        get_v("開札（予定）日"),
                        get_v("状態")
                    ]

                    # 入札結果（業者名, 金額1, ...）の抽出
                    bidders_part = []
                    try:
                        # 業者名セクションを抜き出し
                        bid_txt = detail_txt.split("摘要")[-1].split("備考")[0]
                        # 業者名と金額のペアを探す
                        matches = re.findall(r"([^\t\n\r]+?)\s+([0-9,]{4,})", bid_txt)
                        for name, price in matches:
                            n = name.strip()
                            if n and not n.replace(',','').isdigit():
                                bidders_part.extend([n, price.replace(',', '').strip()])
                    except: pass

                    # --- ヘッダー作成 ---
                    header = [f"一覧_{j}" for j in range(len(base_data))]
                    header += ["電子入札案件番号", "工事・業務名", "場所", "予定価格", "最低制限価格", "開札（予定）日", "状態"]
                    for k in range(len(bidders_part) // 2):
                        header.extend([f"業者名_{k+1}", f"金額_{k+1}"])

                    # --- 保存 ---
                    full_row = base_data + detail_fields + bidders_part
                    with open('result.csv', 'w', encoding='utf-8-sig', newline='') as f:
                        writer = csv.writer(f)
                        writer.writerow(header)
                        writer.writerow(full_row)
                    
                    print(f"★全情報をCSVに保存しました: {full_row}")
                    detail_f.evaluate("jsBack();")
                
                print("\n完了。")
            else:
                print("!! 一覧が見つかりませんでした。")

        except Exception as e:
            print(f"重大なエラー: {e}")
        finally:
            browser.close()

if __name__ == "__main__":
    main()
