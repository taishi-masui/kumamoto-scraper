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
    # テスト対象
    targets = [
        {"name": "熊本県", "code": "0100"},
        {"name": "熊本市", "code": "0200"},
        {"name": "南小国町", "code": "0423"} # あえて0件の地区を入れる
    ]

    all_data_rows = []
    header = ["施行番号/案件番号", "業種 種別", "工事・業務名", "契約方法",
              "電子入札案件番号", "工事・業務名", "場所", "予定価格", "最低制限価格", "開札（予定）日", "状態"]
    for k in range(1, 11): header.extend([f"業者{k}", f"金額{k}"])

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(user_agent="Mozilla/5.0...", locale="ja-JP")
        page = context.new_page()

        try:
            for target in targets:
                t_name = target["name"]
                t_code = target["code"]
                print(f"--- {t_name} (Code:{t_code}) の取得を開始します ---")

                page.goto(f"https://ebid.kumamoto-idc.pref.kumamoto.jp/PPIAccepter/AccepterServlet?kikan_no={t_code}", wait_until="networkidle")
                time.sleep(5)

                menu_f = next((f for f in page.frames if "PJC001Servlet" in f.url), page)
                menu_f.evaluate("jsLink(1,1);")
                
                search_started = False
                for _ in range(10): 
                    for f in page.frames:
                        try:
                            sel = f.locator('select[name="ListCount"]')
                            if sel.count() > 0:
                                sel.select_option("100")
                                f.evaluate("jsSearch();")
                                search_started = True
                                break
                        except: continue
                    if search_started: break
                    time.sleep(3)

                # --- 【修正】0件でも止まらないように判定を追加 ---
                target_f = None
                for _ in range(10):
                    for f in page.frames:
                        try:
                            if f.evaluate("() => document.querySelectorAll('#tBody tr').length") > 0:
                                target_f = f
                                break
                        except: continue
                    if target_f: break
                    time.sleep(2)
                
                if not target_f:
                    print(f"  -> {t_name}: 対象データがありません。スキップします。")
                    continue

                # 1件だけ取得（テスト用）
                rows_count = 1 
                for i in range(rows_count):
                    # 詳細取得ロジック（実績そのまま）
                    target_f.evaluate(f"jsBidInfo({i});")
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
                        # 0列目に自治体名を入れておく（統合時に便利）
                        row_data = [t_name] + [f'="{case_id}"', get_v("工事・業務名"), get_v("場所"),
                                    format_price(get_v("予定価格")), format_price(get_v("最低制限価格")),
                                    get_v("開札（予定）日"), get_v("状態")]
                        all_data_rows.append(row_data)
                        
                        print(f"★ {t_name}: 1件完了")
                        detail_f.evaluate("jsBack();")
                        time.sleep(10)

            # --- 【修正】最後に1つのCSVにまとめて書き出す ---
            with open('result.csv', 'w', encoding='utf-8-sig', newline='') as f:
                writer = csv.writer(f)
                # スプレッドシート化を見越して「自治体名」を列に追加
                writer.writerow(["自治体名"] + header)
                writer.writerows(all_data_rows)

        except Exception as e:
            print(f"Error: {e}")
        finally:
            browser.close()

if __name__ == "__main__":
    main()
