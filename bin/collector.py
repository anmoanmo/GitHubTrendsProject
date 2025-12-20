import requests
from bs4 import BeautifulSoup
import json
import datetime
import os
import random
import time
import subprocess
import urllib3
from concurrent.futures import ThreadPoolExecutor, as_completed

# 禁用代理情况下的 SSL 警告
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# --- 1. 配置管理 ---
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "data/raw")
DATE_STR = datetime.datetime.now().strftime("%Y-%m-%d")

# 获取 GitHub Token (推荐配置，防限流)
GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN", "")


# --- 2. 智能网络配置 ---
def get_proxy_config():
    """
    智能获取代理配置。
    优先级：
    1. 环境变量 (HTTP_PROXY) - 适用于服务器/CI/其他开发者
    2. WSL 自动探测 - 适用于你的本地开发环境
    3. 无代理 - 直连
    """
    # 1. 尝试读取环境变量
    env_proxy = os.environ.get("HTTP_PROXY") or os.environ.get("HTTPS_PROXY")
    if env_proxy:
        return {"http": env_proxy, "https": env_proxy}, "系统环境变量"

    # 2. 尝试 WSL 自动探测 (你的特殊需求)
    try:
        # 判断是否在 WSL 环境 (读取内核版本信息)
        with open("/proc/version", "r") as f:
            if "microsoft" in f.read().lower():
                # 获取宿主机 IP
                result = subprocess.check_output(
                    "ip route show | grep default", shell=True
                ).decode()
                host_ip = result.split()[2]
                # 默认端口 7890，但允许通过环境变量覆盖，避免硬编码死端口
                port = os.environ.get("WSL_PROXY_PORT", "7890")
                proxy_url = f"http://{host_ip}:{port}"
                return {
                    "http": proxy_url,
                    "https": proxy_url,
                }, f"WSL自动适配 ({proxy_url})"
    except Exception:
        pass

    return None, "直连模式 (无代理)"


# 初始化代理
PROXIES, PROXY_SOURCE = get_proxy_config()

print(f"========== 环境初始化 ==========")
print(f">>> GitHub Token: {'已配置' if GITHUB_TOKEN else '未配置 (易触发限流)'}")
print(f">>> 网络模式: {PROXY_SOURCE}")
if not PROXIES:
    print(">>> 提示: 如果下载失败，请设置环境变量 HTTP_PROXY 或检查 WSL 代理设置")
print(f"==============================")

if not os.path.exists(DATA_DIR):
    os.makedirs(DATA_DIR)


def get_headers():
    headers = {
        "User-Agent": get_random_ua(),
        "Accept-Language": "en-US,en;q=0.9",
    }
    if GITHUB_TOKEN:
        headers["Authorization"] = f"token {GITHUB_TOKEN}"
    return headers


def get_random_ua():
    uas = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
    ]
    return random.choice(uas)


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


# --- 3. 核心引擎 A: 爬虫 ---
def engine_scrape(period):
    print(f"[Engine-A] 正在爬取: {period}...")
    url = f"https://github.com/trending?since={period}"

    for attempt in range(1, 3):
        try:
            time.sleep(random.uniform(1, 2))

            # 使用全局计算好的 PROXIES，并关闭 SSL 验证 (verify=False)
            resp = requests.get(
                url, headers=get_headers(), proxies=PROXIES, timeout=15, verify=False
            )

            if resp.status_code != 200:
                raise Exception(f"HTTP {resp.status_code}")

            soup = BeautifulSoup(resp.text, "html.parser")
            articles = soup.select("article.Box-row")

            if not articles:
                raise Exception("页面为空 (可能是网络拦截)")

            repos = []
            for article in articles:
                try:
                    h2 = article.select_one("h2")
                    name = h2.select_one("a").get("href").strip("/")

                    p = article.select_one("p.col-9")
                    desc = p.text.strip() if p else "No description"

                    lang_tag = article.select_one("[itemprop='programmingLanguage']")
                    language = lang_tag.text.strip() if lang_tag else "Other"

                    total_stars = 0
                    for a in article.select("a.Link--muted"):
                        if "stargazers" in a.get("href", ""):
                            total_stars = parse_stars_text(a.text)

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
                print(f"  [SUCCESS] [Engine-A] {period} 成功 ({len(repos)}条)")
                return repos

        except Exception as e:
            err_msg = str(e)
            if "ProxyError" in err_msg:
                print(f"  [ERROR] [Engine-A] 代理连接失败，请检查端口 7890 是否开启")
                break
            print(f"  [WARN] [Engine-A] {period} 失败: {err_msg[:50]}...")

    return None


