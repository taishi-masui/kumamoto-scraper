from playwright.sync_api import sync_playwright
import time
import csv
import re

def format_price(v):
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
            print("[LOG] 1. 検索条件画面を表示...")
            page.goto("https://ebid.kumamoto-idc.pref.kumamoto.jp/PPIAccepter/AccepterServlet?kikan_no=0100", wait_until="networkidle")
            time.sleep(5)
            
            # 実績コード: メニュー呼び出し
            menu_f = next((f for f in page.frames if "PJC001Servlet" in f.url), page)
            print(f"[LOG] メニューフレーム特定: {menu_f.url}")
            menu_f.evaluate("jsLink(1,1);")
            
            # --- 2. 100件設定 & 検索実行 (実績コードそのまま) ---
            print("[LOG] 2. 検索ボタンを探して100件設定＆実行...")
            search_started = False
            for _ in range(10): 
                for f in page.frames:
                    try:
                        sel = f.locator('select[name="ListCount"]')
                        if sel.count() > 0:
                            sel.select_option("100")
                            print(f"[LOG] ★100件に設定しました。(Frame: {f.url})")
                            
                        btn = f.locator('input[name="btnSearch"]')
                        if btn.count() > 0:
                            f.evaluate("jsSearch();")
                            print(f"[LOG] ★検索を実行しました。(Frame: {f.url})")
                            search_started = True
                            break
                    except: continue
                if search_started: break
                time.sleep(3)

            # --- 3. データ抽出ループ (実績コードそのまま) ---
            all_data = []
            page_num = 1
            global_count = 0
            target_count = 180 # 180番目の詳細を取得する
            
            while True:
                print(f"\n[LOG] --- ページ {page_num} 解析中 ---")
                time.sleep(15) # 実績コードの遷移待ち

                target_f = None
                for _ in range(5):
                    for f in page.frames:
                        try:
                            if f.evaluate("() => document.querySelectorAll('#tBody tr').length") > 0:
                                target_f = f
                                print(f"[LOG] 一覧フレーム特定成功: {f.url}")
                                break
                        except: continue
                    if target_f: break
                    time.sleep(3)
                
                if not target_f:
                    print("[LOG] !! データ(一覧フレーム)が見つかりません。終了します。")
                    break

                # データの抽出 (実績コードそのまま)
                rows = target_f.locator("#tBody tr").all()
                count = 0
                
                for i, r in enumerate(rows):
                    global_count += 1
                    cols = r.locator("td").all_text_contents()
                    clean_row = [c.strip().replace('\n', ' ') for c in cols if c.strip()]
                    
                    if clean_row:
                        base_data = clean_row[0:4]
                        detail_data = [""] * 27 # 詳細データ初期化
                        
                        # --- 180件目の詳細取得 ---
                        if global_count == target_count:
                            print(f"\n[LOG] ===========================================")
                            print(f"[LOG] ★ターゲット到達: {global_count}件目 (ページ内インデックス: {i})")
                            print(f"[LOG] 案件名: {base_data[2] if len(base_data)>2 else ''}")
                            print(f"[LOG] jsBidInfo({i}) を実行します...")
                            
                            target_f.evaluate(f"jsBidInfo({i});")
                            print("[LOG] 詳細画面の描画を待機します(15秒)...")
                            time.sleep(15) # 実績コードの待機時間
                            
                            # 詳細フレームの特定 (実績コードそのまま)
                            detail_f = None
                            detail_txt = ""
                            print("[LOG] 現在の全フレームURLを確認:")
                            for idx_f, f_frame in enumerate(page.frames):
                                print(f"      Frame[{idx_f}]: {f_frame.url}")
                                if "PJC503Servlet" in f_frame.url:
                                    detail_f = f_frame
                                    try:
                                        detail_txt = detail_f.evaluate("() => document.body.innerText")
                                        print(f"[LOG] 詳細フレーム(PJC503Servlet)特定成功。テキスト長: {len(detail_txt)}文字")
                                    except Exception as e:
                                        print(f"[LOG] 詳細テキスト取得エラー: {e}")
                            
                            if detail_f and detail_txt:
                                print("[LOG] 詳細テキストの解析を開始...")
                                def get_v(label):
                                    m = re.search(rf"{label}\s*([^\n\r]+)", detail_txt)
                                    res = m.group(1).strip() if m else ""
                                    print(f"      抽出[{label}]: {res}")
                                    return res

                                case_no = get_v("電子入札案件番号")
                                d_fields = [
                                    f'="{case_no}"',
                                    get_v("工事・業務名"),
                                    get_v("場所"),
                                    format_price(get_v("予定価格")),
                                    format_price(get_v("最低制限価格")),
                                    get_v("開札（予定）日"),
                                    get_v("状態")
                                ]
                                
                                b_list = []
                                try:
                                    bid_txt = detail_txt.split("摘要")[-1].split("備考")[0]
                                    print(f"[LOG] 入札情報ブロック抽出成功 (文字数: {len(bid_txt)}文字)")
                                    matches = re.findall(r"([^\t\n\r]+?)\s+([0-9,]{4,})", bid_txt)
                                    for m in matches:
                                        name = m[0].strip()
                                        if name and not name.isdigit():
                                            b_list.append([name, format_price(m[1])])
                                            print(f"      業者抽出: {name} / {format_price(m[1])}")
                                except Exception as e:
                                    print(f"[LOG] 業者抽出エラー: {e}")
                                    
                                b_fixed = []
                                for k in range(10):
                                    b_fixed.extend(b_list[k] if k < len(b_list) else ["", ""])
                                    
                                detail_data = d_fields + b_fixed
                                print("[LOG] ★詳細データの抽出と格納が完了しました。")
                                
                                # 戻る処理 (実績コードそのまま)
                                print("[LOG] jsBack() を実行して一覧に戻ります...")
                                detail_f.evaluate("jsBack();")
                                print("[LOG] 一覧への戻りを待機(15秒)...")
                                time.sleep(15)
                                
                                # ※超重要：戻った後、フレームが古いままエラーにならないよう再認識させる
                                print("[LOG] 戻り後のフレーム再取得を実施...")
                                target_f = None
                                for _ in range(5):
                                    for f in page.frames:
                                        try:
                                            if f.evaluate("() => document.querySelectorAll('#tBody tr').length") > 0:
                                                target_f = f
                                                print(f"[LOG] 一覧フレーム再特定成功: {f.url}")
                                                break
                                        except: continue
                                    if target_f: break
                                    time.sleep(3)
                            else:
                                print("[LOG] !! 詳細フレームが見つからなかった、またはテキストが空です。")
                                page.screenshot(path="debug_detail_fail.png")
                            print(f"[LOG] ===========================================")

                        all_data.append(base_data + detail_data)
                        count += 1
                
                print(f"[LOG] ページ {page_num}: {count}件取得完了 (累計: {len(all_data)}件)")

                # 「次頁」ボタンのチェック (実績コードそのまま)
                try:
                    if not target_f:
                        print("[LOG] target_f が無効なため次頁チェックをスキップして終了します。")
                        break
                    next_btn = target_f.locator('input[name="btnNextPage"]')
                    if next_btn.count() > 0 and next_btn.is_enabled():
                        print("[LOG] 「次頁」ボタンを発見。クリックします。")
                        target_f.evaluate("jsNextPage();")
                        page_num += 1
                    else:
                        print("[LOG] 最後のページです。ループを終了します。")
                        break
                except Exception as e:
                    print(f"[LOG] ボタン操作中にエラーが発生しました（遷移中）。終了します。: {e}")
                    break

            # 保存 (実績コードそのまま)
            print("\n[LOG] 全ページの処理が完了しました。CSVへ保存します。")
            if all_data:
                header = ["施行番号/案件番号", "業種 種別", "工事・業務名", "契約方法",
                          "電子入札案件番号", "詳細_工事名", "場所", "予定価格", "最低制限価格", "開札日", "状態"]
                for k in range(1, 11): header.extend([f"業者{k}", f"金額{k}"])

                with open('result.csv', 'w', encoding='utf-8-sig', newline='') as f_csv:
                    writer = csv.writer(f_csv)
                    writer.writerow(header)
                    writer.writerows(all_data)
                print(f"[LOG] ★完了！ 全 {len(all_data)} 件を保存しました。")

        except Exception as e:
            print(f"[LOG] 重大なエラー: {e}")
            page.screenshot(path="debug_fatal_error.png")
        finally:
            browser.close()

if __name__ == "__main__":
    main()
