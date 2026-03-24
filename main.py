from playwright.sync_api import sync_playwright
import time

def main():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(user_agent="Mozilla/5.0...", locale="ja-JP")
        page = context.new_page()

        try:
            print("1. 検索条件画面（btnSearchが存在する状態）まで進みます...")
            page.goto("https://ebid.kumamoto-idc.pref.kumamoto.jp/PPIAccepter/AccepterServlet?kikan_no=0100", wait_until="networkidle")
            time.sleep(5)
            menu_f = next((f for f in page.frames if "PJC001Servlet" in f.url), page)
            menu_f.evaluate("jsLink(1,1);")
            time.sleep(10) # 構築待ち

            print("\n=== [操作前の全フレーム構成] ===")
            for i, f in enumerate(page.frames):
                print(f"Frame[{i}] Name: '{f.name}' | URL: {f.url}")

            print("\n2. 検索実行（Detachedを覚悟して命令を投げます）...")
            for f in page.frames:
                try:
                    btn = f.locator('input[name="btnSearch"]')
                    if btn.count() > 0:
                        # クリック後のエラーを避けるため、JavaScriptで非同期に発火
                        print(f"★Frame '{f.name}' で検索実行命令を発行")
                        f.evaluate('() => document.querySelector("input[name=\\"btnSearch\\"]").click()')
                        break
                except: continue

            print("3. 画面の再構築をじっくり待ちます（20秒）...")
            time.sleep(20)

            print(f"\n=== [操作後の新世界スキャン] 現在のURL: {page.url} ===")
            # この時点で「生き残っている」あるいは「新設された」フレームだけを見る
            new_frames = page.frames
            print(f"現存フレーム数: {len(new_frames)}")

            for i, f in enumerate(new_frames):
                try:
                    # 解析の瞬間に消えないよう、URLとテキストだけを慎重に取得
                    url = f.url
                    text_preview = f.evaluate("() => document.body.innerText.substring(0, 100).replace(/\\n/g, ' ')")
                    # テーブル（検索結果リスト）があるか確認
                    has_result = f.evaluate("() => !!document.querySelector('#tBody') || document.querySelectorAll('table').length > 5")
                    
                    print(f"\n[Frame {i}] Name: '{f.name}'")
                    print(f"  URL: {url}")
                    print(f"  内容: {text_preview}...")
                    if has_result:
                        print("  ★ここに検索結果（テーブル）がある可能性が高いです！")
                except:
                    print(f"[Frame {i}] 解析不可（すでに消滅または遷移中）")

            # 最終的な画面を保存
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
