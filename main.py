from playwright.sync_api import sync_playwright
import time
import csv
import re

def format_price(v):
    """円やカンマを消し、¥マークとカンマを付与。"""
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
            
            # メニューから検索画面呼び出し (成功コード流用)
            menu_f = next((f for f in page.frames if "PJC001Servlet" in f.url), page)
            menu_f.evaluate("jsLink(1,1);")
            
            # --- 2. 100件設定 & 検索実行 (189件取得時の成功コードそのまま) ---
            print("2. 検索ボタンを探して100件設定＆実行...")
            search_started = False
            for _ in range(10): 
                for f in page.frames:
                    try:
                        sel = f.locator('select[name="ListCount"]')
                        if sel.count() > 0:
                            sel.select_option("100")
                            print("★100件に設定しました。")
                        btn = f.locator('input[name="btnSearch"]')
                        if btn.count() > 0:
                            f.evaluate("jsSearch();")
                            print("★検索を実行しました。")
                            search_started = True
                            break
                    except: continue
                if search_started: break
                time.sleep(3)

            # --- 3. データ抽出ループ (189件取得ロジックに詳細取得を統合) ---
            all_rows = []
            page_num = 1
            global_count = 0
            target_index = 180  # 180番目の工事をターゲットに設定
            
            # ヘッダー定義
            header = ["施行番号/案件番号", "業種 種別", "工事・業務名", "契約方法",
                      "電子入札案件番号", "詳細_工事名", "場所", "予定価格", "最低制限価格", "開札日", "状態"]
            for k in range(1, 11): header.extend([f"業者{k}", f"金額{k}"])

            while True:
                print(f"\n--- ページ {page_num} 解析中 ---")
                time.sleep(15) # 成功コードの遷移待ち

                target_f = None
                for _ in range(5):
                    for f in page.frames:
                        try:
                            if f.evaluate("() => document.querySelectorAll('#tBody tr').length") > 0:
                                target_f = f
                                break
                        except: continue
                    if target_f: break
                    time.sleep(3)
                
                if not target_f:
                    print("データが見つかりません。終了します。")
                    break

                # 現在のページの行を取得
                rows_count = target_f.locator("#tBody tr").count()
                
                for i in range(rows_count):
                    global_count += 1
                    row_el = target_f.locator("#tBody tr").nth(i)
                    cols = row_el.locator("td").all_text_contents()
                    # 一覧の4項目
                    base_data = [c.strip().replace('\n', ' ') for c in cols if c.strip()][0:4]
                    
                    # 詳細情報の初期化（空欄）
                    detail_data = [""] * 27 # 7項目 + 業者20項目
                    
                    # --- 指定の番号（180件目）だけ詳細を取得 ---
                    if global_count == target_index:
                        print(f"★ターゲット発見: {global_count}件目。詳細を取得します...")
                        target_f.evaluate(f"jsBidInfo({i});")
                        
                        # 詳細画面の出現を待機
                        detail_f = None
                        for _ in range(30):
                            for f in page.frames:
                                if "PJC503Servlet" in f.url:
                                    detail_f = f
                                    break
                            if detail_f: break
                            time.sleep(1)
                        
                        if detail_f:
                            time.sleep(3)
                            detail_txt = detail_f.evaluate("() => document.body.innerText")
                            
                            def get_v(label):
                                m = re.search(rf"{label}\s*([^\n\r]+)", detail_txt)
                                return m.group(1).strip() if m else ""

                            # 詳細7項目
                            d_fields = [
                                f'="{get_v("電子入札案件番号")}"',
                                get_v("工事・業務名"),
                                get_v("場所"),
                                format_price(get_v("予定価格")),
                                format_price(get_v("最低制限価格")),
                                get_v("開札（予定）日"),
                                get_v("状態")
                            ]
                            
                            # 業者10名固定
                            b_list = []
                            try:
                                bid_txt = detail_txt.split("摘要")[-1].split("備考")[0]
                                matches = re.findall(r"([^\t\n\r]+?)\s+([0-9,]{4,})", bid_txt)
                                valid = [[m[0].strip(), format_price(m[1])] for m in matches if not m[0].strip().isdigit()]
                                for k in range(10): b_list.extend(valid[k] if k < len(valid) else ["", ""])
                            except: b_list = [""] * 20
                            
                            detail_data = d_fields + b_list
                            print(f"  -> 抽出完了: {base_data[2]}")
                            
                            # 一覧に戻る
                            detail_f.evaluate("jsBack();")
                            time.sleep(10) # 戻り待ち
                    
                    all_rows.append(base_data + detail_data)

                # 「次頁」ボタンのチェック (成功コードそのまま)
                try:
                    next_btn = target_f.locator('input[name="btnNextPage"]')
                    if next_btn.count() > 0 and next_btn.is_enabled():
                        print("「次頁」をクリックします。")
                        target_f.evaluate("jsNextPage();")
                        page_num += 1
                    else:
                        print("最後のページです。")
                        break
                except:
                    break

            # 保存
            if all_rows:
                with open('result.csv', 'w', encoding='utf-8-sig', newline='') as f:
                    writer = csv.writer(f)
                    writer.writerow(header)
                    writer.writerows(all_rows)
                print(f"\n★完了！ 全 {len(all_rows)} 件を保存しました。ターゲット({target_index}件目)の詳細も含みます。")

        except Exception as e:
            print(f"エラー: {e}")
        finally:
            browser.close()

if __name__ == "__main__":
    main()
