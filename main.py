from playwright.sync_api import sync_playwright
import time

def main():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
            locale="ja-JP"
        )
        page = context.new_page()

        try:
            print("1. 実績のあるURLで本番画面へ直接アクセス...")
            # セッション確立
            page.goto("https://ebid.kumamoto-idc.pref.kumamoto.jp/PPIAccepter/MainServlet?Error=&Message=", wait_until="networkidle")
            # 本番画面（ロゴ並び）へ
            page.goto("https://ebid.kumamoto-idc.pref.kumamoto.jp/PPIAccepter/TopServlet", wait_until="networkidle")
            
            print("2. 画面が安定するまで待機（5秒）...")
            time.sleep(5)

            print("\n=== [調査開始] 自治体選択画面の全要素スキャン ===")
            
            # ページ全体のフレーム構成を再確認
            print(f"現在のURL: {page.url}")
            print(f"検知フレーム数: {len(page.frames)}")

            # 3. 熊本県を選択するための「標的」を特定する
            # aタグ, imgタグ, areaタグ(マップ)をすべて洗い出す
            elements = page.evaluate('''() => {
                const results = [];
                // リンク、画像、クリッカブルマップのエリアを網羅
                const selectors = 'a, img, area';
                document.querySelectorAll(selectors).forEach((el, index) => {
                    results.push({
                        index: index,
                        tag: el.tagName,
                        text: el.innerText || '',
                        alt: el.alt || '',
                        href: el.href || '',
                        onclick: el.getAttribute('onclick') || '',
                        id: el.id || '',
                        className: el.className || '',
                        src: el.src || ''
                    });
                });
                return results;
            }''')

            print(f"検出された全要素数: {len(elements)}")
            print("-" * 50)
            
            # 「熊本」というキーワードが含まれる要素を最優先で出力
            found_kumamoto = False
            for el in elements:
                if "熊本" in el['text'] or "熊本" in el['alt'] or "Kumamoto" in el['onclick'] or "Kumamoto" in el['href']:
                    print(f"【標的候補】発見:")
                    print(f"  Tag: {el['tag']}")
                    print(f"  Text: {el['text']}")
                    print(f"  Alt: {el['alt']}")
                    print(f"  OnClick: {el['onclick']}")
                    print(f"  Href: {el['href']}")
                    print(f"  Selector(推測): {el['tag']}[alt='{el['alt']}'] など")
                    print("-" * 30)
                    found_kumamoto = True

            if not found_kumamoto:
                print("!! '熊本'を含む要素が直接見つかりませんでした。全要素の冒頭20件を表示します:")
                for el in elements[:20]:
                    print(f"  {el['tag']} | Text: {el['text']} | Alt: {el['alt']} | OnClick: {el['onclick']}")

            # 4. 念のため現在の全HTML構造をダンプ（後で解析するため）
            with open("top_servlet_structure.html", "w", encoding="utf-8") as f:
                f.write(page.content())
            page.screenshot(path="top_servlet_check.png", full_page=True)
            print("\n調査完了。HTMLと画像を保存しました。")

        except Exception as e:
            print(f"調査エラー: {e}")
        finally:
            browser.close()

if __name__ == "__main__":
    main()