# --- 4. 核心引擎 B: API 保底 ---
def engine_api_fallback(period):
    print(f"[Engine-B] 启动 API 保底: {period}...")
    now = datetime.datetime.now()

    # 构造查询条件
    if period == "daily":
        since = (now - datetime.timedelta(days=1)).strftime("%Y-%m-%d")
        queries = [f"created:>{since}", f"pushed:>{since} stars:>500"]
    elif period == "weekly":
        since = (now - datetime.timedelta(days=7)).strftime("%Y-%m-%d")
        queries = [f"created:>{since}", f"pushed:>{since} stars:>1000"]
    elif period == "monthly":
        since = (now - datetime.timedelta(days=30)).strftime("%Y-%m-%d")
        queries = [f"created:>{since} stars:>2000"]
    elif period == "yearly":
        since = (now - datetime.timedelta(days=365)).strftime("%Y-%m-%d")
        queries = [f"created:>{since} stars:>5000"]
    else:
        queries = ["stars:>5000"]

    url = "https://api.github.com/search/repositories"
    all_repos = {}

    for q in queries:
        try:
            params = {"q": q, "sort": "stars", "order": "desc", "per_page": 15}

            resp = requests.get(
                url,
                params=params,
                headers=get_headers(),
                proxies=PROXIES,
                timeout=30,
                verify=False,
            )

            if resp.status_code == 200:
                items = resp.json().get("items", [])
                for item in items:
                    name = item.get("full_name")
                    if name and name not in all_repos:
                        stars_total = item.get("stargazers_count", 0)
                        all_repos[name] = {
                            "name": name,
                            "language": item.get("language") or "Other",
                            "stars_total": stars_total,
                            "stars_period": 0,
                            "url": item.get("html_url"),
                            "desc": item.get("description"),
                            "source": "api_fallback",
                        }
            else:
                if resp.status_code in [403, 429]:
                    print(f"  [LIMIT] [Engine-B] API 限流！请配置 GITHUB_TOKEN")
                else:
                    print(f"  [WARN] [Engine-B] API Error: {resp.status_code}")

        except Exception as e:
            print(f"  [WARN] [Engine-B] {period} 查询失败: {str(e)[:50]}")

    results = list(all_repos.values())
    results.sort(key=lambda x: x["stars_total"], reverse=True)

    if results:
        print(f"  [SUCCESS] [Engine-B] {period} 保底成功 ({len(results)}条)")
    else:
        print(f"  [ERROR] [Engine-B] {period} 获取失败")

    return results


# --- 5. 任务调度 ---
def collect_task(period):
    data = []
    if period in ["daily", "weekly", "monthly"]:
        data = engine_scrape(period)
        if not data:
            data = engine_api_fallback(period)
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
    print(f"  [Save] {period} 保存成功")


def main():
    print(f"========== 任务开始 {DATE_STR} ==========")
    start_time = time.time()
    periods = ["daily", "weekly", "monthly", "yearly", "all"]

    # 降低并发数，减少网络压力
    with ThreadPoolExecutor(max_workers=2) as executor:
        future_to_p = {executor.submit(collect_task, p): p for p in periods}
        for future in as_completed(future_to_p):
            period, data = future.result()
            save_json(data, period)

    print(f"========== 任务结束 (耗时 {time.time() - start_time:.2f}s) ==========")


if __name__ == "__main__":
    main()
