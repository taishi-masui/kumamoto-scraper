from playwright.sync_api import sync_playwright
import time

def main():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(user_agent="Mozilla/5.0...", locale="ja-JP")
        page = context.new_page()

        try:
            print("--- Step 1: 玄関口へアクセス ---")
            page.goto("https://ebid.kumamoto-idc.pref.kumamoto.jp/PPIAccepter/jsp/index.jsp", wait_until="networkidle")
            
            # 時間差で3回スキャン（動的読み込みのチェック）
            for wait_sec in [2, 5, 10]:
                print(f"\n--- スキャン（アクセスから {wait_sec} 秒後） ---")
                time.sleep(wait_sec)
                
                frames = page.frames
                print(f"検知フレーム数: {len(frames)}")
                
                for i, f in enumerate(frames):
                    try:
                        print(f"  [Frame {i}] Name: '{f.name}' / URL: {f.url}")
                        
                        # 1. フレーム内の全ボタン/リンクのテキストを抽出
                        elements = f.evaluate('''() => {
                            const tags = Array.from(document.querySelectorAll('a, button, area, img, input'));
                            return tags.map(t => ({
                                tag: t.tagName,
                                text: t.innerText || t.alt || t.value || '',
                                id: t.id,
                                src: t.src || ''
                            })).filter(e => e.text.length > 0 || e.src.length > 0);
                        }''')
                        
                        print(f"    要素数: {len(elements)}")
                        for el in elements[:10]: # 最初の10個を表示
                            print(f"      - {el['tag']}: '{el['text']}' (ID:{el['id']})")
                            
                    except Exception as e:
                        print(f"    Frame {i} の解析に失敗: {e}")

            # 最終的なHTMLを保存して、人間が目視で確認できるようにする
            with open("structure_debug.html", "w", encoding="utf-8") as f:
                f.write(page.content())
            page.screenshot(path="structure_debug.png", full_page=True)
            print("\n解析完了。HTMLとスクリーンショットを保存しました。")

        except Exception as e:
            print(f"エラー: {e}")
        finally:
            browser.close()

if __name__ == "__main__":
    main()
