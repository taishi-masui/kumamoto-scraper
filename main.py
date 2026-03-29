from playwright.sync_api import sync_playwright
import time
import csv
import re
import json
import os
import urllib.request

def format_price(v):
    if not v: return ""
    num_str = re.sub(r'[^\d]', '', v.split('(')[0])
    if not num_str: return ""
    return f"¥{int(num_str):,}"

def send_to_spreadsheet(data):
    """GASのウェブアプリURLにデータを送信する"""
    url = os.environ.get("GAS_WEBAPP_URL")
    if not url:
        print("Error: GAS_WEBAPP_URL が設定されていません。")
        return
    try:
        req_data = json.dumps(data).encode('utf-8')
        req = urllib.request.Request(
            url, data=req_data, method='POST', 
            headers={'Content-Type': 'application/json'}
        )
        with urllib.request.urlopen(req) as res:
            print(f"スプレッドシート送信結果: {res.read().decode('utf-8')}")
    except Exception as e:
        print(f"スプレッドシート送信エラー: {e}")

def main():
    # 取得対象
    targets = [
        {"name": "熊本県", "code": "0100"},
        {"name": "熊本市", "code": "0200"},
        {"name": "南小国町", "code": "0423"}
    ]
    
    all_data_rows = []
    # ヘッダー定義
    header = ["自治体名", "施行番号/案件番号", "業種 種別", "工事・業務名", "契約方法",
              "電子入札案件番号", "詳細工事名", "場所", "予定価格", "最低制限価格", "開札（予定）日", "状態"]
    for k in range(1, 11): header.extend([f"業者{k}", f"金額{k}"])

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(user_agent="Mozilla/5.0...", locale="ja-JP")
        page = context.new_page()

        try:
            for target in targets:
                t_name = target["name"]
                t_code = target["code"]
                print(f"--- {t_name} の取得を開始します ---")

                # 1. アクセス
                page.goto(f"https://ebid.kumamoto-idc.pref.kumamoto.jp/PPIAccepter/AccepterServlet?kikan_no={t_code}", wait_until="networkidle")
                time.sleep(5)
                
                # 2. メニュー
                menu_f = next((f for f in page.frames if "PJC001Servlet" in f.url), page)
                menu_f.evaluate("jsLink(1,1);")
                
                # 3. 検索
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

                # 4. 一覧
                target_f = None
                for _ in range(15):
                    for f in page.frames:
                        try:
                            if f.evaluate("() => document.querySelectorAll('#tBody tr').length") > 0:
                                target_f = f
                                break
                        except: continue
                    if target_f: break
                    time.sleep(2)
                
                if not target_f:
                    print(f"  -> {t_name}: データなし。")
                    continue

                # 各地区 1件 テスト取得
                rows = target_f.locator("#tBody tr")
                rows_count = rows.count()
                
                for i in range(min(1, rows_count)):
                    # 一覧のデータを0〜3列目で固定取得
                    tds = [c.inner_text().strip().replace('\n', ' ') for c in rows.nth(i).locator("td").all()]
                    base_data = tds[0:4] if len(tds) >= 4 else (tds + [""]*4)[:4]

                    # 詳細画面へ
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
                        detail_fields = [
                            f'="{case_id}"', get_v("工事・業務名"), get_v("場所"),
                            format_price(get_v("予定価格")), format_price(get_v("最低制限価格")),
                            get_v("開札（予定）日"), get_v("状態")
                        ]
                        
                        bidders_part = []
                        try:
                            bid_txt = txt.split("摘要")[-1].split("備考")[0]
                            matches = re.findall(r"([^\t\n\r]+?)\s+([0-9,]{4,})", bid_txt)
                            valid_bidders = [[n.strip(), format_price(p)] for n, p in matches if not n.strip().replace(',','').isdigit()]
                            for k in range(10):
                                bidders_part.extend(valid_bidders[k] if k < len(valid_bidders) else ["", ""])
                        except: bidders_part = [""] * 20

                        # 全データを結合
                        all_data_rows.append([t_name] + base_data + detail_fields + bidders_part)
                        print(f"★ {t_name}: 取得完了")
                        
                        detail_f.evaluate("jsBack();")
                        time.sleep(10)

            # 最後にまとめてスプレッドシートへ送信
            if all_data_rows:
                print(f"\nスプレッドシートに {len(all_data_rows)} 件送信中...")
                send_to_spreadsheet(all_data_rows)

        except Exception as e:
            print(f"Error: {e}")
        finally:
            browser.close()

if __name__ == "__main__":
    main()
