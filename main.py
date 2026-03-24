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

            print("2. 検索ボタン(btnSearch)をクリック...")
            # ターゲットフレームを特定
            target_f = None
            for f in page.frames:
                if f.locator('input[name="btnSearch"]').count() > 0:
                    target_f = f
                    break
            
            if target_f:
                # クリック実行（ここで古いフレームが消え始める）
                target_f.locator('input[name="btnSearch"]').click()
                print("クリック完了。画面の再構築を待ちます...")
            
            # --- ここで「待ち」に徹する ---
            print("3. 新しいフレームが安定するまで15秒待機...")
            time.sleep(15)

            print(f"\n=== [最終調査] 現在のURL: {page.url} ===")
            
            # 現在「生きている」フレームだけを対象にスキャン
            active_frames = page.frames
            print(f"検知されたアクティブなフレーム数: {len(active_frames)}")

            for i, f in enumerate(active_frames):
                # detachedを避けるため、各フレームごとにtry-exceptを入れる
                try:
                    # すでに破棄されたフレームはスキップ
                    if f.is_detached(): continue
                    
                    # フレーム内の情報を抽出
                    res = f.evaluate('''() => {
                        return {
                            name: window.name,
                            url: window.location.href,
                            text: document.body.innerText.substring(0, 200).replace(/\\n/g, ' '),
                            tableCount: document.querySelectorAll('table').length,
                            tBodyExists: !!document.querySelector('#tBody'),
                            links: Array.from(document.querySelectorAll('a')).map(a => a.innerText.trim()).filter(t => t)
                        }
                    }''')
                    
                    print(f"\n[Frame {i}] Name: '{res['name']}'")
                    print(f"  URL: {res['url']}")
                    print(f"  内容: {res['text']}...")
                    print(f"  テーブル数: {res['tableCount']} | #tBody: {res['tBodyExists']}")
                    if res['links']: print(f"  リンク: {res['links'][:10]}")

                except Exception:
                    # 解析中に消えたフレームは無視して次へ
                    continue

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
