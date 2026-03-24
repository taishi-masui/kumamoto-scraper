from playwright.sync_api import sync_playwright
import time

def main():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(user_agent="Mozilla/5.0...", locale="ja-JP")
        page = context.new_page()

        try:
            print("1. 熊本県セッションの開始（AccepterServletへ直行）...")
            # 前回のログで判明した「成功URL」を直接叩いてセッションが維持されるか確認
            page.goto("https://ebid-portal.kumamoto-idc.pref.kumamoto.jp/", wait_until="networkidle") # Cookie用
            page.goto("https://ebid.kumamoto-idc.pref.kumamoto.jp/PPIAccepter/AccepterServlet?Error=&Message=&kikan_no=0100", wait_until="networkidle")
            
            print("2. 安定を待ちます（10秒）...")
            time.sleep(10)

            print(f"\n=== [Accepter解析] 現在のURL: {page.url} ===")
            
            # このページにある「全てのテキスト」と「クリック可能な要素」を抽出
            data = page.evaluate('''() => {
                return {
                    bodyText: document.body.innerText,
                    links: Array.from(document.querySelectorAll('a, area, img, input')).map(el => ({
                        tag: el.tagName,
                        text: el.innerText || el.alt || el.value || '',
                        onclick: el.getAttribute('onclick') || '',
                        src: el.src || ''
                    })).filter(e => e.text || e.onclick || e.src)
                }
            }''')

            print(f"テキスト冒頭: {data['bodyText'][:300].replace('\\n', ' ')}")
            print("\n--- 検出された要素（上位30件） ---")
            for i, el in enumerate(data['links'][:30]):
                print(f"[{i}] {el['tag']} | Text: {el['text']} | OnClick: {el['onclick']}")

            # 確実な保存名でActionsと合わせる
            page.screenshot(path="debug_after_click.png", full_page=True)
            with open("debug_page.html", "w", encoding="utf-8") as f:
                f.write(page.content())
            print("\n調査完了。")

        except Exception as e:
            print(f"実行エラー: {e}")
        finally:
            browser.close()

if __name__ == "__main__":
    main()
