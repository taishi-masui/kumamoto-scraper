from playwright.sync_api import sync_playwright
import time

def main():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(user_agent="Mozilla/5.0...", locale="ja-JP")
        page = context.new_page()

        try:
            print("--- Step 1: 直接URLで本番システムへ ---")
            # 判明したURLへ直接ジャンプ
            page.goto("https://ebid.kumamoto-idc.pref.kumamoto.jp/PPIAccepter/jsp/index.jsp", wait_until="networkidle")
            print(f"現在のURL: {page.url}")

            print("\n--- Step 2: 自治体選択（熊本県）の複数パターン試行 ---")
            
            # 候補となるセレクタをリスト化
            candidates = [
                ("CSSクラス", page.locator(".ATYPE").first),
                ("テキスト", page.get_by_text("熊本県").first),
                ("画像Alt", page.locator('img[alt*="熊本県"]').first),
                ("リンクURL", page.locator('a[href*="PrefKumamoto"]').first)
            ]

            success = False
            for name, locator in candidates:
                try:
                    if locator.count() > 0:
                        print(f"  [試行] {name} をクリックします...")
                        locator.click()
                        success = True
                        break
                except:
                    continue

            if not success:
                print("!! すべてのクリック試行に失敗しました。")
                # 最終手段：画面中央付近をクリック
                page.mouse.click(400, 300) 

            # 遷移待ち
            print("\n--- Step 3: メニュー画面の構造解析 ---")
            time.sleep(5)
            
            # ここで「入札・契約情報の検索」があるか確認
            print(f"遷移後のURL: {page.url}")
            
            # フレーム構造を再チェック
            frames = page.frames
            print(f"検知フレーム数: {len(frames)}")
            for i, f in enumerate(frames):
                print(f"  Frame[{i}] Name: '{f.name}' URL: {f.url}")
                # フレーム内のテキストを一部出力して中身を確認
                content = f.evaluate("() => document.body.innerText.substring(0, 50)")
                print(f"    内容(冒頭): {content}...")

        except Exception as e:
            print(f"\nエラー詳細: {e}")
            page.screenshot(path="debug_menu_check.png")
            with open("debug_menu_check.html", "w", encoding="utf-8") as f:
                f.write(page.content())
        finally:
            browser.close()

if __name__ == "__main__":
    main()
