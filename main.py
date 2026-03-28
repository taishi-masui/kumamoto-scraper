from playwright.sync_api import sync_playwright
import time
import csv
import re

def extract_detail(frame):
    """詳細フレームから項目を抽出"""
    try:
        text = frame.evaluate("() => document.body.innerText")
        place = re.search(r"場所\t([^\n]+)", text)
        price = re.search(r"予定価格\t([^\n]+)", text)
        status = re.search(r"状態\t([^\n]+)", text)
        period = re.search(r"工期\t([^\n]+)", text)
        return [
            place.group(1).strip() if place else "未設定",
            price.group(1).strip() if price else "非公表",
            status.group(1).strip() if status else "不明",
            period.group(1).strip() if period else "未記載"
        ]
    except:
        return ["抽出エラー", "", "", ""]

def main():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(user_agent="Mozilla/5.0...", locale="ja-JP")
        page = context.new_page()

        try:
            print("1. 検索実行...")
            page.goto("https://ebid.kumamoto-idc.pref.kumamoto.jp/PPIAccepter/AccepterServlet?kikan_no=0100", wait_until="networkidle")
            time.sleep(5)
            menu_f = next((f for f in page.frames if "PJC001Servlet" in f.url), page)
            menu_f.evaluate("jsLink(1,1);")
            
            # 検索リトライ
            for _ in range(10):
                for f in page.frames:
                    try:
                        if f.locator('input[name="btnSearch"]').count() > 0:
                            f.evaluate("jsSearch();")
                            break
                    except: continue
                else: 
                    time.sleep(3)
                    continue
                break

            print("2. 一覧の出現を待機...")
            time.sleep(15)

            all_results = []
            for i in range(10): # 最初の10件
                print(f"--- [{i+1}/10] 件目の処理開始 ---")
                
                # 毎回フレームを特定し直す（「戻る」後の安定のため）
                list_f = next((f for f in page.frames if "PJC502Servlet" in f.url), None)
                if not list_f: break

                # 一覧の基本情報を取得
                row = list_f.locator("#tBody tr").nth(i)
                base_data = [c.strip().replace('\n', ' ') for c in row.locator("td").all_text_contents() if c.strip()]
                
                # 詳細へ移動
                try:
                    btn = row.locator('img[onclick^="jsBidInfo"]')
                    btn.first.click()
                    time.sleep(5) # 詳細読み込み待ち
                    
                    detail_f = next((f for f in page.frames if "PJC503Servlet" in f.url), None)
                    if detail_f:
                        # データ抽出
                        detail_data = extract_detail(detail_f)
                        base_data.extend(detail_data)
                        
                        # ★最重要：一覧に戻る
                        print("  一覧へ戻ります...")
                        detail_f.evaluate("jsBack();")
                        time.sleep(5) # 一覧の再表示待ち
                    else:
                        base_data.extend(["詳細エラー", "", "", ""])
                except Exception as e:
                    print(f"  エラー: {e}")
                    base_data.extend(["処理失敗", "", "", ""])

                all_results.append(base_data)

            # 保存
            if all_results:
                with open('result.csv', 'w', encoding='utf-8-sig', newline='') as f:
                    writer = csv.writer(f)
                    writer.writerows(all_results)
                print(f"★完了！ 10件分の詳細付きデータを保存しました。")

        except Exception as e:
            print(f"重大なエラー: {e}")
        finally:
            browser.close()

if __name__ == "__main__":
    main()
