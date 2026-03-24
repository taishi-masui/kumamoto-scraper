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
            time.sleep(10)

            print("\n=== [ターゲット要素の徹底解析] ===")
            # 全フレームをループ。特に「frmRIGHT」に注目
            for f in page.frames:
                # 検索という文字を含む要素を抽出
                elements = f.evaluate('''() => {
                    return Array.from(document.querySelectorAll('a, img, input, span, div')).map(el => {
                        return {
                            tag: el.tagName,
                            text: el.innerText.trim() || el.alt || '',
                            onclick: el.getAttribute('onclick') || '',
                            href: el.getAttribute('href') || ''
                        };
                    }).filter(e => e.text.includes('入札・契約情報の検索'));
                }''')

                if elements:
                    print(f"\n[Frame名: {f.name}] にターゲットを発見！")
                    for el in elements:
                        print(f"  - Tag: {el['tag']}")
                        print(f"    Text: {el['text']}")
                        print(f"    OnClick: {el['onclick']}")
                        print(f"    Href: {el['href']}")
                
            # エビデンス保存
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
