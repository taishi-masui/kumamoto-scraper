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
            
            # メニューフレーム特定
            menu_f = next((f for f in page.frames if "PJC001Servlet" in f.url), page)
            menu_f.evaluate("jsLink(1,1);")
            time.sleep(10)

            print("2. 検索実行命令を発行（エラーを無視して突き進みます）...")
            # ページ内の全フレームに対して、jsSearchがあれば実行する（生存確認を挟まない）
            page.evaluate('''() => {
                for (let i = 0; i < window.frames.length; i++) {
                    try {
                        if (typeof window.frames[i].jsSearch === "function") {
                            window.frames[i].jsSearch();
                        }
                    } catch (e) {}
                }
                // 親画面にjsSearchがある場合も考慮
                if (typeof window.jsSearch === "function") window.jsSearch();
            }''')
            
            print("3. フレームの完全な再構築を待ちます（20秒）...")
            time.sleep(20)

            print("4. 構築されたフレーム群から、生きているものだけをスキャン...")
            found_data = False
            # 現在のアクティブな全フレームをチェック
            for f in page.frames:
                try:
                    # Detachedを避けるため、まず要素があるか「静かに」確認
                    # evaluate経由で要素数を数えるのが最も安全
                    row_count = f.evaluate("() => document.querySelectorAll('#tBody tr').length")
                    
                    if row_count > 0:
                        print(f"★成功！ フレーム '{f.name}' に {row_count} 件のデータを捕捉しました。")
                        
                        # データの抜き出し
                        rows = f.locator("#tBody tr").all()
                        scraped_data = []
                        for r in rows:
                            cols = r.locator("td").all_text_contents()
                            clean_row = [c.strip().replace('\\n', ' ').replace('\\t', ' ') for c in cols if c.strip()]
                            if clean_row:
                                scraped_data.append(clean_row)
                        
                        if scraped_data:
                            with open('result.csv', 'w', encoding='utf-8-sig', newline='') as f_csv:
                                writer = csv.writer(f_csv)
                                writer.writerows(scraped_data)
                            print(f"--- result.csv に保存完了 ---")
                            found_data = True
                            break
                except:
                    continue # 死んでいるフレームは無視
            
            if not found_data:
                print("!! 結果テーブルが見つかりませんでした。")
                page.screenshot(path="debug_after_click.png", full_page=True)
                with open("debug_page.html", "w", encoding="utf-8") as file:
                    file.write(page.content())

        except Exception as e:
            print(f"実行中に予期せぬエラー: {e}")
        finally:
            browser.close()

if __name__ == "__main__":
    main()
