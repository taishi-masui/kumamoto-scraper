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
    """取得したリストをそのままGASに投げる"""
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
            log(f"GAS送信完了。サーバー応答: {res.read().decode('utf-8')}")
    except Exception as e:
        log(f"送信エラーが発生しました: {e}")

def main():
    # 取得対象を3つの自治体に絞り込み
    targets = [
        {"name": "熊本県", "code": "0100"},
        {"name": "南小国町", "code": "0423"},
        {"name": "小国町", "code": "0424"}
    ]
    
    all_data_rows = []
    header = []

    log("ブラウザを起動しています...")
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(user_agent="Mozilla/5.0...", locale="ja-JP")
        page = context.new_page()

        try:
            for target in targets:
                t_name = target["name"]
                t_code = target["code"]
                log(f"【開始】{t_name} (コード: {t_code}) のデータ取得を開始")

                # 1. サイトアクセス
                target_url = f"https://ebid.kumamoto-idc.pref.kumamoto.jp/PPIAccepter/AccepterServlet?kikan_no={t_code}"
                log(f"サイトへアクセス中: {target_url}")
                page.goto(target_url, wait_until="networkidle")
                time.sleep(5)
                
                # 2. メニュー表示
                log("入札結果メニューを選択中...")
                menu_f = next((f for f in page.frames if "PJC001Servlet" in f.url), page)
                menu_f.evaluate("jsLink(1,1);")
                
                # 3. 検索条件入力・実行
                log("検索画面の準備を確認中...")
                search_started = False
                for i in range(10): 
                    for f in page.frames:
                        try:
                            sel = f.locator('select[name="ListCount"]')
                            if sel.count() > 0:
                                sel.select_option("100")
                                log("表示件数を100件に変更しました")
                            btn = f.locator('input[name="btnSearch"]')
                            if btn.count() > 0:
                                log("検索ボタンをクリックします")
                                f.evaluate("jsSearch();")
                                search_started = True
                                break
                        except: continue
                    if search_started: break
                    time.sleep(3)

                # 4. 一覧画面のロード待ち
                log("一覧画面の読み込みを待機しています...")
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
                    log(f"× {t_name}: 検索結果が見つかりませんでした。スキップします。")
                    continue

                # 各自治体 1件 ずつ取得（テストモード）
                rows_count = 1 
                log(f"一覧を確認。最新{rows_count}件の詳細取得に移ります。")

                for i in range(rows_count):
                    rows = target_f.locator("#tBody tr")
                    row_el = rows.nth(i)
                    all_cells = [c.inner_text().strip().replace('\n', ' ') for c in row_el.locator("td").all()]
                    base_data = all_cells[0:4] 

                    # 詳細表示
                    log(f"  -> [{i+1}/{rows_count}件目] 詳細ページを開いています...")
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
                        log("  -> 詳細データの解析中...")
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

                        # 入札業者取得
                        log("  -> 入札業者リストを抽出中...")
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
                            log("  -> 入札業者の抽出に失敗またはデータなし")
                            bidders_part = [""] * 20

                        # ヘッダー情報の定義
                        if not header:
                            header = ["自治体名", "施行番号/案件番号", "業種 種別", "工事・業務名", "契約方法"]
                            header += ["電子入札案件番号", "工事名詳細", "場所", "予定価格", "最低制限価格", "開札（予定）日", "状態"]
                            for k in range(1, 11):
                                header.extend([f"業者{k}", f"金額{k}"])

                        # 取得データをリストに追加
                        all_data_rows.append([t_name] + base_data + detail_fields + bidders_part)
                        log(f"★ {t_name}: 1件の取得に成功しました")
                        
                        log("一覧画面に戻ります...")
                        detail_f.evaluate("jsBack();")
                        time.sleep(10)

            # 5. 結果の保存と送信
            if all_data_rows:
                log(f"全自治体の処理が完了。合計 {len(all_data_rows)} 件のデータを保存します。")
                
                # CSV保存
                with open('result.csv', 'w', encoding='utf-8-sig', newline='') as f:
                    writer = csv.writer(f)
                    writer.writerow(header)
                    writer.writerows(all_data_rows)
                
                # スプレッドシート送信（データ行のみ送る。GAS側で上書き判定するため）
                send_to_spreadsheet(all_data_rows)
            else:
                log("データが1件も取得できなかったため、送信を中止しました。")

        except Exception as e:
            log(f"メインループ内で予期せぬエラーが発生しました: {e}")
        finally:
            log("ブラウザを終了します。")
            browser.close()

if __name__ == "__main__":
    main()
