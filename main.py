from playwright.sync_api import sync_playwright
import time

def main():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(user_agent="Mozilla/5.0...", locale="ja-JP")
        page = context.new_page()

        try:
            print("1. 自治体選択画面へアクセス...")
            page.goto("https://ebid.kumamoto-idc.pref.kumamoto.jp/PPIAccepter/MainServlet?Error=&Message=", wait_until="networkidle")
            page.goto("https://ebid.kumamoto-idc.pref.kumamoto.jp/PPIAccepter/TopServlet", wait_until="networkidle")
            
            print("2. ターゲット画像を正確にクリック...")
            # 教えていただいた <td><img onclick="jsClick(1);"> の構造を狙い撃ち
            target = page.locator('img[onclick*="jsClick(1)"]')
            target.wait_for(state="visible")
            target.click()
            
            print("3. 遷移後の安定を待ちます（15秒）...")
            time.sleep(15)

            print(f"\n=== [遷移後スキャン] 現在のURL: {page.url} ===")
            
            # 全てのフレームをループで調査
            frames = page.frames
            print(f"検知されたフレーム数: {len(frames)}")
            
            for i, f in enumerate(frames):
                try:
                    # eval内のクォーテーション競合を避けるため、単純な文字列として取得
                    f_name = f.name
                    f_url = f.url
                    # フレーム内のテキスト情報を全て取得
                    f_text = f.evaluate("() => document.body.innerText")
                    # フレーム内の全リンク(aタグ)のテキストを取得
                    f_links = f.evaluate("() => Array.from(document.querySelectorAll('a')).map(a => a.innerText.trim())")
                    
                    print(f"\n[Frame {i}] Name: '{f_name}'")
                    print(f"  URL: {f_url}")
                    print(f"  テキスト(冒頭150文字): {f_text[:150].replace(chr(10), ' ')}...")
                    if f_links:
                        print(f"  見つかったリンク: {f_links}")
                        
                except Exception as e:
                    print(f"  [Frame {i}] 解析不可: {e}")

            # 証拠保存
            page.screenshot(path="debug_after_click.png", full_page=True)
            with open("debug_after_click.html", "w", encoding="utf-8") as f:
                f.write(page.content())
            print("\n調査完了。")

        except Exception as e:
            print(f"実行エラー: {e}")
        finally:
            browser.close()

if __name__ == "__main__":
    main()
