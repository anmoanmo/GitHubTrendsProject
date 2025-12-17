import json
import os
import datetime
import matplotlib.pyplot as plt

# 路径配置
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATE_STR = datetime.datetime.now().strftime("%Y-%m-%d")
RAW_FILE = os.path.join(BASE_DIR, f"data/raw/github_trending_{DATE_STR}.json")
HISTORY_FILE = os.path.join(BASE_DIR, "data/archive/history_all.json")
IMG_OUTPUT = os.path.join(BASE_DIR, f"web/static/trend_{DATE_STR}.png")
SUMMARY_FILE = os.path.join(BASE_DIR, f"data/processed/summary_{DATE_STR}.json")


def process_data():
    if not os.path.exists(RAW_FILE):
        print("[ERROR] 今日原始数据不存在")
        exit(1)

    with open(RAW_FILE, "r", encoding="utf-8") as f:
        today_data = json.load(f)

    # --- 任务1：追加合并文件 (符合文档关于合并文件的要求) ---
    history_data = []
    if os.path.exists(HISTORY_FILE):
        with open(HISTORY_FILE, "r", encoding="utf-8") as f:
            try:
                history_data = json.load(f)
            except:
                pass

    history_data.extend(today_data)
    with open(HISTORY_FILE, "w", encoding="utf-8") as f:
        json.dump(history_data, f, ensure_ascii=False)

    # --- 任务2：分析语言热度 ---
    lang_counts = {}
    top_repo = today_data[0]  # 假设第一个是Star最高的

    for repo in today_data:
        lang = repo["language"]
        lang_counts[lang] = lang_counts.get(lang, 0) + 1
        if repo["stars"] > top_repo["stars"]:
            top_repo = repo

    # --- 任务3：生成可视化图表 ---
    plt.figure(figsize=(10, 6))
    plt.bar(lang_counts.keys(), lang_counts.values(), color="skyblue")
    plt.title(f"GitHub Trending Languages ({DATE_STR})")
    plt.xticks(rotation=45)
    plt.tight_layout()
    plt.savefig(IMG_OUTPUT)  # 保存图片供Web使用

    # --- 任务4：输出简报数据供Shell读取 ---
    summary = {
        "date": DATE_STR,
        "top_repo_name": top_repo["name"],
        "top_repo_stars": top_repo["stars"],
        "top_lang": max(lang_counts, key=lang_counts.get),
        "img_path": f"static/trend_{DATE_STR}.png",
    }
    with open(SUMMARY_FILE, "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False)

    print(f"[INFO] 处理完成，图表已生成: {IMG_OUTPUT}")


if __name__ == "__main__":
    process_data()
