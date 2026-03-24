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
            
            # メニューフレームから検索開始
            menu_f = next((f for f in page.frames if "PJC001Servlet" in f.url), page)
            menu_f.evaluate("jsLink(1,1);")
            time.sleep(10)

            print("2. 検索実行命令を発行（全フレーム対象）...")
            # どのフレームにjsSearchがあってもいいように一斉実行し、エラーは無視
            page.evaluate('''() => {
                const trigger = (w) => {
                    try { if (typeof w.jsSearch === "function") w.jsSearch(); } catch (e) {}
                    for (let i = 0; i < w.frames.length; i++) trigger(w.frames[i]);
                };
                trigger(window);
            }''')
            
            print("3. 結果テーブルの出現を監視中（最大30秒）...")
            found_data = False
            start_time = time.time()
            
            # 30秒間、しつこく全フレームをチェックし続ける
            while time.time() - start_time < 30:
                for f in page.frames:
                    try:
                        # フレームが生きているか、かつ #tBody があるか
                        row_count = f.evaluate("() => document.querySelectorAll('#tBody tr').length")
                        if row_count > 0:
                            print(f"★データ捕捉！ フレーム '{f.name}' に {row_count} 件あります。")
                            
                            # データの抽出
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
                                print("--- result.csv に保存しました ---")
                                found_data = True
                                break
                    except:
                        continue
                
                if found_data: break
                time.sleep(2) # 2秒おきに再スキャン

            if not found_data:
                print("!! タイムアウト：結果が見つかりませんでした。")
                page.screenshot(path="debug_after_click.png", full_page=True)

        except Exception as e:
            print(f"実行中にエラー: {e}")
        finally:
            browser.close()

if __name__ == "__main__":
    main()
