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
                print(f"[1/5] URLアクセス中...")
                page.goto(url, wait_until="networkidle")
                time.sleep(5)

                # --- 実績のあるフレーム探索 ---
                print("[2/5] メニュー(jsLink)実行中...")
                menu_f = None
                for f in page.frames:
                    if "PJC001Servlet" in f.url:
                        menu_f = f
                        break
                
                if menu_f:
                    menu_f.evaluate("jsLink(1,1);")
                    time.sleep(5)
                else:
                    print("  !! Error: メニューフレーム不在")
                    page.close()
                    continue

                # --- 実績のある検索ボタン総当たり ---
                print("[3/5] 検索ボタン実行中...")
                search_started = False
                for _ in range(10): 
                    for f in page.frames:
                        try:
                            # 実績通り、ListCountがあるフレームでjsSearchを実行
                            sel = f.locator('select[name="ListCount"]')
                            if sel.count() > 0:
                                f.evaluate("jsSearch();")
                                search_started = True
                                break
                        except: continue
                    if search_started: break
                    time.sleep(3)

                if not search_started:
                    print("  !! Error: 検索実行失敗")
                    page.close()
                    continue

                # --- 実績のある一覧取得 ---
                print("[4/5] 一覧から1件目を取得中...")
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

                if list_f:
                    # 1件目のみ処理
                    i = 0
                    rows = list_f.locator("#tBody tr")
                    row_el = rows.nth(i)
                    base_data = [c.inner_text().strip().replace('\n', ' ') for c in row_el.locator("td").all()][0:4]

                    # 詳細(jsBidInfo)
                    list_f.evaluate(f"jsBidInfo({i});")
                    time.sleep(15)

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
                        print(f"  -> 成功: {case_id}")
                        
                        detail_fields = [
                            f'="{case_id}"', get_v("工事・業務名"), get_v("場所"),
                            format_price(get_v("予定価格")), format_price(get_v("最低制限価格")),
                            get_v("開札（予定）日"), get_v("状態")
                        ]
                        
                        # 保存
                        print(f"[5/5] 保存中: result_{t_name}.csv")
                        with open(f'result_{t_name}.csv', 'w', encoding='utf-8-sig', newline='') as f_out:
                            writer = csv.writer(f_out)
                            writer.writerow(["Header"]) 
                            writer.writerow(base_data + detail_fields)
                    else:
                        print("  !! Error: 詳細フレーム不在")
                
                print(f"=== [FINISH] {t_name} 完了 ===\n")
                page.close()

            except Exception as e:
                print(f"  !! エラー: {e}")
                if 'page' in locals(): page.close()

        browser.close()

if __name__ == "__main__":
    main()
