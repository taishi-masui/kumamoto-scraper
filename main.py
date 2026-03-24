from playwright.sync_api import sync_playwright
import time

def dump_frames(page, label):
    print(f"\n=== {label} : フレーム構造解析 ===")
    frames = page.frames
    print(f"検知されたフレーム数: {len(frames)}")
    for i, f in enumerate(frames):
        try:
            name = f.name
            url = f.url
            # フレーム内の全リンク（aタグ）のhrefを抽出
            links = f.evaluate('() => Array.from(document.querySelectorAll("a")).map(a => a.href)')
            # フレーム内の全ボタン/入力要素のnameを抽出
            inputs = f.evaluate('() => Array.from(document.querySelectorAll("input, img")).map(el => el.name || el.src)')
            
            print(f"  Frame[{i}] Name: '{name}'")
            print(f"    URL: {url}")
            if links: print(f"    Links(first 5): {links[:5]}")
            if inputs: print(f"    Elements(first 5): {inputs[:5]}")
        except Exception as e:
            print(f"  Frame[{i}] 解析失敗: {e}")
    print("=" * 40)

def main():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(user_agent="Mozilla/5.0...", locale="ja-JP")
        page = context.new_page()

        try:
            # 1. URL1 解析
            print("1. URL1 (ポータル) アクセス直後の解析")
            page.goto("http://ebid-portal.kumamoto-idc.pref.kumamoto.jp/", wait_until="networkidle")
            dump_frames(page, "URL1 初期状態")

            # 2. メニュークリック後の解析
            print("\n2. 'koukaisystem.html' へのリンクをクリック...")
            rtop = page.frame_locator('frame[name="rtop"]')
            target = rtop.locator('a[href="koukaisystem.html"]')
            if target.count() > 0:
                target.click()
                time.sleep(5)
                dump_frames(page, "URL1 メニュークリック後")
            else:
                print("!! rtop内に koukaisystem.html が見つかりません")

            # 3. ポップアップ発生の解析
            print("\n3. ポップアップを試行...")
            rbottom = page.frame_locator('frame[name="rbottom"]')
            popup_trigger = rbottom.locator('a[href*="PPIAccepter"]').first
            
            if popup_trigger.count() > 0:
                with page.expect_popup() as popup_info:
                    popup_trigger.click()
                ppi_page = popup_info.value
                ppi_page.wait_for_load_state("networkidle")
                
                # ここが本番システム(URL2/URL3)の真の姿
                dump_frames(ppi_page, "URL2 ポップアップ直後")
                
                print("\n4. 熊本県（ATYPE）をクリックした後の解析...")
                ppi_page.locator(".ATYPE").first.click()
                time.sleep(5)
                dump_frames(ppi_page, "URL3 自治体選択後")
            else:
                print("!! rbottom内にポップアップ用リンクが見つかりません")

        except Exception as e:
            print(f"\n!!! 実行エラー: {e}")
        finally:
            browser.close()

if __name__ == "__main__":
    main()
