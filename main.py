from playwright.sync_api import sync_playwright

def main():
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()

        page.goto("https://ebid.kumamoto-idc.pref.kumamoto.jp/PPIAccepter/MainServlet?Error=&Message=")

        # ★ここ超重要：フレームが出るまで待つ
        page.wait_for_selector("frame[name='frmRIGHT']")

        # ★frmRIGHT取得
        right = page.frame(name="frmRIGHT")

        # ★frmTOPが出るまで待つ
        page.wait_for_timeout(2000)

        top = right.child_frames[0]

        # ★検索ボタン待つ
        top.wait_for_selector("input[name='btnSearch']")

        # ★クリック
        top.click("input[name='btnSearch']")

        # ★結果待つ
        top.wait_for_selector("#tBody tr")

        rows = top.query_selector_all("#tBody tr")

        for row in rows:
            cols = row.query_selector_all("td")
            print([c.inner_text() for c in cols])

        browser.close()

if __name__ == "__main__":
    main()
