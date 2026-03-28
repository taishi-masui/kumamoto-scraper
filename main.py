from playwright.sync_api import sync_playwright
import time
import csv

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
            time.sleep(10)

            print("2. 表示件数を100件に切り替え中...")
            count_set_success = False
            for f in page.frames:
                try:
                    # 確定した名前 'ListCount' で検索
                    target_select = f.locator('select[name="ListCount"]')
                    if target_select.count() > 0:
                        # 値 '100' を選択
                        target_select.select_option("100")
                        print(f"★フレーム '{f.name}' にて表示件数を100件に設定しました。")
                        count_set_success = True
                        break
                except:
                    continue

            if not count_set_success:
                print("!! 表示件数の選択窓(ListCount)が見つかりませんでした。")

            print("3. 検索実行...")
            # 全フレームに対して jsSearch を実行
            page.evaluate('''() => {
                const trigger = (w) => {
                    try { if (typeof w.jsSearch === "function") w.jsSearch(); } catch (e) {}
                    for (let i = 0; i < w.frames.length; i++) trigger(w.frames[i]);
                };
                trigger(window);
            }''')
            
            print("4. 結果の出現を監視中...")
            found_data = False
            start_time = time.time()
            
            while time.time() - start_time < 30:
                for f in page.frames:
                    try:
                        # 以前成功した #tBody tr を探す
                        row_count = f.evaluate("() => document.querySelectorAll('#tBody tr').length")
                        if row_count > 0:
                            print(f"★データ捕捉！ {row_count} 件の表示を確認しました。")
                            
                            rows = f.locator("#tBody tr").all()
                            scraped_data = []
                            for r in rows:
                                cols = r.locator("td").all_text_contents()
                                clean_row = [c.strip().replace('\\n', ' ').replace('\\t', ' ') for c in cols if c.strip()]
                                if clean_row: scraped_data.append(clean_row)
                            
                            if scraped_data:
                                with open('result.csv', 'w', encoding='utf-8-sig', newline='') as f_csv:
                                    writer = csv.writer(f_csv)
                                    writer.writerows(scraped_data)
                                print(f"--- result.csv に {len(scraped_data)} 件保存しました ---")
                                found_data = True
                                break
                    except:
                        continue
                if found_data: break
                time.sleep(2)

        except Exception as e:
            print(f"エラー発生: {e}")
        finally:
            browser.close()

if __name__ == "__main__":
    main()
