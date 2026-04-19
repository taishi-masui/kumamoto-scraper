from playwright.sync_api import sync_playwright
import time
import csv
import re
import json
import os
import urllib.request
from datetime import datetime

def log(message):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{timestamp}] {message}")

def format_price(v):
    if not v: return ""
    num_str = re.sub(r'[^\d]', '', v.split('(')[0])
    if not num_str: return ""
    return f"¥{int(num_str):,}"

def send_to_spreadsheet(data):
    url = os.environ.get("GAS_WEBAPP_URL")
    if not url:
        log("警告: GAS_WEBAPP_URL が設定されていません。")
        return
    try:
        log("GASへの送信を開始します...")
        req_data = json.dumps(data).encode('utf-8')
        req = urllib.request.Request(
            url, data=req_data, method='POST', 
            headers={'Content-Type': 'application/json'}
        )
        with urllib.request.urlopen(req) as res:
            log(f"送信完了: {res.read().decode('utf-8')}")
    except Exception as e:
        log(f"送信エラー: {e}")

def main():
    # テストのため「熊本県」のみに限定
    targets = [
        {"name": "熊本県", "code": "0100"}
    ]
    
    all_data_rows = []
    header = ["自治体名", "施行番号/案件番号", "業種 種別", "工事・業務名", "契約方法", "電子入札案件番号", "工事名詳細", "場所", "予定価格", "最低制限価格", "開札（予定）日", "状態"]
    for k in range(1, 11):
        header.extend([f"業者{k}", f"金額{k}"])

    log("ブラウザを起動しています...")
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(user_agent="Mozilla/5.0...", locale="ja-JP")
        page = context.new_page()

        try:
            for target in targets:
                t_name = target["name"]
                t_code = target["code"]
                log(f"--- {t_name} の取得を開始 ---")

                page.goto(f"https://ebid.kumamoto-idc.pref.kumamoto.jp/PPIAccepter/AccepterServlet?kikan_no={t_code}", wait_until="networkidle")
                time.sleep(5)
                
                menu_f = next((f for f in page.frames if "PJC001Servlet" in f.url), page)
                menu_f.evaluate("jsLink(1,1);")
                
                search_started = False
                for _ in range(10): 
                    for f in page.frames:
                        try:
                            # 業種分類を「工事(00)」に固定
                            sel_gyosyu = f.locator('select[name="GYOSYU_TYPE"]')
                            if sel_gyosyu.count() > 0:
                                sel_gyosyu.select_option("00")
                            
                            f.locator('select[name="ListCount"]').select_option("100")
                            btn = f.locator('input[name="btnSearch"]')
                            if btn.count() > 0:
                                f.evaluate("jsSearch();")
                                search_started = True
                                break
                        except: continue
                    if search_started: break
                    time.sleep(3)

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
                    log(f"× {t_name}: 該当なし")
                    continue

                # テスト用に 5件 固定
                actual_rows = target_f.locator("#tBody tr").count()
                rows_count = min(actual_rows, 5) 
                log(f"{t_name}: 最新{rows_count}件を取得します")

                for i in range(rows_count):
                    rows = target_f.locator("#tBody tr")
                    row_el = rows.nth(i)
                    all_cells = [c.inner_text().strip().replace('\n', ' ') for c in row_el.locator("td").all()]
                    base_data = all_cells[0:4] 

                    target_f.evaluate(f"jsBidInfo({i});")
                    time.sleep(15) # サイト負荷軽減のため維持
                    
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
                            return m.group(1).strip() if m else ""

                        case_id = get_v("電子入札案件番号")
                        detail_fields = [f'="{case_id}"', get_v("工事・業務名"), get_v("場所"), format_price(get_v("予定価格")), format_price(get_v("最低制限価格")), get_v("開札（予定）日"), get_v("状態")]

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

                        all_data_rows.append([t_name] + base_data + detail_fields + bidders_part)
                        log(f"  -> {i+1}件目 取得成功: {case_id}")
                        detail_f.evaluate("jsBack();")
                        time.sleep(10)

            if all_data_rows:
                send_to_spreadsheet(all_data_rows)

        except Exception as e:
            log(f"エラー: {e}")
        finally:
            browser.close()

if __name__ == "__main__":
    main()
