from playwright.sync_api import sync_playwright
import time

def main():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(user_agent="Mozilla/5.0...", locale="ja-JP")
        page = context.new_page()

        try:
            print("1. 熊本県セッションの開始（AccepterServletへアクセス）...")
            # ポータルを経由せず、前回の成功URLを直接呼び出し
            page.goto("https://ebid.kumamoto-idc.pref.kumamoto.jp/PPIAccepter/AccepterServlet?Error=&Message=&kikan_no=0100", wait_until="networkidle")
            
            print("2. 安定を待ちます（10秒）...")
            time.sleep(10)

            print("=== [Accepter解析] 現在のURL: " + page.url + " ===")
            
            # ページ内のテキストと要素を抽出（バックスラッシュを使わない安全な方法）
            data = page.evaluate('''() => {
                return {
                    bodyText: document.body.innerText,
                    elements: Array.from(document.querySelectorAll('a, area, img, input, frame, iframe')).map(el => {
                        return {
                            tag: el.tagName,
                            text: el.innerText || el.alt || el.value || '',
                            name: el.name || '',
                            onclick: el.getAttribute('onclick') || '',
                            src: el.src || ''
                        };
                    })
                };
            }''')

            # テキストの出力（エラー回避のため単純なスライスのみ）
            full_text = data['bodyText']
            print("\n--- ページ内の全テキスト（冒頭） ---")
            print(full_text[:500])
            
            print("\n--- 検出された要素（全件表示） ---")
            for i, el in enumerate(data['elements']):
                print(f"[{i}] {el['tag']} | Text: {el['text']} | Name: {el['name']} | OnClick: {el['onclick']}")

            # 確実な保存名でActionsと合わせる（名前を固定）
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
