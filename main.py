from playwright.sync_api import sync_playwright
import time

def main():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(user_agent="Mozilla/5.0...", locale="ja-JP")
        page = context.new_page()

        try:
            print("--- Step 1: ポータルから正規ルートで進入 ---")
            page.goto("http://ebid-portal.kumamoto-idc.pref.kumamoto.jp/", wait_until="networkidle")
            
            # メニュークリック
            rtop = page.frame_locator('frame[name="rtop"]')
            rtop.locator('a[href="koukaisystem.html"]').click()
            
            # 画像ボタン待機
            rbottom = page.frame_locator('frame[name="rbottom"]')
            btn = rbottom.locator('img[src*="botan02.gif"]').first
            btn.wait_for(state="visible")

            # --- 重要：親が閉じるのを防ぎつつ、ポップアップを待つ ---
            print("--- Step 2: ポップアップ発生の監視 ---")
            # 親ウィンドウの自己終了命令を無効化
            page.evaluate("window.close = function() { console.log('Prevented window.close()'); };")

            with page.expect_popup() as popup_info:
                btn.click()
            
            ppi_page = popup_info.value
            # ロードが完了するまでじっくり待つ（ここで焦ると Target closed になる）
            print("ポップアップを検知。安定するまで5秒待機します...")
            time.sleep(5) 
            ppi_page.wait_for_load_state("networkidle")

            print(f"\n--- Step 3: 捕捉したページの真の構造 ---")
            print(f"URL: {ppi_page.url}")
            
            # フレーム構造の走査
            frames = ppi_page.frames
            print(f"検知フレーム数: {len(frames)}")
            for i, f in enumerate(frames):
                try:
                    # フレーム内のテキスト、リンク、ボタンを全て書き出す
                    data = f.evaluate('''() => {
                        return {
                            text: document.body.innerText.substring(0, 100),
                            links: Array.from(document.querySelectorAll('a, area')).map(a => a.innerText || a.alt || 'no-text'),
                            images: Array.from(document.querySelectorAll('img')).map(img => img.alt || img.src)
                        }
                    }''')
                    print(f"  [Frame {i}] Name: '{f.name}'")
                    print(f"    冒頭テキスト: {data['text']}...")
                    print(f"    見つかったリンク/画像: {data['links'][:5]} / {data['images'][:5]}")
                except Exception as fe:
                    print(f"  [Frame {i}] 解析エラー: {fe}")

            # 証拠保存
            ppi_page.screenshot(path="popup_captured.png", full_page=True)
            with open("popup_captured.html", "w", encoding="utf-8") as f:
                f.write(ppi_page.content())

        except Exception as e:
            print(f"\n実行エラー: {e}")
        finally:
            browser.close()

if __name__ == "__main__":
    main()
