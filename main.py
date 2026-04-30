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
        log(f"GASへ合計 {len(data)} 件のデータを送信します...")
        req_data = json.dumps(data).encode('utf-8')
        req = urllib.request.Request(url, data=req_data, method='POST', headers={'Content-Type': 'application/json'})
        with urllib.request.urlopen(req) as res:
            log(f"GAS送信完了: {res.read().decode('utf-8')}")
    except Exception as e:
        log(f"送信エラー: {e}")

def main():
    one_month_ago = datetime.now() - timedelta(days=60)
    y_str, m_str, d_str = str(one_month_ago.year), str(one_month_ago.month), str(one_month_ago.day)

    targets = [
        {"name": "熊本県", "code": "0100", "n_types": ["1002011", "1002012"], "g_list": ["0100010", "0100130", "0100050"], "h_tanto": "25"},
        {"name": "南小国町", "code": "0423", "n_types": [""], "g_list": [""], "h_tanto": ""},
        {"name": "小国町", "code": "0424", "n_types": [""], "g_list": ["0100010", "0100130", "0100050"], "h_tanto": ""}
    ]
    
    all_data_rows = []

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36", locale="ja-JP")
        page = context.new_page()

        try:
            for t in targets:
                for n_type in t["n_types"]:
                    for g_val in t["g_list"]:
                        log(f"=== 検索開始: {t['name']} (入札:{n_type} / 業種:{g_val}) ===")
                        page.goto(f"https://ebid.kumamoto-idc.pref.kumamoto.jp/PPIAccepter/AccepterServlet?kikan_no={t['code']}", wait_until="networkidle")
                        
                        # メインフレームの特定
                        search_f = None
                        for _ in range(20):
                            for f in page.frames:
                                if "PJC001Servlet" in f.url:
                                    search_f = f; break
                            if search_f: break
                            time.sleep(1)
                        if not search_f: continue
                        
                        time.sleep(2)
                        search_f.evaluate("jsLink(1,1);") # 入札結果
                        
                        # 検索条件入力
                        condition_f = None
                        for _ in range(20):
                            time.sleep(1)
                            for f in page.frames:
                                try:
                                    if f.locator('select[name="GYOSYU_TYPE"]').count() > 0:
                                        condition_f = f; break
                                except: continue
                            if condition_f: break
                        
                        if condition_f:
                            condition_f.locator('select[name="GYOSYU_TYPE"]').select_option("00")
                            if n_type: condition_f.locator('select[name="NYUSATU_TYPE"]').select_option(n_type)
                            if g_val: condition_f.locator('select[name="GYOSYU"]').select_option(g_val)
                            if t["h_tanto"]: condition_f.locator('select[name="HACHU_TANTOU_KYOKU"]').select_option(t["h_tanto"])
                            condition_f.locator('select[name="KAISATSU_DATE_f_yyyy"]').select_option(y_str)
                            condition_f.locator('select[name="KAISATSU_DATE_f_mm"]').select_option(m_str)
                            condition_f.locator('select[name="KAISATSU_DATE_f_dd"]').select_option(d_str)
                            condition_f.locator('select[name="ListCount"]').select_option("100")
                            condition_f.evaluate("jsSearch();")
                        
                        # --- ページング処理開始 ---
                        page_idx = 1
                        while True:
                            log(f"  P.{page_idx} のデータを確認中...")
                            target_f = None
                            for _ in range(15):
                                for f in page.frames:
                                    if f.locator("#tBody tr").count() > 0:
                                        target_f = f; break
                                if target_f: break
                                time.sleep(2)
                            
                            if not target_f:
                                log("    -> 案件が表示されません。終了します。")
                                break

                            rows_count = target_f.locator("#tBody tr").count()
                            log(f"    -> {rows_count} 件表示されています")

                            # 1ページ内のループ
                            for i in range(rows_count):
                                # 1. まず概要データを取得（絶対に確保）
                                row = target_f.locator("#tBody tr").nth(i)
                                cells = row.locator("td").all()
                                
                                seko_no = cells[0].inner_text().split('\n')[0].strip()
                                gyosyu = cells[1].inner_text().strip()
                                case_name = cells[2].inner_text().strip()
                                keiyaku = cells[3].inner_text().strip()
                                kaisatsu_date = cells[4].inner_text().strip()
                                status = cells[5].inner_text().strip() # 画像テキスト
                                
                                # 2. 詳細画面へ
                                log(f"    [{i+1}/{rows_count}] 詳細取得中: {case_name[:15]}")
                                target_f.evaluate(f"jsBidInfo({i});")
                                
                                # 詳細フレーム待機
                                detail_f = None
                                for _ in range(20):
                                    for f in page.frames:
                                        if "PJC503Servlet" in f.url:
                                            detail_f = f; break
                                    if detail_f: break
                                    time.sleep(1)
                                
                                # 詳細情報の解析
                                detail_data = [""] * 35 # 予備含め初期化
                                if detail_f:
                                    txt = detail_f.evaluate("() => document.body.innerText")
                                    def find_v(label):
                                        m = re.search(rf"{label}\s*([^\n\r]+)", txt)
                                        return m.group(1).strip() if m else ""

                                    case_id = find_v("電子入札案件番号")
                                    basho = find_v("場所")
                                    yotei = format_price(find_v("予定価格"))
                                    saitei = format_price(find_v("最低制限価格"))
                                    nendo, tsuki = get_nendo_and_tsuki(kaisatsu_date)

                                    # 落札者と落札金額の抽出
                                    rakusatsu_v, rakusatsu_p = "", ""
                                    try:
                                        for r in detail_f.locator("tr").all():
                                            tds = r.locator("td").all()
                                            if len(tds) >= 3 and "落札" in tds[2].inner_text():
                                                rakusatsu_v = tds[0].inner_text().strip()
                                                rakusatsu_p = format_price(tds[1].inner_text().strip())
                                                break
                                    except: pass

                                    # 業者一覧（上位10社）
                                    bidders = [""] * 20
                                    try:
                                        bid_txt = txt.split("摘要")[-1].split("備考")[0]
                                        matches = re.findall(r"([^\t\n\r]+?)\s+([0-9,]{4,})", bid_txt)
                                        valid = [[m[0].strip(), format_price(m[1])] for m in matches if not m[0].strip().replace(',','').isdigit()]
                                        for k in range(min(len(valid), 10)):
                                            bidders[k*2], bidders[k*2+1] = valid[k][0], valid[k][1]
                                    except: pass

                                    # 行データの組み立て
                                    row_final = [
                                        t['name'], seko_no, gyosyu, keiyaku, f'="{case_id}"',
                                        case_name, basho, yotei, rakusatsu_p, rakusatsu_v, saitei,
                                        kaisatsu_date, status
                                    ] + bidders + [nendo, tsuki]
                                    all_data_rows.append(row_final)
                                    
                                    # 戻る
                                    detail_f.evaluate("jsBack();")
                                    time.sleep(5)
                                else:
                                    log(f"      × 詳細の取得に失敗しました ({case_name[:10]})")

                            # --- 次ページチェック ---
                            next_img = target_f.locator("img[src*='NextPage.gif']")
                            if next_img.count() > 0:
                                log("  -> 次ページへ移動します")
                                target_f.evaluate("jsNext();")
                                time.sleep(8)
                                page_idx += 1
                            else:
                                break

            send_to_spreadsheet(all_data_rows)

        except Exception as e:
            log(f"致命的エラー: {e}")
        finally:
            browser.close()

if __name__ == "__main__":
    main()
