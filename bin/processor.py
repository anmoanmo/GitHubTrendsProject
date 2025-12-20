import json
import os
import datetime
import threading
import requests
from concurrent.futures import ThreadPoolExecutor
from deep_translator import GoogleTranslator

# --- 用户配置区域 ---
# 如果你有代理（例如 Clash/v2ray），请在这里填入端口 (http://127.0.0.1:7890)
# 如果没有代理，保持为 None，程序会自动检测并跳过翻译
PROXY_URL = None
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
ENABLE_TRANSLATION = True  # 默认开启，稍后检测


def check_google_access():
    """检测是否能连接翻译服务"""
    global ENABLE_TRANSLATION
    print(">>> [Self-Check] 正在检测翻译服务连通性...")
    try:
        proxies = {"https": PROXY_URL} if PROXY_URL else None
        # 尝试连接 Google 翻译 API 域名，2秒超时
        requests.get("https://translate.googleapis.com", proxies=proxies, timeout=2)
        print(">>> [Self-Check] ✅ Google 翻译服务可用")
        ENABLE_TRANSLATION = True
    except:
        print(">>> [Self-Check] ❌ 无法连接 Google 翻译 (国内网络需配置代理)")
        print(">>> [Self-Check] ⚠️ 已自动关闭翻译功能，以防止程序卡死")
        ENABLE_TRANSLATION = False


def save_cache():
    try:
        with open(CACHE_FILE, "w", encoding="utf-8") as f:
            json.dump(TRANS_CACHE, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"[WARN] 缓存保存失败: {e}")


def translate_worker(text):
    """单个翻译任务"""
    if not ENABLE_TRANSLATION:
        return text
    if not text or len(text) < 2:
        return text
    if any("\u4e00" <= char <= "\u9fff" for char in text[:5]):
        return text
    if text in TRANS_CACHE:
        return TRANS_CACHE[text]

    try:
        # 这里的 proxies 并不是 deep_translator 的标准参数，它依赖环境变量
        # 如果需要代理，通常需要设置 os.environ
        if PROXY_URL:
            os.environ["https_proxy"] = PROXY_URL
            os.environ["http_proxy"] = PROXY_URL

        res = GoogleTranslator(source="auto", target="zh-CN").translate(text)

        # 简单的验证，防止空结果
        if res:
            with cache_lock:
                TRANS_CACHE[text] = res
            return res
        return text
    except Exception as e:
        # 出错就不翻译，直接返回原文
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

    # 排序
    if period in ["daily", "weekly", "monthly"]:
        data.sort(
            key=lambda x: x.get("stars_period", 0) or x.get("stars_total", 0),
            reverse=True,
        )
    else:
        data.sort(key=lambda x: x.get("stars_total", 0), reverse=True)

    top_repos = data[:15]

    # --- 并发翻译 (仅当开启时) ---
    if ENABLE_TRANSLATION:
        desc_list = [repo.get("desc", "") for repo in top_repos]
        # 减少并发数，避免触发 429 Too Many Requests
        with ThreadPoolExecutor(max_workers=5) as executor:
            translated_descs = list(executor.map(translate_worker, desc_list))

        for i, repo in enumerate(top_repos):
            repo["desc"] = translated_descs[i]
            if "stars_total" not in repo:
                repo["stars_total"] = repo.get("stars", 0)
            if "stars_period" not in repo:
                repo["stars_period"] = 0
    else:
        # 如果关闭翻译，也要补全字段防止前端报错
        for repo in top_repos:
            if "stars_total" not in repo:
                repo["stars_total"] = repo.get("stars", 0)
            if "stars_period" not in repo:
                repo["stars_period"] = 0

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
    # 1. 检测网络
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
