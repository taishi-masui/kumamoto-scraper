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
            print("1. 検索実行（実績コード通り）...")
            page.goto("https://ebid.kumamoto-idc.pref.kumamoto.jp/PPIAccepter/AccepterServlet?kikan_no=0100", wait_until="networkidle")
            time.sleep(5)
            menu_f = next((f for f in page.frames if "PJC001Servlet" in f.url), page)
            menu_f.evaluate("jsLink(1,1);")
            
            # 100件設定 & 検索 (成功実績そのまま)
            search_started = False
            for _ in range(10): 
                for f in page.frames:
                    try:
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

            all_rows = []
            page_num = 1
            global_count = 0

            while True:
                print(f"\n--- ページ {page_num} 解析中 ---")
                time.sleep(15) # 成功実績の待機時間

                # 一覧フレーム特定 (成功実績そのまま)
                target_f = None
                for _ in range(5):
                    for f in page.frames:
                        if f.evaluate("() => document.querySelectorAll('#tBody tr').length") > 0:
                            target_f = f
                            break
                    if target_f: break
                    time.sleep(3)
                
                if not target_f: break

                rows = target_f.locator("#tBody tr")
                rows_count = rows.count()
                
                for i in range(rows_count):
                    global_count += 1
                    row_el = rows.nth(i)
                    cols = row_el.locator("td").all_text_contents()
                    base_data = [c.strip().replace('\n', ' ') for c in cols if c.strip()][0:4]
                    
                    detail_data = [""] * 27 # 詳細情報の器

                    # --- 180件目のみ詳細取得 (成功実績のある抽出ロジック) ---
                    if global_count == 180:
                        print(f"★180件目に到達。詳細を取得します...")
                        target_f.evaluate(f"jsBidInfo({i});")
                        
                        # 詳細フレーム出現待ち
                        detail_f = None
                        for _ in range(30):
                            for f in page.frames:
                                if "PJC503Servlet" in f.url:
                                    detail_f = f
                                    break
                            if detail_f: break
                            time.sleep(1)
                        
                        if detail_f:
                            time.sleep(5) # 描画待ち
                            detail_txt = detail_f.evaluate("() => document.body.innerText")
                            
                            # 成功実績のある正規表現抽出
                            def get_v(label):
                                m = re.search(rf"{label}\s*([^\n\r]+)", detail_txt)
                                return m.group(1).strip() if m else ""

                            d_fields = [
                                f'="{get_v("電子入札案件番号")}"',
                                get_v("工事・業務名"),
                                get_v("場所"),
                                format_price(get_v("予定価格")),
                                format_price(get_v("最低制限価格")),
                                get_v("開札（予定）日"),
                                get_v("状態")
                            ]
                            
                            # 業者10名固定ロジック
                            b_list = []
                            try:
                                bid_txt = detail_txt.split("摘要")[-1].split("備考")[0]
                                matches = re.findall(r"([^\t\n\r]+?)\s+([0-9,]{4,})", bid_txt)
                                for m in matches:
                                    name = m[0].strip()
                                    if name and not name.isdigit():
                                        b_list.append([name, format_price(m[1])])
                                b_fixed = []
                                for k in range(10): b_fixed.extend(b_list[k] if k < len(b_list) else ["", ""])
                                b_list = b_fixed
                            except: b_list = [""] * 20
                            
                            detail_data = d_fields + b_list
                            print(f"   抽出完了: {base_data[2]}")
                            
                            # 戻る
                            detail_f.evaluate("jsBack();")
                            time.sleep(10)
                    
                    all_rows.append(base_data + detail_data)

                # 次ページ送り (成功実績そのまま)
                next_btn = target_f.locator('input[name="btnNextPage"]')
                if next_btn.count() > 0 and next_btn.is_enabled():
                    print("「次頁」をクリック...")
                    target_f.evaluate("jsNextPage();")
                    page_num += 1
                else:
                    break

            # 保存
            header = ["施行番号/案件番号", "業種 種別", "工事・業務名", "契約方法",
                      "電子入札案件番号", "詳細_工事名", "場所", "予定価格", "最低制限価格", "開札日", "状態"]
            for k in range(1, 11): header.extend([f"業者{k}", f"金額{k}"])

            with open('result.csv', 'w', encoding='utf-8-sig', newline='') as f:
                writer = csv.writer(f)
                writer.writerow(header)
                writer.writerows(all_rows)
            print(f"★全 {len(all_rows)} 件完了。")

        except Exception as e:
            print(f"エラー: {e}")
        finally:
            browser.close()

if __name__ == "__main__":
    main()
