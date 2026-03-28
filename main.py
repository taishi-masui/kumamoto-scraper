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
            
            print("2. 検索実行...")
            search_started = False
            for _ in range(10): 
                for f in page.frames:
                    try:
                        btn = f.locator('input[name="btnSearch"]')
                        if btn.count() > 0:
                            f.evaluate("jsSearch();")
                            search_started = True
                            break
                    except: continue
                if search_started: break
                time.sleep(3)

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
            
            if target_f:
                # --- 一覧情報を取得（画像1枚目の4項目分に絞る） ---
                row_el = target_f.locator("#tBody tr").nth(0)
                all_cells = [c.inner_text().strip().replace('\n', ' ') for c in row_el.locator("td").all()]
                # 施行番号/番号, 業種/種別, 工事名, 契約方法 の4つを抽出
                base_data = all_cells[0:4] 

                print("4. 詳細ボタンをクリック...")
                target_f.evaluate("jsBidInfo(0);")
                time.sleep(15)
                
                # --- 5. 遷移後の全フレーム調査 ---
                print("\n=== [遷移後のフレーム構造スキャン] ===")
                detail_txt = ""
                detail_f = None
                for i, f in enumerate(page.frames):
                    try:
                        res = f.evaluate("() => ({ url: window.location.href, text: document.body.innerText })")
                        print(f"Frame[{i}] URL: {res['url']}")
                        if "PJC503Servlet" in res['url']:
                            detail_f = f
                            detail_txt = res['text']
                    except: continue

                if detail_f:
                    print("\n★詳細情報の解析（固定レイアウト）...")
                    
                    def get_v(label):
                        m = re.search(rf"{label}\s*([^\n\r]+)", detail_txt)
                        if not m: return ""
                        v = m.group(1).strip()
                        if "価格" in label:
                            v = v.split('(')[0].replace('円', '').replace(',', '').strip()
                        return v

                    # 詳細基本7項目
                    detail_fields = [
                        get_v("電子入札案件番号"), get_v("工事・業務名"), get_v("場所"),
                        get_v("予定価格"), get_v("最低制限価格"), get_v("開札（予定）日"), get_v("状態")
                    ]

                    # 入札結果（業者10社分固定）
                    bidders_part = []
                    try:
                        bid_txt = detail_txt.split("摘要")[-1].split("備考")[0]
                        # 業者名と金額のペアを抽出
                        matches = re.findall(r"([^\t\n\r]+?)\s+([0-9,]{4,})", bid_txt)
                        valid_bidders = []
                        for name, price in matches:
                            n = name.strip()
                            if n and not n.replace(',','').isdigit():
                                valid_bidders.append([n, price.replace(',', '').strip()])
                        
                        # 10社分を埋める（足りなければ空、多ければカット）
                        for k in range(10):
                            if k < len(valid_bidders):
                                bidders_part.extend(valid_bidders[k])
                            else:
                                bidders_part.extend(["", ""])
                    except:
                        bidders_part = [""] * 20

                    # --- ヘッダー作成 ---
                    header = ["施行番号/案件番号", "業種 種別", "工事・業務名", "契約方法"]
                    header += ["電子入札案件番号", "工事・業務名", "場所", "予定価格", "最低制限価格", "開札（予定）日", "状態"]
                    for k in range(1, 11):
                        header.extend([f"業者{k}", f"金額{k}"])

                    # --- 保存 ---
                    full_row = base_data + detail_fields + bidders_part
                    with open('result.csv', 'w', encoding='utf-8-sig', newline='') as f:
                        writer = csv.writer(f)
                        writer.writerow(header)
                        writer.writerow(full_row)
                    
                    print(f"★保存完了。")
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
