from playwright.sync_api import sync_playwright
import time
import csv
import re

def format_price(v):
    """金額に¥マークとカンマを付与する"""
    if not v: return ""
    num_str = re.sub(r'[^\d]', '', v.split('(')[0])
    if not num_str: return ""
    return f"¥{int(num_str):,}"

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
            
            print("2. 検索実行...")
            search_started = False
            for _ in range(10): 
                for f in page.frames:
                    try:
                        # 100件表示設定を追加 (全件取得のため)
                        sel = f.locator('select[name="ListCount"]')
                        if sel.count() > 0:
                            sel.select_option("100")

                        btn = f.locator('input[name="btnSearch"]')
                        if btn.count() > 0:
                            f.evaluate("jsSearch();")
                            search_started = True
                            break
                    except: continue
                if search_started: break
                time.sleep(3)

            # 結果格納用
            all_data_rows = []
            header = []
            page_num = 1
            global_idx = 1

            # --- 全ページを巡回するループ ---
            while True:
                print(f"\n=== ページ {page_num} の処理を開始 ===")

                print("3. 結果一覧の出現を待機...")
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
                    print("!! 一覧が見つからないため終了します。")
                    break

                # 現在のページの全行数を取得
                rows_count = target_f.locator("#tBody tr").count()
                print(f"ページ {page_num}: 全 {rows_count} 件のデータを処理します。")

                # --- ページ内の全行を1件ずつ処理するループ ---
                for i in range(rows_count):
                    print(f"\n--- [累計 {global_idx} 件目] の詳細を取得中 ---")
                    
                    # 再度一覧フレームを特定 (戻る処理の後はフレームがリセットされるため)
                    for _ in range(5):
                        for f in page.frames:
                            try:
                                if f.evaluate("() => document.querySelectorAll('#tBody tr').length") > 0:
                                    target_f = f
                                    break
                            except: continue
                        if target_f: break
                        time.sleep(2)

                    rows = target_f.locator("#tBody tr")
                    
                    # 一覧情報を取得
                    row_el = rows.nth(i)
                    all_cells = [c.inner_text().strip().replace('\n', ' ') for c in row_el.locator("td").all()]
                    base_data = all_cells[0:4] 

                    print(f"4. 詳細ボタン(jsBidInfo({i}))をクリック...")
                    target_f.evaluate(f"jsBidInfo({i});")
                    time.sleep(15)
                    
                    # --- 5. 遷移後の全フレーム調査 (実績コードそのまま) ---
                    detail_txt = ""
                    detail_f = None
                    for frame_idx, f in enumerate(page.frames):
                        try:
                            res = f.evaluate("() => ({ url: window.location.href, text: document.body.innerText })")
                            if "PJC503Servlet" in res['url']:
                                detail_f = f
                                detail_txt = res['text']
                        except: continue

                    if detail_f:
                        print("★詳細情報の解析...")
                        
                        def get_v(label):
                            m = re.search(rf"{label}\s*([^\n\r]+)", detail_txt)
                            if not m: return ""
                            return m.group(1).strip()

                        case_id = get_v("電子入札案件番号")
                        
                        # 詳細基本7項目 (¥マークと0落ち防止を適用)
                        detail_fields = [
                            f'="{case_id}"', 
                            get_v("工事・業務名"), 
                            get_v("場所"),
                            format_price(get_v("予定価格")), 
                            format_price(get_v("最低制限価格")), 
                            get_v("開札（予定）日"), 
                            get_v("状態")
                        ]

                        # 入札結果（業者10社分固定）
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
                                if k < len(valid_bidders):
                                    bidders_part.extend(valid_bidders[k])
                                else:
                                    bidders_part.extend(["", ""])
                        except:
                            bidders_part = [""] * 20

                        # ヘッダー作成（初回のみ）
                        if not header:
                            header = ["施行番号/案件番号", "業種 種別", "工事・業務名", "契約方法"]
                            header += ["電子入札案件番号", "工事・業務名", "場所", "予定価格", "最低制限価格", "開札（予定）日", "状態"]
                            for k in range(1, 11):
                                header.extend([f"業者{k}", f"金額{k}"])

                        # 1行分をリストに追加
                        all_data_rows.append(base_data + detail_fields + bidders_part)
                        
                        print("★保存完了。戻ります。")
                        detail_f.evaluate("jsBack();")
                        time.sleep(10) # 戻った後の描画待ち
                    else:
                        print("!! 詳細フレームが見つかりませんでした。")
                        
                    global_idx += 1

                # --- ページ内の全行処理完了 ---
                # 次のページがあるか確認
                print("\nページ内の全件処理が完了しました。「次頁」ボタンを探します...")
                try:
                    next_btn = target_f.locator('input[name="btnNextPage"]')
                    if next_btn.count() > 0 and next_btn.is_enabled():
                        print("「次頁」ボタンをクリックして次のページへ進みます。")
                        target_f.evaluate("jsNextPage();")
                        page_num += 1
                        time.sleep(15) # ページ遷移待ち
                    else:
                        print("最後のページに到達しました。全処理を終了します。")
                        break
                except Exception as e:
                    print(f"次ページへの遷移中にエラーが発生しました: {e}")
                    break

            # --- 全件終了後にCSV書き出し ---
            if all_data_rows:
                with open('result.csv', 'w', encoding='utf-8-sig', newline='') as f:
                    writer = csv.writer(f)
                    writer.writerow(header)
                    writer.writerows(all_data_rows)
                print(f"\n★全 {len(all_data_rows)} 件の詳細保存が完了しました。")

        except Exception as e:
            print(f"エラー: {e}")
        finally:
            browser.close()

if __name__ == "__main__":
    main()
