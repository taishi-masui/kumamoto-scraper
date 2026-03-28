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
            
            # --- 2. 検索実行 (成功ルートそのまま) ---
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
                # 一覧情報を取得
                row = target_f.locator("#tBody tr").first
                base_data = [c.strip().replace('\n', ' ') for c in row.locator("td").all_text_contents() if c.strip()]

                print("4. 1行目の『入札情報』ボタン(jsBidInfo(0))をクリック...")
                target_f.evaluate("jsBidInfo(0);")
                print("クリック完了。画面の切り替えを待ちます（15秒）...")
                time.sleep(15)
                
                # --- 5. 遷移後の全フレーム調査 (成功コードそのまま) ---
                print("\n=== [遷移後のフレーム構造スキャン] ===")
                detail_f = None
                for i, f in enumerate(page.frames):
                    try:
                        res = f.evaluate('''() => {
                            return {
                                url: window.location.href,
                                text: document.body.innerText.substring(0, 500).replace(/\\n/g, ' '),
                                tables: document.querySelectorAll('table').length
                            }
                        }''')
                        print(f"Frame[{i}] URL: {res['url']}")
                        print(f"  内容: {res['text']}...")
                        
                        if "PJC503Servlet" in res['url']:
                            detail_f = f
                    except: continue

                # --------------------------------------------------
                # 追加：標準ライブラリ(re)のみで全項目を抽出
                # --------------------------------------------------
                if detail_f:
                    full_text = detail_f.evaluate("() => document.body.innerText")
                    
                    # 各項目を抽出する関数（存在しない場合は空文字）
                    def get_val(label):
                        match = re.search(rf"{label}\t*([^\n]+)", full_text)
                        if not match: return ""
                        val = match.group(1).strip()
                        # 価格の場合は数字以外（かっこ、円、カンマ）を除去
                        if "価格" in label:
                            val = val.split('(')[0].replace('円', '').replace(',', '').strip()
                        return val

                    # 指定された全項目を取得
                    extracted_fields = [
                        get_val("電子入札案件番号"),
                        get_val("工事・業務名"),
                        get_val("場所"),
                        get_val("予定価格"),
                        get_val("最低制限価格"),
                        get_val("開札（予定）日"),
                        get_val("状態")
                    ]
                    
                    # 業者名と金額（タブ区切りの構造から簡易的に抽出）
                    # 業者名は「(株)」などで始まることが多いが、ここでは「業者名」以降の行を解析
                    bidders_part = full_text.split("業者名")[-1].split("備考")[0]
                    bidders = re.findall(r"([^\t\n]+)\t+([0-9,]+)", bidders_part)
                    
                    for b_name, b_price in bidders:
                        extracted_fields.append(b_name.strip())
                        extracted_fields.append(b_price.replace(',', '').strip())

                    # CSV保存
                    with open('result.csv', 'w', encoding='utf-8-sig', newline='') as csvfile:
                        writer = csv.writer(csvfile)
                        writer.writerow(extracted_fields)
                    
                    print(f"\n★全情報を抽出しました: {extracted_fields}")
                    detail_f.evaluate("jsBack();")
                    time.sleep(5)

                page.screenshot(path="debug_detail_frame.png", full_page=True)
                print("\n完了。")
            else:
                print("!! 一覧フレームが見つかりませんでした。")

        except Exception as e:
            print(f"重大なエラー: {e}")
        finally:
            browser.close()

if __name__ == "__main__":
    main()
