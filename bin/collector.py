import requests
from bs4 import BeautifulSoup
import json
import datetime
import os
import random
import time
import subprocess
from concurrent.futures import ThreadPoolExecutor, as_completed


# --- 1. 网络与代理配置 (自动适配 WSL) ---
def get_host_ip():
    """自动获取 WSL 宿主机 IP，解决 Connection Refused 问题"""
    try:
        # 读取默认网关
        result = subprocess.check_output(
            "ip route show | grep default", shell=True
        ).decode()
        return result.split()[2]
    except:
        return "127.0.0.1"


# 自动配置代理
HOST_IP = get_host_ip()
PROXY_PORT = "7890"  
PROXY_URL = f"http://{HOST_IP}:{PROXY_PORT}"

print(f">>> [Init] 宿主机IP: {HOST_IP}, 代理地址: {PROXY_URL}")

# --- 2. 基础配置 ---
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "data/raw")
DATE_STR = datetime.datetime.now().strftime("%Y-%m-%d")

if not os.path.exists(DATA_DIR):
    os.makedirs(DATA_DIR)


def get_proxies():
    return {"http": PROXY_URL, "https": PROXY_URL}


def get_random_ua():
    uas = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
    ]
    return random.choice(uas)


def parse_stars_text(text):
    """解析 '1.2k' -> 1200"""
    if not text:
        return 0
    text = text.strip().replace(",", "").lower()
    try:
        if "k" in text:
            return int(float(text.replace("k", "")) * 1000)
        return int(text)
    except:
        return 0


# --- 3. 核心引擎 A: 爬虫 (高精度) ---
def engine_scrape(period):
    """
    尝试从 HTML 页面爬取数据
    优势：能获取 'stars today' (真实增量)
    劣势：不稳定，易被反爬
    """
    print(f"[Engine-A] 正在爬取: {period}...")
    url = f"https://github.com/trending?since={period}"

    # 最多重试 2 次，避免浪费时间
    for attempt in range(1, 3):
        try:
            # 随机延时，模拟真人
            time.sleep(random.uniform(1, 2))

            resp = requests.get(
                url,
                headers={
                    "User-Agent": get_random_ua(),
                    "Accept-Language": "en-US,en;q=0.9",
                },
                proxies=get_proxies(),
                timeout=15,  # 15秒超时，超时后自动触发保底
            )

            if resp.status_code != 200:
                raise Exception(f"HTTP {resp.status_code}")

            soup = BeautifulSoup(resp.text, "html.parser")
            articles = soup.select("article.Box-row")

            if not articles:
                raise Exception("页面结构改变或为空")

            repos = []
            for article in articles:
                try:
                    h2 = article.select_one("h2")
                    name = h2.select_one("a").get("href").strip("/")

                    p = article.select_one("p.col-9")
                    desc = p.text.strip() if p else "No description"

                    lang = article.select_one("[itemprop='programmingLanguage']")
                    language = lang.text.strip() if lang else "Other"

                    # 总星数
                    total_stars = 0
                    for a in article.select("a.Link--muted"):
                        if "stargazers" in a.get("href", ""):
                            total_stars = parse_stars_text(a.text)

                    # 周期增量 (Today/Weekly stars)
                    period_stars = 0
                    span = article.select_one("span.d-inline-block.float-sm-right")
                    if span:
                        period_stars = parse_stars_text(span.text.split(" stars")[0])

                    repos.append(
                        {
                            "name": name,
                            "language": language,
                            "stars_total": total_stars,
                            "stars_period": period_stars,
                            "url": f"https://github.com/{name}",
                            "desc": desc,
                            "source": "scrape",
                        }
                    )
                except:
                    continue

            if repos:
                print(f"  ✅ [Engine-A] {period} 爬取成功 ({len(repos)}条)")
                return repos

        except Exception as e:
            print(f"  ⚠️ [Engine-A] {period} 尝试 {attempt} 失败: {str(e)[:50]}")

    return None  # 失败返回 None，触发 API 保底


