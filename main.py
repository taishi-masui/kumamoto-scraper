from playwright.sync_api import sync_playwright

def main():
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()

        page.goto("https://ebid.kumamoto-idc.pref.kumamoto.jp/PPIAccepter/MainServlet?Error=&Message=")

        # ★フレームが出るまで待つ
        page.wait_for_timeout(3000)

        # ★ここ修正（None対策）
        left = None
        for _ in range(10):
            left = page.frame(name="frmLEFT")
            if left:
                break
            page.wait_for_timeout(1000)

        if not left:
            raise Exception("frmLEFTが取得できない")

        # メニュークリック
        left.click("text=入札・契約情報の検索")

        page.wait_for_timeout(3000)

        # 右フレーム取得（同じく待つ）
        right = None
        for _ in range(10):
            right = page.frame(name="frmRIGHT")
            if right:
                break
            page.wait_for_timeout(1000)

        if not right:
            raise Exception("frmRIGHTが取得できない")

        # 検索
        right.click("input[name='btnSearch']")

        page.wait_for_timeout(3000)

        right = page.frame(name="frmRIGHT")

        rows = right.query_selector_all("#tBody tr")

        print(f"件数: {len(rows)}")

        for row in rows:
            cols = row.query_selector_all("td")

            if len(cols) < 5:
                continue

            print("-----")
            print(cols[0].inner_text().strip())
            print(cols[2].inner_text().strip())

        browser.close()

if __name__ == "__main__":
    main()
