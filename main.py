from playwright.sync_api import sync_playwright

def main():
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()

        # ① トップページ
        page.goto("https://ebid.kumamoto-idc.pref.kumamoto.jp/PPIAccepter/MainServlet?Error=&Message=")

        # ② frmRIGHT → frmTOP に入る
        frame = page.frame_locator("frame[name='frmRIGHT']") \
                    .frame_locator("frame[name='frmTOP']")

        # ③ 検索ボタン押す
        frame.locator("input[name='btnSearch']").click()

        # ④ 結果待つ
        frame.locator("#tBody tr").first.wait_for()

        # ⑤ データ取得
        rows = frame.locator("#tBody tr").all()

        for row in rows:
            cols = row.locator("td").all_inner_texts()
            print(cols)

        browser.close()

if __name__ == "__main__":
    main()