# --- 4. 核心引擎 B: API 保底 (高可用) ---
def engine_api_fallback(period):
    """
    当爬虫失败时，使用 API 获取数据
    优势：极其稳定，只要代理通就能获取
    策略：混合查询 '新创建项目' 和 '活跃老项目'
    """
    print(f"[Engine-B] 启动 API 保底: {period}...")

    # 构造智能查询条件
    now = datetime.datetime.now()
    queries = []

    if period == "daily":
        since = (now - datetime.timedelta(days=1)).strftime("%Y-%m-%d")
        # 查新建 + 查活跃(近期有提交且星数高)
        queries = [f"created:>{since}", f"pushed:>{since} stars:>1000"]
    elif period == "weekly":
        since = (now - datetime.timedelta(days=7)).strftime("%Y-%m-%d")
        queries = [f"created:>{since}", f"pushed:>{since} stars:>1000"]
    elif period == "monthly":
        since = (now - datetime.timedelta(days=30)).strftime("%Y-%m-%d")
        queries = [f"created:>{since}", f"pushed:>{since} stars:>2000"]
    elif period == "yearly":
        since = (now - datetime.timedelta(days=365)).strftime("%Y-%m-%d")
        queries = [f"created:>{since} stars:>500"]
    else:  # all time
        queries = ["stars:>2000"]

    url = "https://api.github.com/search/repositories"
    all_repos = {}  # 使用字典去重

    for q in queries:
        try:
            params = {"q": q, "sort": "stars", "order": "desc", "per_page": 15}
            # API 请求增加 30秒 超时，保证稳定性
            resp = requests.get(
                url,
                params=params,
                headers={"User-Agent": get_random_ua()},
                proxies=get_proxies(),
                timeout=30,
            )

            if resp.status_code == 200:
                items = resp.json().get("items", [])
                for item in items:
                    name = item.get("full_name")
                    if name and name not in all_repos:
                        # 估算增量逻辑：
                        # API 无法直接给增量。如果是新项目，假设 增量=总量。
                        # 如果是老项目，增量设为 0 (前端会隐藏 +0，只显示总量，交互更友好)
                        is_new = False
                        if item.get("created_at"):
                            c_date = item["created_at"][:10]
                            # 如果创建时间在查询窗口内，视为新项目
                            if period == "daily" and c_date >= (
                                now - datetime.timedelta(days=1)
                            ).strftime("%Y-%m-%d"):
                                is_new = True
                            if period == "weekly" and c_date >= (
                                now - datetime.timedelta(days=7)
                            ).strftime("%Y-%m-%d"):
                                is_new = True

                        stars_total = item.get("stargazers_count", 0)

                        all_repos[name] = {
                            "name": name,
                            "language": item.get("language") or "Other",
                            "stars_total": stars_total,
                            "stars_period": stars_total if is_new else 0,
                            "url": item.get("html_url"),
                            "desc": item.get("description"),
                            "source": "api_fallback",
                        }
            else:
                print(f"  ⚠️ [Engine-B] {period} API Error: {resp.status_code}")

        except Exception as e:
            print(f"  ⚠️ [Engine-B] {period} 查询失败: {e}")

    # 结果排序：优先展示有增量的新项目，其次是高星老项目
    results = list(all_repos.values())
    results.sort(key=lambda x: (x["stars_period"], x["stars_total"]), reverse=True)

    if results:
        print(f"  ✅ [Engine-B] {period} 保底成功 ({len(results)}条)")
    else:
        print(f"  ❌ [Engine-B] {period} 获取失败 (网络全断?)")

    return results


# --- 5. 任务调度 ---
def collect_task(period):
    data = []

    # 策略路由：
    # 日/周/月榜 -> 优先爬虫 -> 失败则 API
    if period in ["daily", "weekly", "monthly"]:
        data = engine_scrape(period)
        if not data:  # 如果爬虫返回 None
            data = engine_api_fallback(period)

    # 年/总榜 -> 直接 API (GitHub 官网没有这两个维度的 Trending 页面)
    else:
        data = engine_api_fallback(period)

    return period, data or []


def save_json(data, period):
    if not data:
        return
    filename = f"github_{period}_{DATE_STR}.json"
    filepath = os.path.join(DATA_DIR, filename)
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)
    print(f"  💾 [Save] {period} 保存完毕")


def main():
    print(f"========== 任务开始 {DATE_STR} ==========")
    start_time = time.time()

    periods = ["daily", "weekly", "monthly", "yearly", "all"]

    with ThreadPoolExecutor(max_workers=3) as executor:
        future_to_p = {executor.submit(collect_task, p): p for p in periods}

        for future in as_completed(future_to_p):
            period, data = future.result()
            save_json(data, period)

    print(f"========== 任务结束 (耗时 {time.time() - start_time:.2f}s) ==========")


if __name__ == "__main__":
    main()
