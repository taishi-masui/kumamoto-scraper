from playwright.sync_api import sync_playwright
import time
import csv
import re

def format_price(v):
    """円やカンマを消し、¥マークとカンマを付与。空なら空。"""
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
            
            # メニュー操作 (成功コードそのまま)
            menu_f = next((f for f in page.frames if "PJC001Servlet" in f.url), page)
            menu_f.evaluate("jsLink(1,1);")
            time.sleep(5)

            # --- 2. 100件設定 & 検索実行 (成功コード完全再現) ---
            print("2. 検索ボタンを探して100件設定＆実行...")
            search_started = False
            for _ in range(10): 
                for f in page.frames:
                    try:
                        # 成功コードのセレクタ
                        sel = f.locator('select[name="ListCount"]')
                        if sel.count() > 0:
                            sel.select_option("100")
                            print(f"   [SUCCESS] 100件に設定完了 (URL: {f.url})")
                            
                        btn = f.locator('input[name="btnSearch"]')
                        if btn.count() > 0:
                            print(f"   [SUCCESS] 検索ボタン発見、jsSearch()実行 (URL: {f.url})")
                            f.evaluate("jsSearch();")
                            search_started = True
                            break
                    except: continue
                if search_started: break
                time.sleep(3)

            # --- 3. 一覧待機 (URL判定を強化) ---
            print("3. 結果一覧の出現を待機中...")
            target_f = None
            for retry in range(20):
                for f in page.frames:
                    # PJC502Servlet が一覧。tBodyの中身があれば成功
                    if "PJC502Servlet" in f.url:
                        try:
                            if f.evaluate("() => document.querySelectorAll('#tBody tr').length") > 0:
                                target_f = f
                                break
                        except: continue
                if target_f: break
                print(f"   一覧待機中... ({retry+1}/20)")
                time.sleep(2)
            
            if target_f:
                idx = 79 # 80番目
                rows = target_f.locator("#tBody tr")
                count = rows.count()
                print(f"★現在の一覧表示件数: {count}件")

                # 一覧の4項目を確保
                row_el = rows.nth(idx)
                cols = row_el.locator("td").all_text_contents()
                base_data = [c.strip().replace('\n', ' ') for c in cols if c.strip()][0:4]
                print(f"★80個目の基本データ: {base_data}")

                # --- 4. 詳細ボタンをクリック (成功コードの evaluate 実行) ---
                print(f"4. 80個目の詳細ボタンをクリック(jsBidInfo({idx}))...")
                target_f.evaluate(f"jsBidInfo({idx});")
                
                # --- 5. 詳細フレーム (PJC503Servlet) の出現を動的に監視 ---
                print("5. 詳細画面(PJC503Servlet)への遷移を監視します...")
                detail_f = None
                for sec in range(30):
                    # 毎秒全フレームをチェック。URLにPJC503Servletが含まれるものを探す
                    for f in page.frames:
                        if "PJC503Servlet" in f.url:
                            detail_f = f
                            break
                    if detail_f:
                        print(f"   [SUCCESS] {sec}秒後に詳細フレームを捕捉しました。")
                        break
                    if sec % 5 == 0:
                        # 5秒おきに現在の全フレームURLをログ出し
                        urls = [f.url for f in page.frames]
                        print(f"   ...監視中({sec}秒経過)。現在存在するフレームURL: {urls}")
                    time.sleep(1)

                if detail_f:
                    print("6. データの抽出を開始します。")
                    time.sleep(3) # 完全な描画を待つ
                    detail_txt = detail_f.evaluate("() => document.body.innerText")

                    def get_val(label):
                        # ラベルに続く文字列を抽出
                        m = re.search(rf"{label}\s*([^\n\r]+)", detail_txt)
                        return m.group(1).strip() if m else ""

                    case_id = get_val("電子入札案件番号")
                    detail_fields = [
                        f'="{case_id}"', # Excel 0落ち防止
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
                        # 摘要以降〜備考まで
                        parts = detail_txt.split("摘要")
                        if len(parts) > 1:
                            bid_txt = parts[-1].split("備考")[0]
                            # 業者名と金額のペアを抽出
                            matches = re.findall(r"([^\t\n\r]+?)\s+([0-9,]{4,})", bid_txt)
                            for m in matches:
                                if not m[0].strip().isdigit():
                                    b_list.append([m[0].strip(), format_price(m[1])])
                    except: pass

                    bidders_part = []
                    for k in range(10):
                        if k < len(b_list): bidders_part.extend(b_list[k])
                        else: bidders_part.extend(["", ""])

                    # ヘッダー定義
                    header = ["施行番号/案件番号", "業種 種別", "工事・業務名", "契約方法",
                              "電子入札案件番号", "工事・業務名", "場所", "予定価格", "最低制限価格", "開札（予定）日", "状態"]
                    for k in range(1, 11):
                        header.extend([f"業者{k}", f"金額{k}"])

                    # 保存
                    with open('result.csv', 'w', encoding='utf-8-sig', newline='') as f:
                        writer = csv.writer(f)
                        writer.writerow(header)
                        writer.writerow(base_data + detail_fields + bidders_part)
                    
                    print(f"★すべての情報を保存しました。")
                    detail_f.evaluate("jsBack();")
                else:
                    print("!! エラー: 詳細画面(PJC503Servlet)に到達できませんでした。")
                    page.screenshot(path="debug_timeout.png")
            else:
                print("!! エラー: 一覧画面が表示されませんでした。")
                page.screenshot(path="debug_no_list.png")

        except Exception as e:
            print(f"重大なエラー: {e}")
        finally:
            browser.close()

if __name__ == "__main__":
    main()
