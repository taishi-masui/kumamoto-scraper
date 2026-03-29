from playwright.sync_api import sync_playwright
import time
import csv
import re

def format_price(v):
    """数字を ¥1,234,567 の形式に整形する"""
    if not v: return ""
    num_str = re.sub(r'[^\d]', '', v.split('(')[0])
    if not num_str: return ""
    return f"¥{int(num_str):,}"

def main():
    # 取得対象
    targets = [
        {"name": "熊本県", "code": "0100"},
        {"name": "熊本市", "code": "0200"}
    ]
    
    all_data_rows = []
    header = []

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(user_agent="Mozilla/5.0...", locale="ja-JP")
        page = context.new_page()

        try:
            for target in targets:
                t_name = target["name"]
                t_code = target["code"]
                print(f"--- {t_name} の取得を開始します ---")

                # 1. サイトアクセス
                page.goto(f"https://ebid.kumamoto-idc.pref.kumamoto.jp/PPIAccepter/AccepterServlet?kikan_no={t_code}", wait_until="networkidle")
                time.sleep(5)
                
                # 2. メニュー表示（実績そのまま）
                menu_f = next((f for f in page.frames if "PJC001Servlet" in f.url), page)
                menu_f.evaluate("jsLink(1,1);")
                
                # 3. 検索実行（実績そのまま）
                search_started = False
                for _ in range(10): 
                    for f in page.frames:
                        try:
                            sel = f.locator('select[name="ListCount"]')
                            if sel.count() > 0:
                                sel.select_option("100")
                            btn = f.locator('input[name="btnSearch"]')
                            if btn.count() > 0:
                                f.evaluate("jsSearch();")
                                search_started = True
                                break
                        except: continue
                    if search_started: break
                    time.sleep(3)

                # 4. 一覧から1件取得（実績そのまま、ループを1回に限定）
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
                
                if not target_f:
                    print(f"  -> {t_name}: データが見つかりませんでした")
                    continue

                # テスト用に 1件 のみ取得
                rows_count = 1 
                for i in range(rows_count):
                    # 一覧からデータ取得
                    rows = target_f.locator("#tBody tr")
                    row_el = rows.nth(i)
                    all_cells = [c.inner_text().strip().replace('\n', ' ') for c in row_el.locator("td").all()]
                    base_data = all_cells[0:4] 

                    # 詳細表示
                    target_f.evaluate(f"jsBidInfo({i});")
                    time.sleep(15)
                    
                    detail_txt = ""
                    detail_f = None
                    for f in page.frames:
                        try:
                            res = f.evaluate("() => ({ url: window.location.href, text: document.body.innerText })")
                            if "PJC503Servlet" in res['url']:
                                detail_f = f
                                detail_txt = res['text']
                        except: continue

                    if detail_f:
                        def get_v(label):
                            m = re.search(rf"{label}\s*([^\n\r]+)", detail_txt)
                            if not m: return ""
                            return m.group(1).strip()

                        case_id = get_v("電子入札案件番号")
                        detail_fields = [
                            f'="{case_id}"', 
                            get_v("工事・業務名"), 
                            get_v("場所"),
                            format_price(get_v("予定価格")), 
                            format_price(get_v("最低制限価格")), 
                            get_v("開札（予定）日"), 
                            get_v("状態")
                        ]

                        bidders_part = []
                        try:
                            bid_txt = detail_txt.split("摘要")[-1].split("備考")[0]
                            matches = re.findall(r"([^\t\n\r]+?)\s+([0-9,]{4,})", bid_txt)
                            valid_bidders = []
                            for name, price in matches:
                                n = name.strip()
                                if n and not n.replace(',','').isdigit():
                                    valid_bidders.append([n, format_price(price)])
                            for k in range(10):
                                if k < len(valid_bidders): bidders_part.extend(valid_bidders[k])
                                else: bidders_part.extend(["", ""])
                        except:
                            bidders_part = [""] * 20

                        # ヘッダー作成（最初の1回だけ）
                        if not header:
                            header = ["自治体名", "施行番号/案件番号", "業種 種別", "工事・業務名", "契約方法"]
                            header += ["電子入札案件番号", "工事・業務名", "場所", "予定価格", "最低制限価格", "開札（予定）日", "状態"]
                            for k in range(1, 11):
                                header.extend([f"業者{k}", f"金額{k}"])

                        # 統合リストに保存
                        all_data_rows.append([t_name] + base_data + detail_fields + bidders_part)
                        print(f"★ {t_name}: 1件完了")
                        
                        detail_f.evaluate("jsBack();")
                        time.sleep(10)

            # 5. 【修正】全地区の処理が終わった後に result.csv という名前で保存
            if all_data_rows:
                with open('result.csv', 'w', encoding='utf-8-sig', newline='') as f:
                    writer = csv.writer(f)
                    writer.writerow(header)
                    writer.writerows(all_data_rows)
                print(f"\nCSV作成完了: 計{len(all_data_rows)}件を保存しました。")

        except Exception as e:
            print(f"Error: {e}")
        finally:
            browser.close()

if __name__ == "__main__":
    main()
