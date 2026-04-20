from playwright.sync_api import sync_playwright
import time
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
    try:
        return int(num_str)
    except:
        return ""

def get_nendo_and_tsuki(date_str):
    """日付文字列から年度(int)と月(str)を返す"""
    if not date_str:
        return "", ""
    m = re.findall(r'(\d+)', date_str)
    if len(m) >= 2:
        y, m = int(m[0]), int(m[1])
        # 年度計算：1-3月なら前年を年度とする
        nendo = y if m >= 4 else y - 1
        return f"{nendo}年度", f"{m}月"
    return "", ""

def send_to_spreadsheet(data):
    url = os.environ.get("GAS_WEBAPP_URL")
    if not url:
        log("警告: GAS_WEBAPP_URL 未設定")
        return
    try:
        log(f"GASへ合計 {len(data)} 件のデータを送信します...")
        req_data = json.dumps(data).encode('utf-8')
        req = urllib.request.Request(url, data=req_data, method='POST', headers={'Content-Type': 'application/json'})
        with urllib.request.urlopen(req) as res:
            log(f"GAS送信完了: {res.read().decode('utf-8')}")
    except Exception as e:
        log(f"送信エラー: {e}")

def main():
    targets = [
        {"name": "熊本県", "code": "0100", "n_types": ["1002011", "1002012"], "g_list": ["0100010", "0100130", "0100050"], "h_tanto": "25"},
        {"name": "南小国町", "code": "0423", "n_types": [""], "g_list": [""], "h_tanto": ""},
        {"name": "小国町", "code": "0424", "n_types": [""], "g_list": ["0100010", "0100130", "0100050"], "h_tanto": ""}
    ]
    
    all_data_rows = []

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(user_agent="Mozilla/5.0...", locale="ja-JP")
        page = context.new_page()

        try:
            for t in targets:
                for n_type in t["n_types"]:
                    for g_val in t["g_list"]:
                        log(f"--- {t['name']} (入札:{n_type if n_type else '全'} / 業種:{g_val if g_val else '全'}) ---")
                        page.goto(f"https://ebid.kumamoto-idc.pref.kumamoto.jp/PPIAccepter/AccepterServlet?kikan_no={t['code']}", wait_until="networkidle")
                        
                        menu_f = None
                        for _ in range(15):
                            for f in page.frames:
                                if "PJC001Servlet" in f.url:
                                    menu_f = f; break
                            if menu_f: break
                            time.sleep(1)
                        if not menu_f: continue
                        
                        time.sleep(3)
                        menu_f.evaluate("jsLink(1,1);")
                        
                        search_started = False
                        for _ in range(15): 
                            time.sleep(2)
                            for f in page.frames:
                                try:
                                    if f.locator('select[name="GYOSYU_TYPE"]').count() > 0:
                                        f.locator('select[name="GYOSYU_TYPE"]').select_option("00")
                                        if n_type: f.locator('select[name="NYUSATU_TYPE"]').select_option(n_type)
                                        if g_val: f.locator('select[name="GYOSYU"]').select_option(g_val)
                                        if t["h_tanto"]: f.locator('select[name="HACHU_TANTOU_KYOKU"]').select_option(t["h_tanto"])
                                        f.locator('select[name="ListCount"]').select_option("100")
                                        f.evaluate("jsSearch();")
                                        search_started = True; break
                                except: continue
                            if search_started: break

                        target_f = None
                        for _ in range(10):
                            for f in page.frames:
                                try:
                                    if f.evaluate("() => document.querySelectorAll('#tBody tr').length") > 0:
                                        target_f = f; break
                                except: continue
                            if target_f: break
                            time.sleep(3)
                        
                        if not target_f:
                            log("  -> 該当案件なし")
                            continue

                        rows_count = target_f.locator("#tBody tr").count()
                        log(f"  -> {rows_count} 件検出")

                        for i in range(rows_count):
                            current_rows = target_f.locator("#tBody tr")
                            cells = current_rows.nth(i).locator("td").all()
                            
                            v_kikan = t['name']
                            v_seko_no = cells[1].inner_text().strip()
                            v_gyosyu = cells[2].inner_text().strip()
                            v_keiyaku = cells[4].inner_text().strip()
                            
                            log(f"  -> [{i+1}/{rows_count}] 詳細取得中")
                            target_f.evaluate(f"jsBidInfo({i});")
                            time.sleep(15) 
                            
                            detail_txt, detail_f = "", None
                            for f in page.frames:
                                try:
                                    res = f.evaluate("() => ({ url: window.location.href, text: document.body.innerText })")
                                    if "PJC503Servlet" in res['url']:
                                        detail_f, detail_txt = f, res['text']
                                except: continue

                            if detail_f:
                                def get_v(label):
                                    m = re.search(rf"{label}\s*([^\n\r]+)", detail_txt)
                                    return m.group(1).strip() if m else ""

                                rakusatsu_price, rakusatsu_vender = "", ""
                                try:
                                    rows_data = detail_f.locator("tr").all()
                                    for r in rows_data:
                                        tds = r.locator("td").all()
                                        if len(tds) >= 3:
                                            tekiyo = tds[2].inner_text().strip()
                                            if "［落札］" in tekiyo or "[落札]" in tekiyo:
                                                rakusatsu_vender = tds[0].inner_text().strip()
                                                rakusatsu_price = format_price(tds[1].inner_text().strip())
                                                break
                                except: pass

                                case_id = get_v("電子入札案件番号")
                                kaisatsu_date = get_v("開札（予定）日")
                                nendo_str, tsuki_str = get_nendo_and_tsuki(kaisatsu_date)

                                # 基本データ（13項目）
                                base_data = [
                                    v_kikan, v_seko_no, v_gyosyu, v_keiyaku,
                                    f'="{case_id}"', get_v("工事・業務名"), get_v("場所"), 
                                    format_price(get_v("予定価格")), 
                                    rakusatsu_price, rakusatsu_vender,
                                    format_price(get_v("最低制限価格")), 
                                    kaisatsu_date, get_v("状態")
                                ]
                                
                                # 業者情報（20列分固定）
                                bidders = [""] * 20
                                try:
                                    bid_txt = detail_txt.split("摘要")[-1].split("備考")[0]
                                    matches = re.findall(r"([^\t\n\r]+?)\s+([0-9,]{4,})", bid_txt)
                                    valid = [[m[0].strip(), format_price(m[1])] for m in matches if not m[0].strip().replace(',','').isdigit()]
                                    for k in range(min(len(valid), 10)):
                                        bidders[k*2], bidders[k*2+1] = valid[k][0], valid[k][1]
                                except: pass

                                # 全てを連結（最後が年度と月）
                                all_columns = base_data + bidders + [nendo_str, tsuki_str]
                                all_data_rows.append(all_columns)
                                
                                detail_f.evaluate("jsBack();")
                                time.sleep(10)
                                time.sleep(2)

            if all_data_rows:
                send_to_spreadsheet(all_data_rows)

        except Exception as e:
            log(f"エラー発生: {e}")
        finally:
            browser.close()

if __name__ == "__main__":
    main()
