from playwright.sync_api import sync_playwright
import time
import re
import json
import os
import urllib.request
from datetime import datetime, timedelta

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
        nendo = y if m >= 4 else y - 1
        return f"{nendo}年度", f"{m}月"
    return "", ""

def send_to_spreadsheet(data):
    url = os.environ.get("GAS_WEBAPP_URL")
    if not url:
        log("警告: GAS_WEBAPP_URL 未設定")
        return
    try:
        # ヘッダー名（キー）を含む辞書形式で送信
        log(f"GASへ合計 {len(data)} 件のデータを送信します(ヘッダー照合型)...")
        req_data = json.dumps(data).encode('utf-8')
        req = urllib.request.Request(url, data=req_data, method='POST', headers={'Content-Type': 'application/json'})
        with urllib.request.urlopen(req) as res:
            log(f"GAS送信完了: {res.read().decode('utf-8')}")
    except Exception as e:
        log(f"送信エラー: {e}")

def main():
    # 検索用の日付（実行日の180日前）を計算
    one_month_ago = datetime.now() - timedelta(days=1)
    y_str, m_str, d_str = str(one_month_ago.year), str(one_month_ago.month), str(one_month_ago.day)

    # 熊本県（阿蘇25）、および指名競争コードを修正済み
    targets = [
        {"name": "熊本県", "code": "0100", "n_types": ["1002011", "2002027"], "g_list": ["0100010", "0100130", "0100050"], "h_tanto": "25"},
        {"name": "南小国町", "code": "0423", "n_types": [""], "g_list": [""], "h_tanto": ""},
        {"name": "小国町", "code": "0424", "n_types": [""], "g_list": ["0100010", "0100130", "0100050"], "h_tanto": ""}
    ]
    
    all_data_dicts = []

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36", locale="ja-JP")
        page = context.new_page()

        try:
            for t in targets:
                for n_type in t["n_types"]:
                    for g_val in t["g_list"]:
                        log(f"--- 検索開始: {t['name']} (入札:{n_type if n_type else '全'} / 業種:{g_val if g_val else '全'}) ---")
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
                                        
                                        f.locator('select[name="KAISATSU_DATE_f_yyyy"]').select_option(y_str)
                                        f.locator('select[name="KAISATSU_DATE_f_mm"]').select_option(m_str)
                                        f.locator('select[name="KAISATSU_DATE_f_dd"]').select_option(d_str)

                                        f.locator('select[name="ListCount"]').select_option("100")
                                        f.evaluate("jsSearch();")
                                        search_started = True; break
                                except: continue
                            if search_started: break

                        # --- ページング処理ループ ---
                        while True:
                            target_f = None
                            for _ in range(15):
                                for f in page.frames:
                                    try:
                                        if f.evaluate("() => document.querySelectorAll('#tBody tr').length") > 0:
                                            target_f = f; break
                                    except: continue
                                if target_f: break
                                time.sleep(3)
                            
                            if not target_f:
                                log("  -> 該当案件なし（または終了）")
                                break

                            rows_count = target_f.locator("#tBody tr").count()
                            log(f"  -> {rows_count} 件検出")

                            for i in range(rows_count):
                                row = target_f.locator("#tBody tr").nth(i)
                                cells = row.locator("td").all()
                                
                                v_seko_no = cells[0].inner_text().split('\n')[0].strip()
                                v_gyosyu = cells[1].inner_text().strip()      
                                v_case_name = cells[2].inner_text().strip()    
                                v_keiyaku = cells[3].inner_text().strip()     
                                v_kaisatsu_list = cells[4].inner_text().strip() 
                                v_status = cells[5].inner_text().strip()
                                
                                log(f"    [{i+1}/{rows_count}] 詳細取得中: {v_case_name[:15]}...")
                                target_f.evaluate(f"jsBidInfo({i});")
                                time.sleep(12) 
                                
                                detail_txt, detail_f = "", None
                                for f in page.frames:
                                    try:
                                        if "PJC503Servlet" in f.url:
                                            detail_f = f
                                            detail_txt = f.evaluate("() => document.body.innerText")
                                            break
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
                                            if len(tds) >= 3 and "落札" in tds[2].inner_text():
                                                rakusatsu_vender = tds[0].inner_text().strip()
                                                rakusatsu_price = format_price(tds[1].inner_text().strip())
                                                break
                                    except: pass

                                    case_id = get_v("電子入札案件番号")
                                    nendo_str, tsuki_str = get_nendo_and_tsuki(v_kaisatsu_list)

                                    # 送信データの作成（シートの最新列名に完全一致）
                                    row_dict = {
                                        "自治体名": t['name'],
                                        "施行番号/案件番号": v_seko_no,
                                        "業種 種別": v_gyosyu,
                                        "契約方法": v_keiyaku,
                                        "電子入札案件番号": f'="{case_id}"',
                                        "工事・業務名": v_case_name,
                                        "場所": get_v("場所"),
                                        "予定価格": format_price(get_v("予定価格")),
                                        "落札価格": rakusatsu_price,
                                        "落札業者": rakusatsu_vender,
                                        "最低制限価格": format_price(get_v("最低制限価格")),
                                        "開札（予定）日": v_kaisatsu_list,
                                        "年度": nendo_str,
                                        "月": tsuki_str,
                                        "状態": v_status
                                    }

                                    # 業者・金額情報の解析（1〜10ペア）
                                    try:
                                        bid_parts = detail_txt.split("摘要")
                                        if len(bid_parts) > 1:
                                            bid_txt = bid_parts[-1].split("備考")[0]
                                            matches = re.findall(r"([^\t\n\r]+?)\s+([0-9,]{4,})", bid_txt)
                                            valid = [[m[0].strip(), format_price(m[1])] for m in matches if not m[0].strip().replace(',','').isdigit()]
                                            for k in range(10):
                                                idx = k + 1
                                                row_dict[f"業者{idx}"] = valid[k][0] if k < len(valid) else ""
                                                row_dict[f"金額{idx}"] = valid[k][1] if k < len(valid) else ""
                                    except: pass

                                    all_data_dicts.append(row_dict)
                                    detail_f.evaluate("jsBack();")
                                    time.sleep(8)
                            
                            # --- 次ページ確認 ---
                            next_img = target_f.locator("img[src*='NextPage.gif']")
                            if next_img.count() > 0:
                                log("  -> 次ページへ移動します")
                                target_f.evaluate("jsNext();")
                                time.sleep(10)
                            else:
                                break

            # 最終送信
            send_to_spreadsheet(all_data_dicts)

        except Exception as e:
            log(f"エラー発生: {e}")
        finally:
            browser.close()

if __name__ == "__main__":
    main()
