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
    return f"¥{int(num_str):,}"

def send_to_spreadsheet(data):
    url = os.environ.get("GAS_WEBAPP_URL")
    if not url:
        log("警告: GAS_WEBAPP_URL 未設定")
        return
    try:
        req_data = json.dumps(data).encode('utf-8')
        req = urllib.request.Request(url, data=req_data, method='POST', headers={'Content-Type': 'application/json'})
        with urllib.request.urlopen(req) as res:
            log(f"GAS送信完了: {res.read().decode('utf-8')}")
    except Exception as e:
        log(f"送信エラー: {e}")

def main():
    targets = [
        {
            "name": "熊本県", 
            "code": "0100",
            "filters": {
                "nyusatsu_type": "1002011",
                "gyosyu_list": ["0100010", "0100130", "0100050"],
                "hachu_tanto": "25"
            }
        }
    ]
    
    all_data_rows = []

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(user_agent="Mozilla/5.0...", locale="ja-JP")
        page = context.new_page()

        try:
            for target in targets:
                t_name = target["name"]
                t_code = target["code"]
                f_conf = target["filters"]

                for gyosyu_val in f_conf["gyosyu_list"]:
                    log(f"--- {t_name} (業種:{gyosyu_val}) 検索開始 ---")
                    page.goto(f"https://ebid.kumamoto-idc.pref.kumamoto.jp/PPIAccepter/AccepterServlet?kikan_no={t_code}", wait_until="networkidle")
                    
                    # メニュー待機
                    menu_f = None
                    for _ in range(15):
                        for f in page.frames:
                            if "PJC001Servlet" in f.url:
                                menu_f = f
                                break
                        if menu_f: break
                        time.sleep(1)
                    
                    if not menu_f: continue
                    time.sleep(3)
                    menu_f.evaluate("jsLink(1,1);")
                    
                    # 検索条件入力
                    search_started = False
                    for _ in range(15): 
                        time.sleep(2)
                        for f in page.frames:
                            try:
                                if f.locator('select[name="GYOSYU_TYPE"]').count() > 0:
                                    f.locator('select[name="GYOSYU_TYPE"]').select_option("00")
                                    f.locator('select[name="NYUSATU_TYPE"]').select_option(f_conf["nyusatsu_type"])
                                    f.locator('select[name="GYOSYU"]').select_option(gyosyu_val)
                                    f.locator('select[name="HACHU_TANTOU_KYOKU"]').select_option(f_conf["hachu_tanto"])
                                    f.locator('select[name="ListCount"]').select_option("100")
                                    f.evaluate("jsSearch();")
                                    search_started = True
                                    break
                            except: continue
                        if search_started: break

                    # 一覧待機
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
                    
                    if not target_f: continue

                    # 各1件取得
                    target_f.evaluate("jsBidInfo(0);")
                    time.sleep(15)
                    
                    detail_txt = ""
                    detail_f = None
                    for f in page.frames:
                        try:
                            res = f.evaluate("() => ({ url: window.location.href, html: document.body.innerHTML, text: document.body.innerText })")
                            if "PJC503Servlet" in res['url']:
                                detail_f, detail_html, detail_txt = f, res['html'], res['text']
                        except: continue

                    if detail_f:
                        def get_v(label):
                            m = re.search(rf"{label}\s*([^\n\r]+)", detail_txt)
                            return m.group(1).strip() if m else ""

                        # 落札者抽出ロジック
                        rakusatsu_price = ""
                        rakusatsu_vender = ""
                        try:
                            # HTML内の全trをスキャンして「［落札］」を探す
                            rows_data = detail_f.locator("tr").all()
                            for r in rows_data:
                                cells = r.locator("td").all()
                                if len(cells) >= 3:
                                    tekiyo = (await cells[2].inner_text()).strip() if hasattr(cells[2], 'inner_text') else cells[2].inner_text()
                                    # 上記を同期版に修正
                                    tekiyo = cells[2].inner_text().strip()
                                    if "［落札］" in tekiyo or "[落札]" in tekiyo:
                                        rakusatsu_vender = cells[0].inner_text().strip()
                                        rakusatsu_price = format_price(cells[1].inner_text().strip())
                                        break
                        except: pass

                        case_id = get_v("電子入札案件番号")
                        # 基本データ
                        base_info = [t_name] + [c.inner_text().strip() for c in target_f.locator("#tBody tr").nth(0).locator("td").all()][0:4]
                        # 詳細データ（落札情報を予定価格の右に追加）
                        detail_info = [
                            f'="{case_id}"', get_v("工事・業務名"), get_v("場所"), 
                            format_price(get_v("予定価格")), 
                            rakusatsu_price,  # 追加: 落札価格
                            rakusatsu_vender, # 追加: 落札業者
                            format_price(get_v("最低制限価格")), 
                            get_v("開札（予定）日"), get_v("状態")
                        ]
                        
                        # 業者10社
                        bidders = [""] * 20
                        try:
                            bid_txt = detail_txt.split("摘要")[-1].split("備考")[0]
                            matches = re.findall(r"([^\t\n\r]+?)\s+([0-9,]{4,})", bid_txt)
                            valid = [[m[0].strip(), format_price(m[1])] for m in matches if not m[0].strip().replace(',','').isdigit()]
                            for k in range(min(len(valid), 10)):
                                bidders[k*2], bidders[k*2+1] = valid[k][0], valid[k][1]
                        except: pass

                        all_data_rows.append(base_info + detail_info + bidders)
                        log(f"  -> 取得成功: {case_id} (落札者: {rakusatsu_vender})")
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
