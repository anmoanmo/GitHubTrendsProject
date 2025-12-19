import requests
from bs4 import BeautifulSoup
import json
import datetime
import os
import sys

# 定义路径
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "data/raw")
# 自动创建目录
if not os.path.exists(DATA_DIR):
    os.makedirs(DATA_DIR)

DATE_STR = datetime.datetime.now().strftime("%Y-%m-%d")
FILE_PATH = os.path.join(DATA_DIR, f"github_trending_{DATE_STR}.json")


def fetch_data():
    url = "https://github.com/trending"
    # 增加超时和重试机制
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    }

    try:
        print(f"[INFO] 开始采集: {url}")
        resp = requests.get(url, headers=headers, timeout=15)
        resp.raise_for_status()  # 检查 HTTP 响应状态

        soup = BeautifulSoup(resp.text, "html.parser")
        repos = []

        for article in soup.select("article.Box-row"):
            h1 = article.select_one("h1")
            name = (
                h1.text.strip().replace("\n", "").replace(" ", "") if h1 else "Unknown"
            )

            lang_span = article.select_one('span[itemprop="programmingLanguage"]')
            lang = lang_span.text.strip() if lang_span else "Other"

            star_a = article.select_one("a.Link--muted")
            stars = int(star_a.text.strip().replace(",", "")) if star_a else 0

            repos.append(
                {"name": name, "language": lang, "stars": stars, "date": DATE_STR}
            )

        with open(FILE_PATH, "w", encoding="utf-8") as f:
            json.dump(repos, f, ensure_ascii=False, indent=4)

        print(f"[INFO] 成功采集 {len(repos)} 个项目到 {FILE_PATH}")

    except Exception as e:
        print(f"[ERROR] 采集失败: {e}")
        sys.exit(1)  # 显式返回错误码供 Shell 捕获


if __name__ == "__main__":
    fetch_data()
