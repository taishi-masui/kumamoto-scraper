from playwright.sync_api import sync_playwright
import time
import csv
import re
import json
import os
import urllib.request
from datetime import datetime

def log(message):
    """時刻付きでログを表示する"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{timestamp}] {message}")

def format_price(v):
    """数字を ¥1,234,567 の形式に整形する"""
    if not v: return ""
    num_str = re.sub(r'[^\d]', '', v.split('(')[0])
    if not num_str: return ""
    return f"¥{int(num_str):,}"

def send_to_spreadsheet(data):
    """取得したリストをGASに投げる（更新日時はGAS側で付与）"""
    url = os.environ.get("GAS_WEBAPP_URL")
    if not url:
        log("警告: GAS_WEBAPP_URL が設定されていません。")
        return
    try:
        log(f"GASへ {len(data)} 件のデータを送信します...")
        req_data = json.dumps(data).encode('utf-8')
        req = urllib.request.Request(
            url, data=req_data, method='POST', 
            headers={'Content-Type': 'application/json'}
        )
        with urllib.request.urlopen(req) as res:
            log(f"GAS送信結果: {res.read().decode('utf-8')}")
    except Exception as e:
        log(f"送信エラーが発生しました: {e}")

def main():
    # 取得対象とフィルタ条件の設定
    targets = [
        {
            "name": "熊本県", 
            "code": "0100",
            "filters": {
                "nyusatsu_type": "1002011", # 一般競争入札
                "gyosyu_list": ["0100010", "0100130", "0100050"], # 土木一式, 舗装, とび土工
                "hachu_tanto": "25" # 阿蘇地域振興局
            }
        }
    ]
    
    all_data_rows = []

    log("ブラウザを起動しています...")
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(user_agent="Mozilla/5.0...", locale="ja-JP")
        page = context.new_page()

        try:
            for target in targets:
                t_name = target["name"]
                t_code = target["code"]
                f_conf = target["filters"]

                # 業種ごとにループして検索
                for gyosyu_val in f_conf["gyosyu_list"]:
                    log(f"--- {t_name} (業種コード:{gyosyu_val}) 検索開始 ---")
                    page.goto(f"https://ebid.kumamoto-idc.pref.kumamoto.jp/PPIAccepter/AccepterServlet?kikan_no={t_code}")
                    
                    # 1. メニューフレームの待機（ReferenceError対策）
                    log("メニュー画面の読み込みを待機中...")
                    menu_f = None
                    for _ in range(15):
                        menu_f = next((f for f in page.frames if "PJC001Servlet" in f.url), None)
                        if menu_f: break
                        time.sleep(1)
                    
                    if not menu_f:
                        log("エラー: メニューが見つかりません。スキップします。")
                        continue

                    # メニューが安定するまで少し待ってからクリック
                    time.sleep(2)
                    try:
                        menu_f.evaluate("jsLink(1,1);")
                    except Exception as e:
                        log(f"メニュークリック再試行中...: {e}")
                        time.sleep(3)
                        menu_f.evaluate("jsLink(1,1);")
                    
                    # 2. 検索条件入力・実行
                    log("検索条件を設定中...")
                    search_started = False
                    for _ in range(15): 
                        for f in page.frames:
                            try:
                                if f.locator('select[name="GYOSYU_TYPE"]').count() > 0:
                                    # 業種分類：工事(00)
                                    f.locator('select[name="GYOSYU_TYPE"]').select_option("00")
                                    # 入札方法
                                    f.locator('select[name="NYUSATU_TYPE"]').select_option(f_conf["nyusatsu_type"])
                                    # 業種種別
                                    f.locator('select[name="GYOSYU"]').select_option(gyosyu_val)
                                    # 発注担当部局
                                    f.locator('select[name="HACHU_TANTOU_KYOKU"]').select_option(f_conf["hachu_tanto"])
                                    # 表示件数
                                    f.locator('select[name="ListCount"]').select_option("100")
                                    
                                    log("検索ボタンをクリックします")
                                    f.evaluate("jsSearch();")
                                    search_started = True
                                    break
                            except: continue
                        if search_started: break
                        time.sleep(2)

                    # 3. 一覧画面のロード待ち
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
                        log(f"  -> この条件(業種:{gyosyu_val})に該当する案件はありませんでした。")
                        continue

                    # 各条件から「1件」だけ取得
                    rows_count = 1 
                    for i in range(rows_count):
                        rows = target_f.locator("#tBody tr")
                        all_cells = [c.inner_text().strip().replace('\n', ' ') for c in rows.nth(i).locator("td").all()]
                        base_data = all_cells[0:4]

                        log(f"  -> 詳細ページを開いています...")
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
                                return m.group(1).strip() if m else ""

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

                            # 業者リストの抽出（最大10社）
                            bidders = [""] * 20
                            try:
                                bid_txt = detail_txt.split("摘要")[-1].split("備考")[0]
                                matches = re.findall(r"([^\t\n\r]+?)\s+([0-9,]{4,})", bid_txt)
                                valid = [[m[0].strip(), format_price(m[1])] for m in matches if not m[0].strip().replace(',','').isdigit()]
                                for k in range(min(len(valid), 10)):
                                    bidders[k*2] = valid[k][0]
                                    bidders[k*2+1] = valid[k][1]
                            except: pass

                            # 取得データをリストに蓄積
                            all_data_rows.append([t_name] + base_data + detail_fields + bidders)
                            log(f"  -> 取得成功: {case_id}")
                            
                            detail_f.evaluate("jsBack();")
                            time.sleep(10)

            # 4. 全業種のループ完了後に一括送信
            if all_data_rows:
                send_to_spreadsheet(all_data_rows)
            else:
                log("全フィルタを通して取得可能なデータはありませんでした。")

        except Exception as e:
            log(f"予期せぬエラー: {e}")
        finally:
            log("ブラウザを終了します。")
            browser.close()

if __name__ == "__main__":
    main()
