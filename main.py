from playwright.sync_api import sync_playwright
import time

def main():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(user_agent="Mozilla/5.0...", locale="ja-JP")
        page = context.new_page()

        try:
            print("1. ターゲット画面(MainServlet)へ到達...")
            page.goto("https://ebid.kumamoto-idc.pref.kumamoto.jp/PPIAccepter/AccepterServlet?kikan_no=0100", wait_until="networkidle")
            time.sleep(10) # 完全にフレームが読み込まれるのを待つ

            # 調査対象のフレームリスト
            target_frames = ["frmLEFT", "frmRIGHT"]

            for frame_name in target_frames:
                print(f"\n--- フレーム [{frame_name}] の内部調査 ---")
                frame = page.frame_locator(f'frame[name="{frame_name}"]')
                
                # フレーム内の全要素（a, img, area, input）の属性を抽出
                # バックスラッシュを避けた安全な抽出ロジック
                elements_data = frame.evaluate('''() => {
                    const tags = Array.from(document.querySelectorAll('a, img, area, input, span'));
                    return tags.map(el => {
                        return {
                            tag: el.tagName,
                            text: el.innerText || el.alt || el.value || '',
                            onclick: el.getAttribute('onclick') || '',
                            href: el.getAttribute('href') || '',
                            id: el.id || '',
                            className: el.className || ''
                        };
                    });
                }''')

                print(f"検出要素数: {len(elements_data)}")
                
                # 「検索」という文字を含む要素を特定
                found_count = 0
                for el in elements_data:
                    if "検索" in el['text'] or "PBI001" in el['href'] or "js" in el['onclick']:
                        print(f"  [発見] Tag: {el['tag']} | Text: {el['text']}")
                        print(f"         OnClick: {el['onclick']}")
                        print(f"         Href: {el['href']}")
                        print(f"         ID: {el['id']} | Class: {el['className']}")
                        print("  " + "-"*30)
                        found_count += 1
                
                if found_count == 0:
                    print("  !! このフレーム内には「検索」に関連する直接の要素は見つかりませんでした。")

            # 証拠として現在のHTMLソースとスクリーンショットを保存
            # Actionsの設定に合わせてファイル名を固定
            page.screenshot(path="debug_after_click.png", full_page=True)
            with open("debug_page.html", "w", encoding="utf-8") as f:
                f.write(page.content())
            print("\n調査完了。")

        except Exception as e:
            print("実行エラー: " + str(e))
        finally:
            browser.close()

if __name__ == "__main__":
    main()
