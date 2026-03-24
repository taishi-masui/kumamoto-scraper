from playwright.sync_api import sync_playwright

def main():
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()

        # ① トップページ
        page.goto("https://ebid.kumamoto-idc.pref.kumamoto.jp/PPIAccepter/MainServlet?Error=&Message=")

        page.wait_for_timeout(3000)

        # ② メニューのフレーム取得
        menu_frame = page.frame(url=lambda url: "PJC001Servlet" in url)

        # ③ 「入札・契約情報の検索」クリック
        menu_frame.click("text=入札・契約情報の検索")

        page.wait_for_timeout(3000)

        # ④ 検索画面のフレーム取得
        search_frame = page.frame(url=lambda url: "PJC002" in url or "PJC501" in url)

        print("検索画面URL:", search_frame.url)

        # ⑤ 検索ボタン押す
        search_frame.click("input[value='検索']")

        page.wait_for_timeout(5000)

        # ⑥ 一覧フレーム取得
        result_frame = page.frame(url=lambda url: "PJC502" in url)

        print("一覧ページURL:", result_frame.url)

        # HTML確認
        html = result_frame.content()
        print("HTML一部:", html[:500])

        browser.close()

if __name__ == "__main__":
    main()
