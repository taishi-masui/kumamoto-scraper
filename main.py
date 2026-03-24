from playwright.sync_api import sync_playwright
import time

def main():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(user_agent="Mozilla/5.0...", locale="ja-JP")
        page = context.new_page()

        try:
            print("--- Step 1: 準備 ---")
            page.goto("http://ebid-portal.kumamoto-idc.pref.kumamoto.jp/", wait_until="networkidle")
            page.frame_locator('frame[name="rtop"]').locator('a[href="koukaisystem.html"]').click()
            rbottom = page.frame_locator('frame[name="rbottom"]')
            btn_container = rbottom.locator('a[href*="PPIAccepter"]').first
            btn_container.wait_for(state="visible")

            # --- 調査A: リンク先のURLを直接ぶっこ抜く ---
            direct_url = btn_container.get_attribute("href")
            print(f"\n[調査A] 取得された直接URL: {direct_url}")

            # --- 調査B: window.close() を無効化してクリック ---
            print("\n[調査B] window.closeを無効化して生存テスト開始...")
            page.evaluate("window.close = function() { console.log('close prevented'); };")
            
            with page.expect_popup(timeout=10000) as popup_info:
                btn_container.click()
            
            ppi_page = popup_info.value
            # ここで即座にURLとタイトルを記録
            print(f"捕捉直後の情報: URL={ppi_page.url} Title={ppi_page.title()}")
            
            # --- 調査C: 生存確認と構造の吸い出し ---
            print("\n[調査C] 内部構造の走査...")
            time.sleep(5) # 5秒耐えられるか？
            
            if ppi_page.is_closed():
                print("!! 5秒待機中に閉じられました。直接アクセス案(A)に切り替えます。")
                # 案Aの実行
                new_page = context.new_page()
                new_page.goto(direct_url, wait_until="networkidle")
                print(f"直接アクセス成功。現在のURL: {new_page.url}")
                target_page = new_page
            else:
                print("成功！ウィンドウは生存しています。")
                target_page = ppi_page

            # 生き残ったページで「自治体選択」のパーツを徹底調査
            print("\n--- 最終ターゲット：自治体選択要素の抽出 ---")
            elements = target_page.evaluate('''() => {
                return Array.from(document.querySelectorAll('a, img, area')).map(el => ({
                    tag: el.tagName,
                    alt: el.alt || '',
                    src: el.src || '',
                    onclick: el.getAttribute('onclick') || ''
                })).filter(e => e.onclick || e.alt.includes('熊本'));
            }''')
            
            for i, el in enumerate(elements):
                print(f"  Element[{i}]: Tag={el['tag']}, Alt='{el['alt']}', OnClick='{el['onclick']}'")

        except Exception as e:
            print(f"\nエラー発生: {e}")
            # どんな状態でもスクリーンショットを撮る
            page.screenshot(path="debug_final_parent.png")
            if 'ppi_page' in locals() and not ppi_page.is_closed():
                ppi_page.screenshot(path="debug_final_child.png")
        finally:
            browser.close()

if __name__ == "__main__":
    main()
