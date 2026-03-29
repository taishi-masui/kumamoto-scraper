from playwright.sync_api import sync_playwright
import time
import csv
import re

def format_price(v):
    if not v: return ""
    num_str = re.sub(r'[^\d]', '', v.split('(')[0])
    if not num_str: return ""
    return f"¥{int(num_str):,}"

def main():
    targets = [
        {"name": "熊本県", "code": "0100"},
        {"name": "南小国町", "code": "0423"}
    ]

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(user_agent="Mozilla/5.0...", locale="ja-JP")
        
        for target in targets:
            t_name = target["name"]
            t_code = target["code"]
            print(f"\n=== [START] {t_name} (Code: {t_code}) ===")

            try:
                page = context.new_page()
                url = f"https://ebid.kumamoto-idc.pref.kumamoto.jp/PPIAccepter/AccepterServlet?kikan_no={t_code}"
                print(f"[1/6] URLアクセス中: {url}")
                page.goto(url, wait_until="networkidle")
                time.sleep(5)

                print("[2/6] メニュー(jsLink)実行中...")
                menu_f = next((f for f in page.frames if "PJC001Servlet" in f.url), None)
                if not menu_f:
                    print("  !! Error: メニューフレームが見つかりません")
                    page.close()
                    continue
                menu_f.evaluate("jsLink(1,1);")
                time.sleep(5)

                print("[3/6] 検索条件設定中...")
                search_f = None
                for _ in range(10):
                    for f in page.frames:
                        if "PJC501Servlet" in f.url:
                            search_f = f
                            break
                    if search_f: break
                    time.sleep(2)
                
                if search_f:
                    search_f.evaluate("jsSearch();")
                    print("  -> 検索ボタン(jsSearch)を実行しました")
                else:
                    print("  !! Error: 検索フレームが見 acknowledge されません")
                    page.close()
                    continue

                print("[4/6] 一覧表示待ち...")
                list_f = None
                for _ in range(15):
                    for f in page.frames:
                        try:
                            if f.evaluate("() => document.querySelectorAll('#tBody tr').length") > 0:
                                list_f = f
                                break
                        except: continue
                    if list_f: break
                    time.sleep(2)

                if not list_f:
                    print("  !! Error: 一覧データ(tBody)が見つかりません")
                    page.close()
                    continue

                print("[5/6] 1件目の詳細取得を開始...")
                # 実績通り 1件目(i=0) のみ処理
                i = 0
                all_data_rows = []
                
                # 行データの取得
                rows = list_f.locator("#tBody tr")
                row_el = rows.nth(i)
                base_data = [c.inner_text().strip().replace('\n', ' ') for c in row_el.locator("td").all()][0:4]

                print(f"  -> 詳細画面(jsBidInfo({i}))へ遷移中...")
                list_f.evaluate(f"jsBidInfo({i});")
                time.sleep(15) # 実績の待機時間

                detail_f = None
                for f in page.frames:
                    if "PJC503Servlet" in f.url:
                        detail_f = f
                        break
                
                if detail_f:
                    txt = detail_f.evaluate("() => document.body.innerText")
                    def get_v(label):
                        m = re.search(rf"{label}\s*([^\n\r]+)", txt)
                        return m.group(1).strip() if m else ""

                    case_id = get_v("電子入札案件番号")
                    print(f"  -> 取得成功: {case_id}")
                    
                    detail_fields = [
                        f'="{case_id}"', get_v("工事・業務名"), get_v("場所"),
                        format_price(get_v("予定価格")), format_price(get_v("最低制限価格")),
                        get_v("開札（予定）日"), get_v("状態")
                    ]
                    
                    # 業者情報の簡易取得
                    bidders = [""] * 20
                    all_data_rows.append(base_data + detail_fields + bidders)
                else:
                    print("  !! Error: 詳細画面フレームが見つかりません")

                print(f"[6/6] CSV書き出し中: result_{t_name}.csv")
                if all_data_rows:
                    with open(f'result_{t_name}.csv', 'w', encoding='utf-8-sig', newline='') as f:
                        writer = csv.writer(f)
                        writer.writerow(["番号等"] * 31) # 簡易ヘッダー
                        writer.writerows(all_data_rows)
                
                print(f"=== [FINISH] {t_name} 完了 ===\n")
                page.close() # 確実に閉じて次へ

            except Exception as e:
                print(f"  !! 重大なエラーが発生しました: {e}")
                if 'page' in locals(): page.close()

        browser.close()

if __name__ == "__main__":
    main()
