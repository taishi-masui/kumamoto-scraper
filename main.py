from playwright.sync_api import sync_playwright

def main():
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()

        # トップページ
        page.goto("https://ebid.kumamoto-idc.pref.kumamoto.jp/PPIAccepter/MainServlet?Error=&Message=")

        # 少し待つ（重要）
        page.wait_for_timeout(3000)

        # フレーム対応（ここがポイント）
        frames = page.frames

        print("フレーム数:", len(frames))

        for f in frames:
            print("Frame URL:", f.url)

        browser.close()

if __name__ == "__main__":
    main()
