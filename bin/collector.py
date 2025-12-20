import requests
from bs4 import BeautifulSoup
import json
import datetime
import os
import random
from concurrent.futures import ThreadPoolExecutor, as_completed

# --- 用户配置 ---
# 如果爬取 GitHub 很慢，尝试填入代理，例如 "http://127.0.0.1:7890"
PROXY_URL = None

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
    return random.choice(
        [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
        ]
    )


def save_json(data, period):
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
    print(f"[START] 抓取: {period}...")
    url = f"https://github.com/trending?since={period}"
    headers = {"User-Agent": get_random_ua()}
    repos = []

    try:
        # 设置 timeout 为 15秒，防止卡死
        resp = requests.get(url, headers=headers, proxies=get_proxies(), timeout=15)
        if resp.status_code != 200:
            return period, []

        soup = BeautifulSoup(resp.text, "html.parser")
        articles = soup.select("article.Box-row")

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
    except Exception as e:
        print(f"[ERROR] {period}: {e}")
    return period, repos


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
        resp = requests.get(
            url, params=params, headers=headers, proxies=get_proxies(), timeout=15
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
    # 使用 ThreadPoolExecutor 并发
    with ThreadPoolExecutor(max_workers=5) as executor:
        tasks = {
            executor.submit(task_scrape_trending, p): p
            for p in ["daily", "weekly", "monthly"]
        }
        tasks.update({executor.submit(task_fetch_api, p): p for p in ["yearly", "all"]})

        for future in as_completed(tasks):
            period, data = future.result()
            save_json(data, period)


if __name__ == "__main__":
    main()
