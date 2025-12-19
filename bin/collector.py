import requests
from bs4 import BeautifulSoup
import json
import datetime
import os
import sys

# --- 配置路径 ---
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "data/raw")
DATE_STR = datetime.datetime.now().strftime("%Y-%m-%d")

# 确保目录存在
if not os.path.exists(DATA_DIR):
    os.makedirs(DATA_DIR)


def save_json(data, period):
    """保存数据到指定分类文件"""
    filename = f"github_{period}_{DATE_STR}.json"
    filepath = os.path.join(DATA_DIR, filename)
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)
    print(f"[SUCCESS] {period} 数据已保存: {len(data)} 条")


# --- 策略 A: 爬虫抓取 Trending (适用 Daily, Weekly, Monthly) ---
def scrape_trending(period):
    print(f"\n[TASK] 正在爬取 Trending: {period}...")
    url = f"https://github.com/trending?since={period}"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    }

    try:
        resp = requests.get(url, headers=headers, timeout=15)
        soup = BeautifulSoup(resp.text, "html.parser")
        repos = []

        articles = soup.select("article.Box-row")
        if not articles:
            print(
                f"[WARN] 未找到项目元素，可能是 GitHub 页面结构变更或被反爬拦截 (Period: {period})"
            )

        for article in articles:
            try:
                # 1. 获取项目名和链接 (GitHub 结构变更为 h2 > a)
                h2 = article.select_one("h2")
                if h2 and h2.select_one("a"):
                    a_tag = h2.select_one("a")
                    # 清洗名称: owner / repo -> owner/repo
                    name = a_tag.text.strip().replace("\n", "").replace(" ", "")
                    # 获取相对链接: /owner/repo -> https://github.com/owner/repo
                    repo_url = "https://github.com" + a_tag["href"]
                else:
                    name = "Unknown"
                    repo_url = "#"

                # 2. 获取语言
                lang_span = article.select_one('span[itemprop="programmingLanguage"]')
                lang = lang_span.text.strip() if lang_span else "Other"

                # 3. 获取 Stars (Trending 页面有两个 star 数字，取总数)
                # 通常是链接中带有 star 图标的那个
                star_a = article.select_one('a[href$="/stargazers"]')
                if star_a:
                    stars_text = star_a.text.strip().replace(",", "")
                    try:
                        stars = int(stars_text)
                    except:
                        stars = 0
                else:
                    # 备用方案：尝试获取纯文本
                    stats = article.select("a.Link--muted")
                    if stats:
                        stars = int(stats[0].text.strip().replace(",", ""))
                    else:
                        stars = 0

                repos.append(
                    {
                        "name": name,
                        "language": lang,
                        "stars": stars,
                        "url": repo_url,  # 新增 URL 字段
                        "desc": "Trending item",
                    }
                )
            except Exception as e:
                print(f"[WARN] 解析单条数据出错: {e}")
                continue

        save_json(repos, period)

    except Exception as e:
        print(f"[ERROR] 爬取 {period} 失败: {e}")


# --- 策略 B: 调用 API 搜索 (适用 Yearly, All) ---
def fetch_api_search(period):
    print(f"\n[TASK] 正在调用 API 搜索: {period}...")

    if period == "yearly":
        one_year_ago = (
            datetime.datetime.now() - datetime.timedelta(days=365)
        ).strftime("%Y-%m-%d")
        q = f"created:>{one_year_ago}"
    else:
        q = "stars:>1000"

    url = "https://api.github.com/search/repositories"
    params = {"q": q, "sort": "stars", "order": "desc", "per_page": 20}

    try:
        resp = requests.get(url, params=params, timeout=15)
        if resp.status_code == 200:
            items = resp.json().get("items", [])
            repos = []
            for item in items:
                repos.append(
                    {
                        "name": item["full_name"],
                        "language": item["language"] if item["language"] else "Other",
                        "stars": item["stargazers_count"],
                        "url": item["html_url"],  # API 直接提供 html_url
                        "desc": item["description"],
                    }
                )
            save_json(repos, period)
        else:
            print(f"[ERROR] API 请求失败 {period}: {resp.status_code}")
            # 生成一条假数据避免前端空屏
            save_json(
                [
                    {
                        "name": "API_Limit_Reached",
                        "language": "Error",
                        "stars": 0,
                        "url": "https://github.com",
                        "desc": "API rate limit exceeded",
                    }
                ],
                period,
            )

    except Exception as e:
        print(f"[ERROR] API 搜索异常 {period}: {e}")


if __name__ == "__main__":
    scrape_trending("daily")
    scrape_trending("weekly")
    scrape_trending("monthly")
    fetch_api_search("yearly")
    fetch_api_search("all")
    print("\n[DONE] 所有采集任务完成。")
