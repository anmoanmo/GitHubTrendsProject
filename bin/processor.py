import json
import os
import datetime
import matplotlib.pyplot as plt

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATE_STR = datetime.datetime.now().strftime("%Y-%m-%d")

# 定义各级目录
RAW_DIR = os.path.join(BASE_DIR, "data/raw")
ARCHIVE_DIR = os.path.join(BASE_DIR, "data/archive")
PROCESSED_DIR = os.path.join(BASE_DIR, "data/processed")
WEB_STATIC_DIR = os.path.join(BASE_DIR, "web/static")

# 确保目录存在
for d in [ARCHIVE_DIR, PROCESSED_DIR, WEB_STATIC_DIR]:
    if not os.path.exists(d):
        os.makedirs(d)

RAW_FILE = os.path.join(RAW_DIR, f"github_trending_{DATE_STR}.json")
HISTORY_FILE = os.path.join(ARCHIVE_DIR, "history_all.json")
IMG_OUTPUT = os.path.join(WEB_STATIC_DIR, f"trend_{DATE_STR}.png")
SUMMARY_FILE = os.path.join(PROCESSED_DIR, f"summary_{DATE_STR}.json")


def process_data():
    if not os.path.exists(RAW_FILE):
        print(f"[ERROR] 今日原始数据不存在: {RAW_FILE}")
        exit(1)

    with open(RAW_FILE, "r", encoding="utf-8") as f:
        today_data = json.load(f)

    if not today_data:
        print("[ERROR] 数据为空，跳过处理")
        exit(1)

    # --- 任务1：追加合并历史数据 ---
    history_data = []
    if os.path.exists(HISTORY_FILE):
        try:
            with open(HISTORY_FILE, "r", encoding="utf-8") as f:
                history_data = json.load(f)
        except json.JSONDecodeError:
            print("[WARN] 历史数据损坏，将重新创建")
            history_data = []

    history_data.extend(today_data)
    with open(HISTORY_FILE, "w", encoding="utf-8") as f:
        json.dump(history_data, f, ensure_ascii=False)

    # --- 任务2：分析语言热度 ---
    lang_counts = {}
    top_repo = today_data[0]

    for repo in today_data:
        lang = repo["language"]
        lang_counts[lang] = lang_counts.get(lang, 0) + 1
        if repo["stars"] > top_repo["stars"]:
            top_repo = repo

    # --- 任务3：生成可视化图表 ---
    plt.figure(figsize=(10, 6))
    # 按照数量排序，让图表更好看
    sorted_langs = dict(
        sorted(lang_counts.items(), key=lambda item: item[1], reverse=True)[:10]
    )  # 只取前10
    plt.bar(sorted_langs.keys(), sorted_langs.values(), color="skyblue")
    plt.title(f"GitHub Top 10 Trending Languages ({DATE_STR})")
    plt.xticks(rotation=45)
    plt.tight_layout()
    plt.savefig(IMG_OUTPUT)

    # --- 任务4：输出简报数据 ---
    summary = {
        "date": DATE_STR,
        "top_repo_name": top_repo["name"],
        "top_repo_stars": top_repo["stars"],
        "top_lang": max(lang_counts, key=lang_counts.get),
        "img_path": f"static/trend_{DATE_STR}.png",
        "raw_file_name": f"github_trending_{DATE_STR}.json",  # 传递文件名给发布模块
    }
    with open(SUMMARY_FILE, "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False)

    print(f"[INFO] 处理完成，图表已生成: {IMG_OUTPUT}")


if __name__ == "__main__":
    process_data()
