from playwright.sync_api import sync_playwright
import time
import csv
import re
from bs4 import BeautifulSoup

def parse_all_details(html_content):
    """詳細画面のHTMLを解析。項目がない場合は空文字を返す。"""
    soup = BeautifulSoup(html_content, 'html.parser')
    data = {}

    # --- 1. 基本情報の解析 ---
    base_table = None
    for table in soup.find_all('table'):
        # 「施行番号」という文字が含まれるテーブルを基本情報とみなす
        if table.find(string=re.compile('施行番号')):
            base_table = table
            break
    
    if base_table:
        for row in base_table.find_all('tr'):
            ths = row.find_all('th')
            tds = row.find_all('td')
            if len(ths) >= 1 and len(tds) >= 1:
                key = ths[0].get_text(strip=True)
                val = tds[0].get_text(strip=True)
                
                # 金額系のクレンジング（かっこ削除・数字のみ）
                if key in ['予定価格', '最低制限価格'] and val:
                    # 「(」より前の部分を取り出し、数字以外を除去
                    val = val.split('(')[0]
                    val = val.replace('円', '').replace(',', '').strip()
                
                data[key] = val

    # --- 2. 入札結果の解析 ---
    result_table = None
    for table in soup.find_all('table'):
        if table.find(string=re.compile('業者名')):
            result_table = table
            break
    
    bidders_output = []
    if result_table:
        # 第何回まであるかヘッダーを確認
        header_row = result_table.find('tr')
        price_indices = [] # 金額が入っている列番号を記録
        if header_row:
            ths = header_row.find_all('th')
            for idx, th in enumerate(ths):
                if re.search(r'第.*回', th.get_text()):
                    price_indices.append(idx)

        # データ行の抽出
        rows = result_table.find_all('tr')[1:] # ヘッダー以外
        for row in rows:
            tds = row.find_all('td')
            if len(tds) > 0:
                name = tds[0].get_text(strip=True)
                if not name or "本入札の指名業者" in name: continue
                
                prices = []
                for idx in price_indices:
                    if idx < len(tds):
                        p = tds[idx].get_text(strip=True).replace(',', '')
                        prices.append(p)
                bidders_output.append([name] + prices)

    # --- 3. データのフラット化（列の固定） ---
    # 必ず取得したい項目を定義
    target_keys = ['電子入札案件番号', '工事・業務名', '場所', '予定価格', '最低制限価格', '開札（予定）日', '状態']
    result_row = [data.get(k, '') for k in target_keys]
    
    # 入札結果を末尾に結合（業者1, 金額1, 金額2..., 業者2...）
    for bidder in bidders_output:
        result_row.extend(bidder)
        
    return result_row

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
            
            # 2. 検索実行 (成功コードを維持)
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

            # 3. 一覧待機
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
                print("4. 1件目の詳細を取得開始...")
                target_f.evaluate("jsBidInfo(0);")
                time.sleep(15)
                
                # 5. フレームスキャン（成功コードを維持）
                detail_f = None
                for i, f in enumerate(page.frames):
                    try:
                        if "PJC503Servlet" in f.url:
                            detail_f = f
                            break
                    except: continue

                if detail_f:
                    # HTML取得と解析
                    html_content = detail_f.content()
                    final_data = parse_all_details(html_content)
                    
                    # CSV保存
                    with open('result.csv', 'w', encoding='utf-8-sig', newline='') as f:
                        writer = csv.writer(f)
                        writer.writerow(final_data)
                    
                    print(f"★抽出完了: {final_data}")
                    
                    # 戻る
                    detail_f.evaluate("jsBack();")
                    time.sleep(5)
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
