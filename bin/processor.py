import json
import os
import datetime
import threading
import requests
from concurrent.futures import ThreadPoolExecutor
from deep_translator import GoogleTranslator

# --- 用户配置区域 ---
PROXY_URL = os.environ.get("HTTP_PROXY") or os.environ.get("HTTPS_PROXY")
# PROXY_URL = "http://127.0.0.1:7890"

# --- 路径配置 ---
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW_DIR = os.path.join(BASE_DIR, "data/raw")
PROCESSED_DIR = os.path.join(BASE_DIR, "data/processed")
CACHE_FILE = os.path.join(BASE_DIR, "data", "translation_cache.json")
DATE_STR = datetime.datetime.now().strftime("%Y-%m-%d")
SUMMARY_FILE = os.path.join(PROCESSED_DIR, f"summary_all_{DATE_STR}.json")

if not os.path.exists(PROCESSED_DIR):
    os.makedirs(PROCESSED_DIR)

# --- 缓存管理 ---
if os.path.exists(CACHE_FILE):
    with open(CACHE_FILE, "r", encoding="utf-8") as f:
        try:
            TRANS_CACHE = json.load(f)
        except:
            TRANS_CACHE = {}
else:
    TRANS_CACHE = {}

cache_lock = threading.Lock()
ENABLE_TRANSLATION = True


def check_google_access():
    global ENABLE_TRANSLATION
    try:
        proxies = {"https": PROXY_URL} if PROXY_URL else None
        requests.get("https://translate.googleapis.com", proxies=proxies, timeout=2)
        ENABLE_TRANSLATION = True
    except:
        ENABLE_TRANSLATION = False


def save_cache():
    try:
        with open(CACHE_FILE, "w", encoding="utf-8") as f:
            json.dump(TRANS_CACHE, f, ensure_ascii=False, indent=2)
    except:
        pass


def translate_worker(text):
    if not ENABLE_TRANSLATION:
        return text
    # 增加对 None 的防护
    if not text or not isinstance(text, str) or len(text) < 2:
        return text
    if any("\u4e00" <= char <= "\u9fff" for char in text[:5]):
        return text
    if text in TRANS_CACHE:
        return TRANS_CACHE[text]

    try:
        if PROXY_URL:
            os.environ["https_proxy"] = PROXY_URL
            os.environ["http_proxy"] = PROXY_URL

        res = GoogleTranslator(source="auto", target="zh-CN").translate(text)

        if res:
            with cache_lock:
                TRANS_CACHE[text] = res
            return res
        return text
    except Exception as e:
        return text


def process_period(period):
    filename = f"github_{period}_{DATE_STR}.json"
    filepath = os.path.join(RAW_DIR, filename)

    if not os.path.exists(filepath):
        return None

    with open(filepath, "r", encoding="utf-8") as f:
        data = json.load(f)
    if not data:
        return None

    # 排序逻辑
    if period in ["daily", "weekly", "monthly"]:
        data.sort(
            key=lambda x: (x.get("stars_period", 0), x.get("stars_total", 0)),
            reverse=True,
        )
    else:
        data.sort(key=lambda x: x.get("stars_total", 0), reverse=True)

    top_repos = data[:15]

    # --- 修复核心：确保 desc 不为 None ---
    # 使用 (repo.get("desc") or "") 强制转为字符串，防止 .get 返回 None
    desc_list = [(repo.get("desc") or "") for repo in top_repos]

    if ENABLE_TRANSLATION:
        with ThreadPoolExecutor(max_workers=5) as executor:
            translated_descs = list(executor.map(translate_worker, desc_list))
    else:
        translated_descs = desc_list

    for i, repo in enumerate(top_repos):
        # 再次兜底，确保入库的肯定是字符串
        repo["desc"] = translated_descs[i] or "No description provided."

        if "stars_total" not in repo:
            repo["stars_total"] = repo.get("stars", 0)
        if "stars_period" not in repo:
            repo["stars_period"] = 0

        # 简单判断新项目逻辑
        repo["is_new"] = (repo.get("stars_total") == repo.get("stars_period")) and (
            repo.get("stars_period") > 0
        )

    # 统计语言
    lang_counts = {}
    for repo in data:
        l = repo.get("language", "Other")
        if l and l != "Other":
            lang_counts[l] = lang_counts.get(l, 0) + 1

    chart_data = [{"name": k, "value": v} for k, v in lang_counts.items()]
    chart_data.sort(key=lambda x: x["value"], reverse=True)

    return {
        "period": period,
        "top_repo": top_repos[0] if top_repos else {},
        "top_lang": chart_data[0]["name"] if chart_data else "N/A",
        "chart_data": chart_data[:10],
        "repos": top_repos,
    }


def run_processor():
    check_google_access()

    start_time = datetime.datetime.now()
    final_summary = {
        "date": DATE_STR,
        "update_time": datetime.datetime.now().strftime("%H:%M:%S"),
        "data": {},
    }

    periods = ["daily", "weekly", "monthly", "yearly", "all"]

    print(">>> [Processor] 开始处理数据...")
    for p in periods:
        res = process_period(p)
        if res:
            final_summary["data"][p] = res

    with open(SUMMARY_FILE, "w", encoding="utf-8") as f:
        json.dump(final_summary, f, ensure_ascii=False, indent=4)

    if ENABLE_TRANSLATION:
        save_cache()

    print(
        f"[SUCCESS] 处理完成，耗时: {(datetime.datetime.now() - start_time).total_seconds():.2f}s"
    )


if __name__ == "__main__":
    run_processor()
