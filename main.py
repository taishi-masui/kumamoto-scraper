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

# --- 前半の関数（log, format_price, send_to_spreadsheet）は変更なし ---

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

                for gyosyu_val in f_conf["gyosyu_list"]:
                    log(f"--- {t_name} (業種コード:{gyosyu_val}) 検索開始 ---")
                    # ページ読み込み完了をしっかり待つ
                    page.goto(f"https://ebid.kumamoto-idc.pref.kumamoto.jp/PPIAccepter/AccepterServlet?kikan_no={t_code}", wait_until="networkidle")
                    
                    # 1. メニューボタンがあるフレームを特定（強化版）
                    log("メニュー画面の読み込みを待機中...")
                    menu_f = None
                    for _ in range(15):
                        # URLの部分一致だけでなく、すべてのフレームをスキャン
                        frames = page.frames
                        for f in frames:
                            # 熊本のサイトは PJC001Servlet という名前のフレームにメニューがある
                            if "PJC001Servlet" in f.url:
                                menu_f = f
                                break
                        if menu_f: break
                        time.sleep(1)
                    
                    # もし見つからなければ、強制的に2番目のフレームをメニューとみなして試行
                    if not menu_f and len(page.frames) > 1:
                        log("URL判定に失敗したため、2番目のフレームを試用します。")
                        menu_f = page.frames[1]

                    if not menu_f:
                        log(f"エラー: フレームが見つかりません。現在の総フレーム数: {len(page.frames)}")
                        continue

                    # ボタン実行
                    time.sleep(3)
                    try:
                        log("『入札結果』ボタンをクリック(jsLink実行)")
                        menu_f.evaluate("jsLink(1,1);")
                    except Exception as e:
                        log(f"jsLink実行失敗: {e}")
                        continue
                    
                    # 2. 検索条件入力（ここもフレーム特定を柔軟に）
                    log("検索画面の読み込みを待機中...")
                    search_started = False
                    for _ in range(15): 
                        time.sleep(2)
                        for f in page.frames:
                            try:
                                # 検索条件の項目が存在するか確認
                                gyosyu_sel = f.locator('select[name="GYOSYU_TYPE"]')
                                if gyosyu_sel.count() > 0:
                                    gyosyu_sel.select_option("00")
                                    f.locator('select[name="NYUSATU_TYPE"]').select_option(f_conf["nyusatsu_type"])
                                    f.locator('select[name="GYOSYU"]').select_option(gyosyu_val)
                                    f.locator('select[name="HACHU_TANTOU_KYOKU"]').select_option(f_conf["hachu_tanto"])
                                    f.locator('select[name="ListCount"]').select_option("100")
                                    
                                    log("検索条件をセットしました。検索を実行します。")
                                    f.evaluate("jsSearch();")
                                    search_started = True
                                    break
                            except: continue
                        if search_started: break

                    # --- 以降の取得処理は前回のコードと同じ ---
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
                        log(f"  -> 条件(業種:{gyosyu_val})に該当なし")
                        continue

                    # 1件取得
                    rows = target_f.locator("#tBody tr")
                    all_cells = [c.inner_text().strip().replace('\n', ' ') for c in rows.nth(0).locator("td").all()]
                    
                    log(f"  -> 詳細ページを開きます")
                    target_f.evaluate("jsBidInfo(0);")
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
                        detail_fields = [f'="{case_id}"', get_v("工事・業務名"), get_v("場所"), format_price(get_v("予定価格")), format_price(get_v("最低制限価格")), get_v("開札（予定）日"), get_v("状態")]
                        bidders = [""] * 20
                        try:
                            bid_txt = detail_txt.split("摘要")[-1].split("備考")[0]
                            matches = re.findall(r"([^\t\n\r]+?)\s+([0-9,]{4,})", bid_txt)
                            valid = [[m[0].strip(), format_price(m[1])] for m in matches if not m[0].strip().replace(',','').isdigit()]
                            for k in range(min(len(valid), 10)):
                                bidders[k*2], bidders[k*2+1] = valid[k][0], valid[k][1]
                        except: pass

                        all_data_rows.append([t_name] + all_cells[0:4] + detail_fields + bidders)
                        log(f"  -> 取得成功: {case_id}")
                        detail_f.evaluate("jsBack();")
                        time.sleep(10)

            if all_data_rows:
                send_to_spreadsheet(all_data_rows)

        except Exception as e:
            log(f"エラー発生: {e}")
        finally:
            browser.close()

if __name__ == "__main__":
    main()
