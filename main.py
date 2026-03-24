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
            
            print("2. ターゲット画像(jsClick(1))を直接クリック...")
            # 教えていただいた構造を元に、正確にimgタグを狙います
            target_img = page.locator('img[onclick="jsClick(1);"]')
            target_img.wait_for(state="visible")
            target_img.click()
            
            print("3. 遷移後の安定を待ちます（15秒）...")
            time.sleep(15)

            print(f"\n=== [遷移後スキャン] 現在のURL: {page.url} ===")
            
            # 全てのフレーム（入れ子構造）を再起的にチェック
            all_frames = page.frames
            print(f"検知されたフレーム数: {len(all_frames)}")
            
            for i, f in enumerate(all_frames):
                try:
                    # 各フレームのURLと、中身にある「文字」と「ボタン」を抽出
                    info = f.evaluate('''() => {
                        return {
                            name: window.name,
                            url: window.location.href,
                            text: document.body.innerText.substring(0, 200).replace(/\\n/g, ' '),
                            inputs: Array.from(document.querySelectorAll('input, a, button')).map(el => ({
                                tag: el.tagName,
                                val: el.value || el.innerText || '',
                                name: el.name || ''
                            }))
                        }
                    }''')
                    print(f"\n[Frame {i}] Name: '{info['name']}' | URL: {info['url']}")
                    print(f"  内容冒頭: {info['text']}...")
                    if info['inputs']:
                        print(f"  見つかった要素(一部): {[f'{item['tag']}({item['val'] or item['name']})' for item in info['inputs'][:10]]}")
                except Exception as e:
                    print(f"  [Frame {i}] 解析不可: {e}")

            # 最終的な証拠保存
            page.screenshot(path="debug_after_click.png", full_page=True)
            with open("debug_after_click.html", "w", encoding="utf-8") as f:
                f.write(page.content())
            print("\n調査完了。HTMLと画像を保存しました。")

        except Exception as e:
            print(f"実行エラー: {e}")
        finally:
            browser.close()

if __name__ == "__main__":
    main()
