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
            time.sleep(5)

            print("2. jsLink(1,1) を実行し、画面遷移を開始...")
            # 安定していた frmTOP で実行
            target_frame = page.frame(name="frmTOP")
            if target_frame:
                target_frame.evaluate("jsLink(1,1);")
            else:
                page.evaluate("jsLink(1,1);")

            # フレームが壊れて作り直されるのをじっくり待つ
            print("3. 画面の再構築を待ちます（15秒）...")
            time.sleep(15) 

            print(f"\n=== [遷移完了後の全フレーム調査] 現在のURL: {page.url} ===")
            
            # 再構築された後の全フレームをリストアップ
            current_frames = page.frames
            print(f"検知された新フレーム数: {len(current_frames)}")

            for i, f in enumerate(current_frames):
                try:
                    # フレームが生きているか確認しながら情報を抜く
                    f_name = f.name
                    f_url = f.url
                    
                    # このフレームの中に「btnSearch」や「検索」があるか徹底調査
                    elements = f.evaluate('''() => {
                        return Array.from(document.querySelectorAll('input, a, button')).map(el => ({
                            tag: el.tagName,
                            text: el.innerText || el.value || el.alt || '',
                            name: el.name || '',
                            type: el.type || ''
                        })).filter(e => e.text.includes('検索') || e.name.includes('Search'));
                    }''')

                    print(f"\n[Frame {i}] Name: '{f_name}' | URL: {f_url}")
                    if elements:
                        for idx, el in enumerate(elements):
                            print(f"  ★発見 [{idx}] {el['tag']}({el['type']}) | Text: '{el['text']}' | Name: '{el['name']}'")
                    else:
                        print("  (検索ボタンに該当する要素は見つかりませんでした)")

                except Exception as e:
                    print(f"  [Frame {i}] 解析エラー（遷移中の可能性）: {e}")

            # 最終的な画面を保存
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
