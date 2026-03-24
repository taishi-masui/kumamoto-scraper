from playwright.sync_api import sync_playwright

def main():
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()

        # ★RIGHTだけ直接開く
        page.goto("https://ebid.kumamoto-idc.pref.kumamoto.jp/PPIAccepter/RightServlet")

        page.wait_for_load_state("networkidle")

        # ★検索ボタン
        page.click("input[name='btnSearch']")

        page.wait_for_timeout(3000)

        # ★データ取得
        rows = page.query_selector_all("#tBody tr")

        print(f"件数: {len(rows)}")

        for row in rows:
            cols = row.query_selector_all("td")

            if len(cols) < 5:
                continue

            print("-----")
            print("番号:", cols[0].inner_text().strip())
            print("工事名:", cols[2].inner_text().strip())
            print("日付:", cols[4].inner_text().strip())

        browser.close()

if __name__ == "__main__":
    main()
