from playwright.sync_api import sync_playwright
import time
import csv
import re

def format_price(v):
    """金額に¥マークとカンマを付与する"""
    if not v: return ""
    num_str = re.sub(r'[^\d]', '', v.split('(')[0])
    if not num_str: return ""
    return f"¥{int(num_str):,}"

def main():
    # 調査結果に基づき、実績のあるURL直接指定方式で2地区を回します
    targets = [
        {"name": "熊本県", "code": "0100"},
        {"name": "南小国町", "code": "0423"}
    ]

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(user_agent="Mozilla/5.0...", locale="ja-JP")
        page = context.new_page()

        try:
            for target in targets:
                t_name = target["name"]
                t_code = target["code"]

                # --- 1. 実績のあるURL直接アクセス (今までにない要素を排除) ---
                page.goto(f"https://ebid.kumamoto-idc.pref.kumamoto.jp/PPIAccepter/AccepterServlet?kikan_no={t_code}", wait_until="networkidle")
                time.sleep(5)

                # --- 2. メニュー呼び出し（実績コードそのまま） ---
                menu_f = next((f for f in page.frames if "PJC001Servlet" in f.url), page)
                menu_f.evaluate("jsLink(1,1);")
                
                # --- 3. 100件設定 & 検索実行（実績コードそのまま） ---
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

                all_data_rows = []
                header = []

                # --- 4. 全ページ・全件ループ（実績コードそのまま） ---
                while True:
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
                    
                    if not target_f: break

                    rows_count = target_f.locator("#tBody tr").count()
                    for i in range(rows_count):
                        # 一覧フレーム再特定
                        for _ in range(5):
                            for f in page.frames:
                                try:
                                    if f.evaluate("() => document.querySelectorAll('#tBody tr').length") > 0:
                                        target_f = f
                                        break
                                except: continue
                            if target_f: break
                            time.sleep(2)

                        rows = target_f.locator("#tBody tr")
                        row_el = rows.nth(i)
                        all_cells = [c.inner_text().strip().replace('\n', ' ') for c in row_el.locator("td").all()]
                        base_data = all_cells[0:4] 

                        # 詳細ボタン(jsBidInfo)
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
                                f'="{case_id}"', # 0落ち防止文字列
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
                                    if k < len(valid_bidders):
                                        bidders_part.extend(valid_bidders[k])
                                    else:
                                        bidders_part.extend(["", ""])
                            except:
                                bidders_part = [""] * 20

                            if not header:
                                header = ["施行番号/案件番号", "業種 種別", "工事・業務名", "契約方法",
                                          "電子入札案件番号", "工事・業務名", "場所", "予定価格", "最低制限価格", "開札（予定）日", "状態"]
                                for k in range(1, 11):
                                    header.extend([f"業者{k}", f"金額{k}"])

                            all_data_rows.append(base_data + detail_fields + bidders_part)
                            detail_f.evaluate("jsBack();")
                            time.sleep(10)

                    # 次ページ送り（実績コード）
                    try:
                        next_btn = target_f.locator('input[name="btnNextPage"]')
                        if next_btn.count() > 0 and next_btn.is_enabled():
                            target_f.evaluate("jsNextPage();")
                            time.sleep(15)
                        else:
                            break
                    except:
                        break

                # 地区名で保存
                if all_data_rows:
                    with open(f'result_{t_name}.csv', 'w', encoding='utf-8-sig', newline='') as f:
                        writer = csv.writer(f)
                        writer.writerow(header)
                        writer.writerows(all_data_rows)

        except Exception as e:
            # 実行ログ表示なしの指示に基づき、最小限の停止処理
            pass
        finally:
            browser.close()

if __name__ == "__main__":
    main()
