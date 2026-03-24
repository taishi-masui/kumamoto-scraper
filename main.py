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
            # メニューから検索画面呼び出し
            menu_f = next((f for f in page.frames if "PJC001Servlet" in f.url), page)
            menu_f.evaluate("jsLink(1,1);")
            time.sleep(10)

            print("2. 検索実行（jsSearchを実行）...")
            # 検索ボタンがあるフレームを特定して、JavaScriptで確実に発火
            search_trigger_frame = None
            for f in page.frames:
                if f.locator('input[name="btnSearch"]').count() > 0:
                    search_trigger_frame = f
                    break
            
            if search_trigger_frame:
                print(f"★フレーム '{search_trigger_frame.name}' で検索命令を出します。")
                search_trigger_frame.evaluate("jsSearch();")
            
            print("3. フレームの再構築完了までじっくり待機（20秒）...")
            # ここで「孫フレーム」が生成されるのを待ちます
            time.sleep(20)

            print("4. 構築された全フレームから結果テーブルを捜索...")
            found_data = False
            for f in page.frames:
                # 調査で判明した「#tBody」をターゲットにします
                rows_locator = f.locator("#tBody tr")
                if rows_locator.count() > 0:
                    print(f"★成功！ フレーム '{f.name}' (URL: {f.url}) にて案件データを捕捉しました。")
                    
                    rows = rows_locator.all()
                    scraped_data = []
                    for r in rows:
                        cols = r.locator("td").all_text_contents()
                        # 不要な空白・改行を除去
                        clean_row = [c.strip().replace('\n', ' ').replace('\t', ' ') for c in cols if c.strip()]
                        if clean_row:
                            scraped_data.append(clean_row)
                    
                    if scraped_data:
                        with open('result.csv', 'w', encoding='utf-8-sig', newline='') as f_csv:
                            writer = csv.writer(f_csv)
                            writer.writerows(scraped_data)
                        print(f"--- 取得完了: {len(scraped_data)} 件のデータを result.csv に保存しました ---")
                        found_data = True
                        break
            
            if not found_data:
                print("!! 結果テーブルが見つかりませんでした。デバッグ画像を生成します。")
                page.screenshot(path="debug_final_check.png", full_page=True)

        except Exception as e:
            print(f"エラー発生: {e}")
        finally:
            browser.close()

if __name__ == "__main__":
    main()
