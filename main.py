from playwright.sync_api import sync_playwright
import time
import csv
import re

def format_currency(v):
    """数字を ¥1,234,567 の形式に整形する"""
    if not v: return ""
    num_str = re.sub(r'[^\d]', '', v)
    if not num_str: return ""
    return f"¥{int(num_str):,}"

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
            search_started = False
            for _ in range(10): 
                for f in page.frames:
                    try:
                        if f.locator('input[name="btnSearch"]').count() > 0:
                            f.evaluate("jsSearch();")
                            search_started = True
                            break
                    except: continue
                if search_started: break
                time.sleep(3)

            print("2. 一覧待機...")
            target_f = None
            for _ in range(10):
                for f in page.frames:
                    if f.evaluate("() => document.querySelectorAll('#tBody tr').length") > 0:
                        target_f = f
                        break
                if target_f: break
                time.sleep(3)
            
            if target_f:
                # 一覧情報確保
                row_el = target_f.locator("#tBody tr").nth(0)
                base_data = [c.inner_text().strip().replace('\n', ' ') for c in row_el.locator("td").all()][0:4]

                print("3. 詳細画面へ遷移中...")
                target_f.evaluate("jsBidInfo(0);")
                time.sleep(15)
                
                # --- 成功したスキャンロジックをそのまま使用 ---
                detail_f = None
                detail_txt = ""
                for f in page.frames:
                    try:
                        # URLで判定（これが最も確実でした）
                        if "PJC503Servlet" in f.url:
                            detail_f = f
                            detail_txt = f.evaluate("() => document.body.innerText")
                            break
                    except: continue

                if detail_f:
                    print("★詳細フレーム捕捉。解析を開始します。")
                    
                    def get_v(label):
                        m = re.search(rf"{label}\s*([^\n\r]+)", detail_txt)
                        return m.group(1).strip() if m else ""

                    # 詳細基本7項目
                    # 電子入札案件番号は ="000..." 形式で0落ちを防止
                    d_fields = [
                        f'="{get_v("電子入札案件番号")}"',
                        get_v("工事・業務名"),
                        get_v("場所"),
                        format_currency(get_v("予定価格")),
                        format_currency(get_v("最低制限価格")),
                        get_v("開札（予定）日"),
                        get_v("状態")
                    ]

                    # 業者10社分固定
                    b_part = []
                    try:
                        bid_txt = detail_txt.split("摘要")[-1].split("備考")[0]
                        matches = re.findall(r"([^\t\n\r]+?)\s+([0-9,]{4,})", bid_txt)
                        valid = [[m[0].strip(), format_currency(m[1])] for m in matches if not m[0].strip().isdigit()]
                        for k in range(10):
                            b_part.extend(valid[k] if k < len(valid) else ["", ""])
                    except:
                        b_part = [""] * 20

                    # ヘッダー作成
                    h = ["施行番号/案件番号", "業種 種別", "工事・業務名", "契約方法"]
                    h += ["電子入札案件番号", "工事・業務名", "場所", "予定価格", "最低制限価格", "開札（予定）日", "状態"]
                    for k in range(1, 11):
                        h.extend([f"業者{k}", f"金額{k}"])

                    # 保存
                    with open('result.csv', 'w', encoding='utf-8-sig', newline='') as f:
                        writer = csv.writer(f)
                        writer.writerow(h)
                        writer.writerow(base_data + d_fields + b_part)
                    
                    print(f"★result.csv を作成しました。")
                    detail_f.evaluate("jsBack();")
                else:
                    print("!! 詳細フレームが見つかりませんでした。再度スキャンが必要です。")
            else:
                print("!! 一覧が見つかりませんでした。")

        except Exception as e:
            print(f"重大なエラー: {e}")
        finally:
            browser.close()

if __name__ == "__main__":
    main()
