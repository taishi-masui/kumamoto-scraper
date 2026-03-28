from playwright.sync_api import sync_playwright
import time
import csv
import re

def main():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(user_agent="Mozilla/5.0...", locale="ja-JP")
        page = context.new_page()

        try:
            print("1. 検索条件画面を表示...")
            page.goto("https://ebid.kumamoto-idc.pref.kumamoto.jp/PPIAccepter/AccepterServlet?kikan_no=0100", wait_until="networkidle")
            time.sleep(5)
            menu_f = next((f for f in page.frames if "PJC001Servlet" in f.url), page)
            menu_f.evaluate("jsLink(1,1);")
            
            # --- 2. 検索実行 ---
            print("2. 検索ボタンを探して実行...")
            search_started = False
            for _ in range(10): 
                for f in page.frames:
                    try:
                        btn = f.locator('input[name="btnSearch"]')
                        if btn.count() > 0:
                            f.evaluate("jsSearch();")
                            print("★検索を実行しました。")
                            search_started = True
                            break
                    except: continue
                if search_started: break
                time.sleep(3)

            # --- 3. 結果一覧の出現を待機 ---
            print("3. 結果一覧の出現を待機中...")
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
            
            if target_f:
                # --- 【重要】クリック前に一覧情報をそのまま確保 ---
                # あなたが以前成功させた「tdのテキストをそのまま取る」ロジックです
                row_cells = target_f.locator("#tBody tr").nth(0).locator("td")
                base_data = [c.inner_text().strip().replace('\n', ' ') for c in row_cells.all()]
                print(f"★一覧情報を確保しました: {base_data}")

                print("4. 1行目の『入札情報』ボタンをクリック...")
                target_f.evaluate("jsBidInfo(0);")
                print("15秒待機します...")
                time.sleep(15)
                
                # --- 5. 遷移後の全フレーム調査 (成功したスキャン構造を維持) ---
                print("\n=== [遷移後のフレーム構造スキャン] ===")
                detail_results = None
                for f in page.frames:
                    try:
                        # 成功した時詳細が出ていたURLを捕捉するためのログ
                        res = f.evaluate("() => ({ url: window.location.href, text: document.body.innerText.substring(0, 100) })")
                        print(f"Frame URL: {res['url']}")
                        
                        if "PJC503Servlet" in res['url']:
                            # 表構造からラベルと値を正確に抜き出す
                            detail_results = f.evaluate('''() => {
                                const tables = Array.from(document.querySelectorAll('table'));
                                const details = {};
                                const bidders = [];
                                
                                // 基本情報テーブルの解析
                                tables.forEach(table => {
                                    table.querySelectorAll('tr').forEach(tr => {
                                        const th = tr.querySelector('th');
                                        const td = tr.querySelector('td');
                                        if (th && td) {
                                            details[th.innerText.trim().replace(/\\s/g, "")] = td.innerText.trim();
                                        }
                                    });
                                });

                                // 入札結果テーブルの解析
                                const bidderTable = tables.find(t => t.innerText.includes('業者名'));
                                if (bidderTable) {
                                    const rows = Array.from(bidderTable.querySelectorAll('tr')).slice(1);
                                    rows.forEach(row => {
                                        const cells = Array.from(row.querySelectorAll('td')).map(c => c.innerText.trim());
                                        if (cells.length > 0 && !cells[0].includes('事前公開していません')) {
                                            bidders.push(cells);
                                        }
                                    });
                                }
                                return { details, bidders };
                            }''')
                    except: continue

                if detail_results:
                    print("★詳細情報の抽出完了。整形します。")
                    
                    # 価格クレンジング用
                    def clean_price(v):
                        if not v: return ""
                        v = v.split('(')[0] # かっこ以降を削除
                        return re.sub(r'[^\d]', '', v) # 数字以外を削除

                    # 指定された7項目
                    d_keys = ["電子入札案件番号", "工事・業務名", "場所", "予定価格", "最低制限価格", "開札（予定）日", "状態"]
                    detail_fields = []
                    for k in d_keys:
                        val = detail_results['details'].get(k, "")
                        if k in ["予定価格", "最低制限価格"]:
                            val = clean_price(val)
                        detail_fields.append(val)

                    # 入札結果（業者名, 金額1, 金額2...）
                    bidders_part = []
                    for b in detail_results['bidders']:
                        # 業者名(b[0]) + 金額列(b[1:-1])
                        name = b[0]
                        prices = [p.replace(',', '') for p in b[1:-1]]
                        bidders_part.extend([name] + prices)

                    # --- ヘッダー作成 ---
                    header = [f"一覧_{i}" for i in range(len(base_data))]
                    header += d_keys
                    for i in range(len(detail_results['bidders'])):
                        header += [f"業者_{i+1}", f"金額_{i+1}_回1"] # 簡易ヘッダー

                    # --- 保存 ---
                    full_row = base_data + detail_fields + bidders_part
                    with open('result.csv', 'w', encoding='utf-8-sig', newline='') as f:
                        writer = csv.writer(f)
                        writer.writerow(header)
                        writer.writerow(full_row)
                    
                    print(f"★全情報をCSVに保存しました: {full_row}")
                    # 戻る
                    detail_f = next(f for f in page.frames if "PJC503Servlet" in f.url)
                    detail_f.evaluate("jsBack();")
                else:
                    print("!! 詳細内容が見つかりませんでした。")
            else:
                print("!! 一覧が見つかりませんでした。")

        except Exception as e:
            print(f"重大なエラー: {e}")
        finally:
            browser.close()

if __name__ == "__main__":
    main()
