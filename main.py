from playwright.sync_api import sync_playwright
import time
import csv
import re

def format_price(v):
    """¥マークとカンマを付与した数値文字列を返す"""
    if not v: return ""
    # カンマや円、かっこを消して数字のみにする
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
            
            # メニューから検索画面呼び出し (成功コードそのまま)
            menu_f = next((f for f in page.frames if "PJC001Servlet" in f.url), page)
            menu_f.evaluate("jsLink(1,1);")
            
            # --- 2. 100件設定 & 検索実行 (ご提示の成功コードを完全再現) ---
            print("2. 検索ボタンを探して100件設定＆実行...")
            search_started = False
            for _ in range(10): 
                for f in page.frames:
                    try:
                        # セレクトボックスがあれば100件に設定
                        sel = f.locator('select[name="ListCount"]')
                        if sel.count() > 0:
                            sel.select_option("100")
                            print("★100件に設定しました。")
                            
                        # 検索ボタンがあればjsSearch()を実行
                        btn = f.locator('input[name="btnSearch"]')
                        if btn.count() > 0:
                            f.evaluate("jsSearch();")
                            print("★検索を実行しました。")
                            search_started = True
                            break
                    except: continue
                if search_started: break
                time.sleep(3)

            # --- 3. データ抽出（80番目を狙い撃ち） ---
            print("3. 結果一覧の出現を待機中...")
            target_f = None
            for _ in range(15):
                for f in page.frames:
                    try:
                        # データがあるフレームを特定
                        if f.evaluate("() => document.querySelectorAll('#tBody tr').length") > 0:
                            target_f = f
                            break
                    except: continue
                if target_f: break
                time.sleep(3)
            
            if target_f:
                idx = 79 # 80番目
                rows = target_f.locator("#tBody tr")
                print(f"   現在の一覧表示件数: {rows.count()}件")

                # 一覧の4項目を確保
                row_el = rows.nth(idx)
                cols = row_el.locator("td").all_text_contents()
                base_data = [c.strip().replace('\n', ' ') for c in cols if c.strip()][0:4]

                # --- 4. 詳細ボタンをクリック (jsBidInfo(idx)を実行) ---
                print(f"4. 80個目の詳細ボタンをクリック(jsBidInfo({idx}))...")
                target_f.evaluate(f"jsBidInfo({idx});")
                time.sleep(15) # 遷移待ち
                
                # --- 5. 詳細フレーム特定と解析 ---
                detail_f = None
                detail_txt = ""
                for f in page.frames:
                    if "PJC503Servlet" in f.url:
                        detail_f = f
                        detail_txt = f.evaluate("() => document.body.innerText")
                        break

                if detail_f:
                    print("★詳細情報の抽出を開始...")
                    def get_val(label):
                        m = re.search(rf"{label}\s*([^\n\r]+)", detail_txt)
                        return m.group(1).strip() if m else ""

                    case_id = get_val("電子入札案件番号")
                    detail_fields = [
                        f'="{case_id}"', # エクセル0落ち防止
                        get_val("工事・業務名"),
                        get_val("場所"),
                        format_price(get_val("予定価格")),
                        format_price(get_val("最低制限価格")),
                        get_val("開札（予定）日"),
                        get_val("状態")
                    ]

                    # 業者10名固定ロジック
                    b_list = []
                    try:
                        bid_txt = detail_txt.split("摘要")[-1].split("備考")[0]
                        matches = re.findall(r"([^\t\n\r]+?)\s+([0-9,]{4,})", bid_txt)
                        for m in matches:
                            name = m[0].strip()
                            if name and not name.replace(',','').isdigit():
                                b_list.append([name, format_price(m[1])])
                    except: pass

                    bidders_part = []
                    for k in range(10):
                        if k < len(b_list):
                            bidders_part.extend(b_list[k])
                        else:
                            bidders_part.extend(["", ""])

                    # ヘッダーと保存
                    header = ["施行番号/案件番号", "業種 種別", "工事・業務名", "契約方法",
                              "電子入札案件番号", "工事・業務名", "場所", "予定価格", "最低制限価格", "開札（予定）日", "状態"]
                    for k in range(1, 11): header.extend([f"業者{k}", f"金額{k}"])

                    with open('result.csv', 'w', encoding='utf-8-sig', newline='') as f:
                        writer = csv.writer(f)
                        writer.writerow(header)
                        writer.writerow(base_data + detail_fields + bidders_part)
                    
                    print("★result.csv を保存しました。")
                    detail_f.evaluate("jsBack();")
                else:
                    print("!! 詳細フレームが見つかりませんでした。")
            else:
                print("!! 一覧が見つかりませんでした。")

        except Exception as e:
            print(f"エラー: {e}")
        finally:
            browser.close()

if __name__ == "__main__":
    main()
