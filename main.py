from playwright.sync_api import sync_playwright
import time
import csv
import os

def save_debug(page, name):
    """デバッグ用のスクリーンショットとHTMLを保存する関数"""
    try:
        page.screenshot(path=f"debug_{name}.png", full_page=True)
        with open(f"debug_{name}.html", "w", encoding="utf-8") as f:
            f.write(page.content())
        print(f"--- デバッグ保存完了: {name} ---")
    except Exception as e:
        print(f"デバッグ保存失敗({name}): {e}")

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
            save_debug(page, "01_input_page")

            print("2. 表示件数を100件に切り替え中...")
            for f in page.frames:
                try:
                    # 'ListCount' を探し、値を100にしてchangeイベントを発火
                    target_select = f.locator('select[name="ListCount"]')
                    if target_select.count() > 0:
                        # JavaScriptで確実に値をセットし、イベントを飛ばす
                        f.evaluate('''() => {
                            const sel = document.querySelector('select[name="ListCount"]');
                            sel.value = "100";
                            sel.dispatchEvent(new Event('change', { bubbles: true }));
                        }''')
                        print(f"★フレーム '{f.name}' にて100件設定を実行しました。")
                        break
                except: continue
            
            time.sleep(3)
            save_debug(page, "02_after_selection")

            print("3. 検索実行...")
            # 全フレームに対して jsSearch を実行（エラーは無視）
            page.evaluate('''() => {
                const trigger = (w) => {
                    try { if (typeof w.jsSearch === "function") w.jsSearch(); } catch (e) {}
                    for (let i = 0; i < w.frames.length; i++) trigger(w.frames[i]);
                };
                trigger(window);
            }''')
            
            print("4. 結果の出現を監視中（最大40秒）...")
            scraped_data = []
            start_time = time.time()
            
            while time.time() - start_time < 40:
                for f in page.frames:
                    try:
                        row_count = f.evaluate("() => document.querySelectorAll('#tBody tr').length")
                        if row_count > 0:
                            print(f"★データ捕捉！ {row_count} 件を確認。")
                            rows = f.locator("#tBody tr").all()
                            for r in rows:
                                cols = r.locator("td").all_text_contents()
                                clean_row = [c.strip().replace('\\n', ' ').replace('\\t', ' ') for c in cols if c.strip()]
                                if clean_row: scraped_data.append(clean_row)
                            
                            if scraped_data:
                                with open('result.csv', 'w', encoding='utf-8-sig', newline='') as f_csv:
                                    writer = csv.writer(f_csv)
                                    writer.writerows(scraped_data)
                                print(f"--- result.csv に {len(scraped_data)} 件保存しました ---")
                                save_debug(page, "03_result_success")
                                break
                    except: continue
                if scraped_data: break
                time.sleep(3)

            if not scraped_data:
                print("!! 最終的にデータが見つかりませんでした。")
                save_debug(page, "04_result_not_found")

        except Exception as e:
            print(f"実行中に重大なエラー: {e}")
            save_debug(page, "99_fatal_error")
        finally:
            browser.close()

if __name__ == "__main__":
    main()
