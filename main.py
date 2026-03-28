from playwright.sync_api import sync_playwright
import time
import csv
import re

def format_price(v):
    """¥マークとカンマを付与した数値文字列を返す"""
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
            print("1. 検索実行...")
            page.goto("https://ebid.kumamoto-idc.pref.kumamoto.jp/PPIAccepter/AccepterServlet?kikan_no=0100", wait_until="networkidle")
            time.sleep(5)
            menu_f = next((f for f in page.frames if "PJC001Servlet" in f.url), page)
            menu_f.evaluate("jsLink(1,1);")
            
            # 検索フレーム特定
            for f in page.frames:
                if f.locator('input[name="btnSearch"]').count() > 0:
                    # すでに解決済みの「100件表示」を確実に実行
                    f.evaluate('''() => {
                        const sel = document.getElementsByName("listCount")[0];
                        if(sel) { sel.value = "100"; sel.onchange(); }
                    }''')
                    time.sleep(2)
                    f.evaluate("jsSearch();")
                    break

            print("2. 100件一覧の出現を待機中...")
            target_f = None
            for _ in range(15):
                for f in page.frames:
                    if f.evaluate("() => document.querySelectorAll('#tBody tr').length") > 0:
                        target_f = f
                        break
                if target_f: break
                time.sleep(3)
            
            if target_f:
                # 80番目 (index 79)
                idx = 79
                rows = target_f.locator("#tBody tr")
                print(f"   現在の表示件数: {rows.count()}件")

                # 一覧情報の確保
                row_el = rows.nth(idx)
                all_cells = [c.inner_text().strip().replace('\n', ' ') for c in row_el.locator("td").all()]
                base_data = all_cells[0:4]

                print(f"3. 80個目の詳細をクリック(jsBidInfo({idx}))...")
                target_f.evaluate(f"jsBidInfo({idx});")
                time.sleep(15)
                
                # 詳細フレーム特定
                detail_f = None
                detail_txt = ""
                for f in page.frames:
                    if "PJC503Servlet" in f.url:
                        detail_f = f
                        detail_txt = f.evaluate("() => document.body.innerText")
                        break

                if detail_f:
                    print("4. 解析と保存...")
                    def get_val(label):
                        m = re.search(rf"{label}\s*([^\n\r]+)", detail_txt)
                        return m.group(1).strip() if m else ""

                    case_id = get_val("電子入札案件番号")
                    detail_fields = [
                        f'="{case_id}"', # 0落ち防止
                        get_val("工事・業務名"),
                        get_val("場所"),
                        format_price(get_val("予定価格")),
                        format_price(get_val("最低制限価格")),
                        get_val("開札（予定）日"),
                        get_val("状態")
                    ]

                    # 業者10名固定
                    b_list = []
                    try:
                        bid_txt = detail_txt.split("摘要")[-1].split("備考")[0]
                        matches = re.findall(r"([^\t\n\r]+?)\s+([0-9,]{4,})", bid_txt)
                        for m in matches:
                            if not m[0].strip().isdigit():
                                b_list.append([m[0].strip(), format_price(m[1])])
                    except: pass

                    bidders_part = []
                    for k in range(10):
                        bidders_part.extend(b_list[k] if k < len(b_list) else ["", ""])

                    # 保存
                    header = ["施行番号/案件番号", "業種 種別", "工事・業務名", "契約方法",
                              "電子入札案件番号", "工事・業務名", "場所", "予定価格", "最低制限価格", "開札（予定）日", "状態"]
                    for k in range(1, 11): header.extend([f"業者{k}", f"金額{k}"])

                    with open('result.csv', 'w', encoding='utf-8-sig', newline='') as f:
                        writer = csv.writer(f)
                        writer.writerow(header)
                        writer.writerow(base_data + detail_fields + bidders_part)
                    
                    print("★result.csv を保存しました。")
                    detail_f.evaluate("jsBack();")

        except Exception as e:
            print(f"エラー: {e}")
        finally:
            browser.close()

if __name__ == "__main__":
    main()
