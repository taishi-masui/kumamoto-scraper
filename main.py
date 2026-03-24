from playwright.sync_api import sync_playwright
import time

def main():
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()

        page.goto("https://ebid.kumamoto-idc.pref.kumamoto.jp/PPIAccepter/MainServlet?Error=&Message=")

        # ★ フレームが増えるまで待つ
        for i in range(10):
            frames = page.frames
            print(f"フレーム数: {len(frames)}")
            if len(frames) > 1:
                break
            time.sleep(1)

        print("=== フレーム一覧 ===")
        for f in page.frames:
            print(f.url)

        # ★ PJC001を探す
        menu_frame = None
        for f in page.frames:
            if "PJC001Servlet" in f.url:
                menu_frame = f

        if menu_frame is None:
            raise Exception("PJC001フレームが見つからない")

        # ★ クリック
        menu_frame.click("text=入札・契約情報の検索")

        time.sleep(3)

        print("=== 遷移後フレーム ===")
        for f in page.frames:
            print(f.url)

        browser.close()

if __name__ == "__main__":
    main()
