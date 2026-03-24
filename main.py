from playwright.sync_api import sync_playwright
import time
import csv

def main():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(user_agent="Mozilla/5.0...", locale="ja-JP")
        page = context.new_page()

        try:
            print("1. ターゲット画面へアクセス...")
            page.goto("https://ebid.kumamoto-idc.pref.kumamoto.jp/PPIAccepter/AccepterServlet?kikan_no=0100", wait_until="networkidle")
            time.sleep(5)

            print("2. 検索条件画面の呼び出し (jsLink(1,1))...")
            # メニューがあるフレームを特定して実行
            menu_frame = next((f for f in page.frames if "PJC001Servlet" in f.url), page)
            menu_frame.evaluate("jsLink(1,1);")

            print("3. 検索画面（フレーム群）の読み込みを待機...")
            # フレームが多重に読み込まれるため、少し長めに待ちます
            time.sleep(10)

            print("4. 全フレームから検索ボタン(btnSearch)を探してクリック...")
            search_clicked = False
            for f in page.frames:
                try:
                    btn = f.locator('input[name="btnSearch"]')
                    if btn.count() > 0:
                        print(f"★フレーム '{f.name}' 内にボタンを発見。クリックします。")
                        btn.click()
                        search_clicked = True
                        break
                except:
                    continue
            
            if not search_clicked:
                print("!! ボタンが見つかりませんでした。JSで直接実行を試みます。")
                page.evaluate("for(let f of window.frames) { if(f.jsSearch) f.jsSearch(); }")

            print("5. 検索結果の表示待ち...")
            time.sleep(8)

            # 結果は通常 frmRIGHT > frmBOTTOM のような構造に出るため全スキャン
            print("6. データ抽出開始...")
            for f in page.frames:
                rows = f.locator("#tBody tr").all()
                if rows:
                    print(f"★フレーム '{f.name}' で {len(rows)} 件のデータを捕捉！")
                    data = [r.locator("td").all_text_contents() for r in rows]
                    
                    with open('result.csv', 'w', encoding='utf-8-sig', newline='') as csvfile:
                        writer = csv.writer(csvfile)
                        for row in data:
                            # 空白や改行を掃除
                            clean_row = [c.strip().replace('\n', ' ') for c in row]
                            writer.writerow(clean_row)
                    print("CSVへの保存が完了しました。")
                    break

        except Exception as e:
            print(f"エラー発生: {e}")
            page.screenshot(path="debug_error.png")
        finally:
            browser.close()

if __name__ == "__main__":
    main()
