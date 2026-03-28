from playwright.sync_api import sync_playwright
import time
import csv
import re

def extract_detail(frame):
    """詳細フレーム(PJC503Servlet)から特定の項目を抽出"""
    try:
        # フレーム内の全テキストを取得
        text = frame.evaluate("() => document.body.innerText")
        
        # 調査結果に基づき、タブ区切りのテキストから抽出
        place = re.search(r"場所\t([^\n]+)", text)
        price = re.search(r"予定価格\t([^\n]+)", text)
        status = re.search(r"状態\t([^\n]+)", text)
        period = re.search(r"工期\t([^\n]+)", text) # 工期も追加してみました
        
        return [
            place.group(1).strip() if place else "未設定",
            price.group(1).strip() if price else "非公表",
            status.group(1).strip() if status else "不明",
            period.group(1).strip() if period else "未記載"
        ]
    except Exception as e:
        return [f"エラー:{str(e)}", "", "", ""]

def main():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(user_agent="Mozilla/5.0...", locale="ja-JP")
        page = context.new_page()

        try:
            print("1. 検索画面を表示...")
            page.goto("https://ebid.kumamoto-idc.pref.kumamoto.jp/PPIAccepter/AccepterServlet?kikan_no=0100", wait_until="networkidle")
            time.sleep(5)
            menu_f = next((f for f in page.frames if "PJC001Servlet" in f.url), page)
            menu_f.evaluate("jsLink(1,1);")
            
            print("2. デフォルト設定(10件)で検索実行...")
            search_started = False
            for _ in range(10):
                for f in page.frames:
                    try:
                        btn = f.locator('input[name="btnSearch"]')
                        if btn.count() > 0:
                            f.evaluate("jsSearch();")
                            search_started = True
                            break
                    except: continue
                if search_started: break
                time.sleep(3)

            print("3. 結果一覧の出現を待機...")
            time.sleep(15)

            # 一覧フレームを特定
            list_f = next((f for f in page.frames if "PJC502Servlet" in f.url), None)
            if not list_f:
                print("一覧が見つかりません。")
                return

            all_results = []
            rows = list_f.locator("#tBody tr").all()
            
            # 最初の10件（または存在する分だけ）を処理
            target_rows = rows[:10]
            print(f"4. {len(target_rows)}件の詳細情報を順次取得します...")

            for i, r in enumerate(target_rows):
                # 一覧の基本情報を取得
                cols = r.locator("td").all_text_contents()
                base_data = [c.strip().replace('\n', ' ') for c in cols if c.strip()]
                
                if base_data:
                    try:
                        # 詳細ボタンをクリック（jsBidInfo(index)）
                        btn = r.locator(f'img[onclick*="jsBidInfo({i})"]')
                        if btn.count() > 0:
                            btn.click()
                            time.sleep(4) # 詳細フレームの更新待ち
                            
                            # 詳細フレーム(PJC503Servlet)を特定してデータ抽出
                            detail_f = next((f for f in page.frames if "PJC503Servlet" in f.url), None)
                            if detail_f:
                                detail_data = extract_detail(detail_f)
                                base_data.extend(detail_data)
                                print(f"  [{i+1}/10] 詳細取得完了: {base_data[2][:15]}...")
                            else:
                                print(f"  [{i+1}/10] 詳細フレームが見つかりません")
                                base_data.extend(["取得失敗", "", "", ""])
                    except Exception as e:
                        print(f"  [{i+1}/10] エラー: {e}")
                        base_data.extend(["エラー", "", "", ""])

                    all_results.append(base_data)

            # 保存
            if all_results:
                with open('result.csv', 'w', encoding='utf-8-sig', newline='') as f:
                    writer = csv.writer(f)
                    writer.writerows(all_results)
                print(f"★完了！ {len(all_results)} 件を詳細付きで result.csv に保存しました。")

        except Exception as e:
            print(f"重大なエラー: {e}")
        finally:
            browser.close()

if __name__ == "__main__":
    main()
