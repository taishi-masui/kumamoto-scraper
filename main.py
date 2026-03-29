from playwright.sync_api import sync_playwright
import time

def main():
    with sync_playwright() as p:
        # ブラウザ起動
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        try:
            print("1. ポータルページへアクセス中...")
            page.goto("https://ebid.kumamoto-idc.pref.kumamoto.jp/PPIAccepter/TopServlet", wait_until="networkidle")
            time.sleep(3)

            # 地区ロゴが並んでいるメインフレームを特定
            # このサイトは通常、フレーム名 "Right" などの中にボタンがあります
            target_frame = None
            for f in page.frames:
                if "AccepterServlet" in f.url:
                    target_frame = f
                    break
            
            if not target_frame:
                target_frame = page # フレームが見つからない場合はメインページ

            print("\n2. 画面内のボタン情報を解析中...\n")

            # すべての <img> タグ（ロゴボタン）を取得
            images = target_frame.locator("img.ATYPE").all()
            
            print(f"{'番号':<5} | {'自治体ロゴ(画像名)':<30} | {'実行される命令(onclick)'}")
            print("-" * 80)

            for img in images:
                # ロゴの画像ファイル名を取得 (どこの自治体か判別するため)
                src = img.get_attribute("src") or "不明"
                logo_name = src.split("/")[-1]
                
                # ボタンを押した時に実行されるJavaScriptを取得
                onclick_js = img.get_attribute("onclick") or "なし"
                
                # 番号を抽出 (jsClick(1) なら 1)
                idx_match = re.search(r'jsClick\((\d+)\)', onclick_js)
                idx = idx_match.group(1) if idx_match else "-"

                print(f"{idx:<5} | {logo_name:<30} | {onclick_js}")

            # --- さらに深掘り: jsClick関数の正体を暴く ---
            print("\n3. jsClick関数の定義を確認します...")
            js_definition = target_frame.evaluate("""() => {
                return typeof jsClick !== 'undefined' ? jsClick.toString() : '定義が見つかりません';
            }""")
            print("\n【jsClick関数のプログラム内容】:")
            print(js_definition)

        except Exception as e:
            print(f"解析中にエラーが発生しました: {e}")
        finally:
            browser.close()

import re # reモジュールが必要なため追加
if __name__ == "__main__":
    main()
