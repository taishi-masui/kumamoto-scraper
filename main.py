from playwright.sync_api import sync_playwright
import time

def main():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(user_agent="Mozilla/5.0...", locale="ja-JP")
        page = context.new_page()

        try:
            print("1. 検索条件画面へ到達...")
            page.goto("https://ebid.kumamoto-idc.pref.kumamoto.jp/PPIAccepter/AccepterServlet?kikan_no=0100", wait_until="networkidle")
            time.sleep(5)
            # メニューから検索画面呼び出し
            menu_f = next((f for f in page.frames if "PJC001Servlet" in f.url), page)
            menu_f.evaluate("jsLink(1,1);")
            time.sleep(10)

            print("2. 検索ボタン(btnSearch)を特定してクリック...")
            target_f = None
            for f in page.frames:
                if f.locator('input[name="btnSearch"]').count() > 0:
                    target_f = f
                    break
            
            if target_f:
                print(f"ターゲットフレーム '{target_f.name}' で検索を実行します。")
                target_f.locator('input[name="btnSearch"]').click()
            else:
                print("!! ボタンが見つかりません。")

            print("3. 結果表示を待ちます（15秒）...")
            time.sleep(15)

            print(f"\n=== [検索結果画面スキャン] 現在のURL: {page.url} ===")
            
            # 全フレームを総当たりで調査
            frames = page.frames
            print(f"検知されたフレーム数: {len(frames)}")

            for i, f in enumerate(frames):
                try:
                    # フレーム内のテキスト、テーブル構造、ボタンを調査
                    info = f.evaluate('''() => {
                        return {
                            name: window.name,
                            url: window.location.href,
                            text: document.body.innerText.substring(0, 200).replace(/\\n/g, ' '),
                            hasTable: document.querySelectorAll('table').length,
                            hasTbody: !!document.querySelector('#tBody'),
                            buttons: Array.from(document.querySelectorAll('input, a')).map(el => el.value || el.innerText).filter(t => t)
                        }
                    }''')
                    
                    print(f"\n[Frame {i}] Name: '{info['name']}' | URL: {info['url']}")
                    print(f"  内容冒頭: {info['text']}...")
                    print(f"  テーブル数: {info['hasTable']} | #tBodyの有無: {info['hasTbody']}")
                    if info['buttons']:
                        print(f"  ボタン/リンク: {info['buttons'][:10]}")

                except Exception as e:
                    print(f"  [Frame {i}] 解析不可: {e}")

            # 証拠保存
            page.screenshot(path="debug_after_click.png", full_page=True)
            with open("debug_page.html", "w", encoding="utf-8") as file:
                file.write(page.content())
            print("\n調査完了。")

        except Exception as e:
            print("実行エラー: " + str(e))
        finally:
            browser.close()

if __name__ == "__main__":
    main()
