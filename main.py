from playwright.sync_api import sync_playwright

def main():
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()

        page.goto("https://ebid.kumamoto-idc.pref.kumamoto.jp/PPIAccepter/MainServlet?Error=&Message=")
        page.wait_for_load_state("networkidle")

        # 左フレーム
        left = page.frame(name="frmLEFT")

        # メニュークリック
        left.click("text=入札・契約情報の検索")

        page.wait_for_timeout(3000)

        # 右フレーム
        right = page.frame(name="frmRIGHT")

        # 検索クリック
        right.click("input[name='btnSearch']")

        page.wait_for_timeout(3000)

        right = page.frame(name="frmRIGHT")

        # =========================
        # ★ここが本題（データ取得）
        # =========================

        rows = right.query_selector_all("#tBody tr")

        print(f"件数: {len(rows)}")

        for row in rows:
            cols = row.query_selector_all("td")

            if len(cols) < 5:
                continue

            number = cols[0].inner_text().strip()
            category = cols[1].inner_text().strip()
            title = cols[2].inner_text().strip()
            method = cols[3].inner_text().strip()
            date = cols[4].inner_text().strip()

            print("-----")
            print("番号:", number)
            print("業種:", category)
            print("工事名:", title)
            print("方法:", method)
            print("日付:", date)

        browser.close()

if __name__ == "__main__":
    main()
