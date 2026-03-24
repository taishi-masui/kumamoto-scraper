from playwright.sync_api import sync_playwright

def main():
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()

        page.goto("https://ebid.kumamoto-idc.pref.kumamoto.jp/PPIAccepter/MainServlet?Error=&Message=")

        page.wait_for_timeout(5000)

        # ★フレーム一覧を確認（デバッグ）
        frames = page.frames
        print("=== フレーム一覧 ===")
        for f in frames:
            print(f.name, f.url)

        # ★frmLEFTを探す（確実版）
        left = None
        for f in frames:
            if "PJC001Servlet" in f.url:
                left = f
                break

        if not left:
            raise Exception("LEFTフレーム見つからない")

        left.click("text=入札・契約情報の検索")

        page.wait_for_timeout(3000)

        # ★RIGHTも同じやり方
        frames = page.frames
        right = None
        for f in frames:
            if "RightServlet" in f.url:
                right = f
                break

        if not right:
            raise Exception("RIGHTフレーム見つからない")

        right.click("input[name='btnSearch']")

        page.wait_for_timeout(3000)

        rows = right.query_selector_all("#tBody tr")

        print(f"件数: {len(rows)}")

        browser.close()

if __name__ == "__main__":
    main()
