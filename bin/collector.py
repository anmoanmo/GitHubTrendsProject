import requests
from bs4 import BeautifulSoup
import json
import datetime
import os
import random
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

# --- 用户配置 ---
# [关键] 如果你在国内，强烈建议填入本地代理端口，否则极易失败
# 例如 Clash 默认是: "http://127.0.0.1:7890"
PROXY_URL = None
# PROXY_URL = "http://127.0.0.1:7890"

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "data/raw")
DATE_STR = datetime.datetime.now().strftime("%Y-%m-%d")

if not os.path.exists(DATA_DIR):
    os.makedirs(DATA_DIR)


def get_proxies():
    if PROXY_URL:
        return {"http": PROXY_URL, "https": PROXY_URL}
    return None


def get_random_ua():
    uas = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.0.0 Safari/537.36",
    ]
    return random.choice(uas)


def save_json(data, period):
    if not data:
        print(f"  [WARN] {period} 数据为空，未保存或保存为空列表")

    filename = f"github_{period}_{DATE_STR}.json"
    filepath = os.path.join(DATA_DIR, filename)
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)
    print(f"  [SAVE] {period} 已保存 {len(data)} 条")


def parse_stars_text(text):
    if not text:
        return 0
    text = text.strip().replace(",", "").lower()
    try:
        if "k" in text:
            return int(float(text.replace("k", "")) * 1000)
        return int(text)
    except:
        return 0


def task_scrape_trending(period):
    print(f"[START] 抓取: {period} (尝试连接 GitHub Trending)...")
    url = f"https://github.com/trending?since={period}"

    # 重试机制：最多尝试 3 次
    for attempt in range(1, 4):
        try:
            headers = {
                "User-Agent": get_random_ua(),
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
                "Accept-Language": "en-US,en;q=0.9",
            }

            # 延长超时时间到 30 秒
            resp = requests.get(url, headers=headers, proxies=get_proxies(), timeout=30)

            if resp.status_code != 200:
                print(f"  [RETRY] {period} HTTP {resp.status_code} (第 {attempt} 次)")
                time.sleep(2)
                continue

            soup = BeautifulSoup(resp.text, "html.parser")
            articles = soup.select("article.Box-row")

            if not articles:
                print(
                    f"  [RETRY] {period} 未找到页面元素 (可能被重定向或结构变更) (第 {attempt} 次)"
                )
                time.sleep(2)
                continue

            repos = []
            for article in articles:
                try:
                    h2 = article.select_one("h2")
                    a_tag = h2.select_one("a")
                    repo_url = "https://github.com" + a_tag["href"]
                    name = a_tag.text.strip().replace("\n", "").replace(" ", "")

                    p_desc = article.select_one("p.col-9")
                    desc = p_desc.text.strip() if p_desc else "No description"

                    lang = article.select_one("[itemprop='programmingLanguage']")
                    language = lang.text.strip() if lang else "Other"

                    total_stars = 0
                    star_elem = article.select_one("a[href$='/stargazers']")
                    if star_elem:
                        total_stars = parse_stars_text(star_elem.text)

                    period_stars = 0
                    stats_spans = article.select("span.d-inline-block.float-sm-right")
                    if stats_spans and "stars " in stats_spans[0].text:
                        period_stars = parse_stars_text(
                            stats_spans[0].text.split(" stars")[0]
                        )

                    repos.append(
                        {
                            "name": name,
                            "language": language,
                            "stars_total": total_stars,
                            "stars_period": period_stars,
                            "url": repo_url,
                            "desc": desc,
                        }
                    )
                except:
                    continue

            if repos:
                return period, repos  # 成功获取，直接返回

        except Exception as e:
            print(f"  [RETRY] {period} 连接异常: {str(e)[:50]}... (第 {attempt} 次)")
            time.sleep(2)

    print(f"[FAIL] {period} 经 3 次重试后彻底失败，该分类将无数据。")
    return period, []


def task_fetch_api(period):
    print(f"[START] API搜索: {period}...")
    q = "stars:>1000"
    if period == "yearly":
        limit = (datetime.datetime.now() - datetime.timedelta(days=365)).strftime(
            "%Y-%m-%d"
        )
        q = f"created:>{limit}"

    url = "https://api.github.com/search/repositories"
    params = {"q": q, "sort": "stars", "order": "desc", "per_page": 20}
    headers = {"User-Agent": get_random_ua()}

    try:
        # API 相对稳定，但也增加超时
        resp = requests.get(
            url, params=params, headers=headers, proxies=get_proxies(), timeout=30
        )
        repos = []
        if resp.status_code == 200:
            for item in resp.json().get("items", []):
                repos.append(
                    {
                        "name": item["full_name"],
                        "language": item["language"] or "Other",
                        "stars_total": item["stargazers_count"],
                        "stars_period": 0,
                        "url": item["html_url"],
                        "desc": item["description"],
                    }
                )
        return period, repos
    except Exception as e:
        print(f"[ERROR] API {period}: {e}")
        return period, []


def main():
    print(">>> 开始采集数据 (并发模式)...")
    with ThreadPoolExecutor(max_workers=5) as executor:
        tasks = {
            executor.submit(task_scrape_trending, p): p
            for p in ["daily", "weekly", "monthly"]
        }
        tasks.update({executor.submit(task_fetch_api, p): p for p in ["yearly", "all"]})

        for future in as_completed(tasks):
            period, data = future.result()
            save_json(data, period)
    print(">>> 采集结束。")


if __name__ == "__main__":
    main()
