from playwright.sync_api import sync_playwright
import time

def main():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        # 追跡しやすくするため、あえて context を分けて検証
        context = browser.new_context(user_agent="Mozilla/5.0...", locale="ja-JP")
        page = context.new_page()

        try:
            print("--- Step 1: ターゲットボタンまでの到達 ---")
            page.goto("http://ebid-portal.kumamoto-idc.pref.kumamoto.jp/", wait_until="networkidle")
            page.frame_locator('frame[name="rtop"]').locator('a[href="koukaisystem.html"]').click()
            
            rbottom = page.frame_locator('frame[name="rbottom"]')
            btn = rbottom.locator('img[src*="botan02.gif"]').first
            btn.wait_for(state="visible")
            print("ボタンを確認しました。検証を開始します。")

            # --- 検証パターン開始 ---
            print("\n--- Pattern A: expect_popup (標準的な待ち受け) ---")
            try:
                with page.expect_popup(timeout=10000) as popup_info:
                    btn.click()
                print("Pattern A 成功: ウィンドウを捕捉しました。")
                test_page = popup_info.value
            except Exception as e:
                print(f"Pattern A 失敗: {e}")

            print("\n--- Pattern B: context.on('page') (イベントリスナー方式) ---")
            # 新しいページが作成されたらリストに追加する仕組み
            pages = []
            context.on("page", lambda p: pages.append(p))
            btn.click() # 再度クリック（あるいはAが失敗していた場合用）
            time.sleep(5)
            if len(pages) > 1: # 元のpage以外に増えているか
                print(f"Pattern B 成功: {len(pages)-1} 個の新しいウィンドウを検知。")
                test_page = pages[-1]
            else:
                print("Pattern B 失敗: 新しいページが検知されませんでした。")

            print("\n--- Pattern C: browser_context.pages (強制リスト取得方式) ---")
            # 現在ブラウザが開いている全タブを強制的にリストアップ
            all_pages = context.pages
            print(f"現在開いている全タブ数: {len(all_pages)}")
            for i, p_in_list in enumerate(all_pages):
                print(f"  Tab[{i}] URL: {p_in_list.url[:50]}...")
            
            # --- 最終検証：生き残ったウィンドウの構造解析 ---
            # ここで ppi_page (URL2) が生きていれば、その中身を徹底調査
            active_pages = [p for p in context.pages if "PPIAccepter" in p.url]
            if active_pages:
                target_page = active_pages[0]
                target_page.wait_for_load_state("networkidle")
                print(f"\n★ 捕捉完了。URL: {target_page.url}")
                
                # ここで「熊本県」などの自治体選択リンクの正体を暴く
                print("自治体選択リンク（ATYPE）の情報を抽出します...")
                elements = target_page.evaluate('''() => {
                    return Array.from(document.querySelectorAll('a, area, img')).map(el => ({
                        tag: el.tagName,
                        text: el.innerText || el.alt,
                        href: el.href,
                        onclick: el.getAttribute('onclick')
                    })).filter(e => e.href || e.onclick);
                }''')
                for el in elements[:15]:
                    print(f"  [{el['tag']}] Text: {el['text']} / OnClick: {el['onclick']}")
            else:
                print("\n!! どのパターンでも本番画面を維持できませんでした。")

        except Exception as e:
            print(f"実行エラー: {e}")
        finally:
            browser.close()

if __name__ == "__main__":
    main()
