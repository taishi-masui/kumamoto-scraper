from playwright.sync_api import sync_playwright

def main():
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()

        page.goto("https://ebid.kumamoto-idc.pref.kumamoto.jp/PPIAccepter/MainServlet?Error=&Message=")

        # ★ フレームが出るまで待つ
        page.wait_for_selector("frame")

        # ★ フレーム一覧確認（デバッグ）
        print("=== フレーム一覧 ===")
        for f in page.frames:
            print(f.url)

        # ★ PJC001を探す（確実に）
        menu_frame = None
        for f in page.frames:
            if "PJC001Servlet" in f.url:
                menu_frame = f

        if menu_frame is None:
            raise Exception("PJC001フレームが見つからない")

        # ★ クリック
        menu_frame.click("text=入札・契約情報の検索")

        page.wait_for_timeout(3000)

        # 次ステップ確認
        print("=== 遷移後フレーム ===")
        for f in page.frames:
            print(f.url)

        browser.close()

if __name__ == "__main__":
    main()
