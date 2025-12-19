import json
import os
import datetime
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATE_STR = datetime.datetime.now().strftime("%Y-%m-%d")
RAW_DIR = os.path.join(BASE_DIR, "data/raw")
PROCESSED_DIR = os.path.join(BASE_DIR, "data/processed")
STATIC_DIR = os.path.join(BASE_DIR, "web/static")

for d in [PROCESSED_DIR, STATIC_DIR]:
    if not os.path.exists(d):
        os.makedirs(d)

SUMMARY_FILE = os.path.join(PROCESSED_DIR, f"summary_all_{DATE_STR}.json")


def process_single_period(period):
    filename = f"github_{period}_{DATE_STR}.json"
    filepath = os.path.join(RAW_DIR, filename)

    if not os.path.exists(filepath):
        return None

    with open(filepath, "r", encoding="utf-8") as f:
        data = json.load(f)

    if not data:
        return None

    data.sort(key=lambda x: x["stars"], reverse=True)
    top_repo = data[0]

    lang_counts = {}
    for repo in data:
        lang = repo["language"]
        if lang and lang != "Other":
            lang_counts[lang] = lang_counts.get(lang, 0) + 1

    top_lang = max(lang_counts, key=lang_counts.get) if lang_counts else "N/A"

    img_name = f"trend_{period}_{DATE_STR}.png"
    img_path = os.path.join(STATIC_DIR, img_name)

    plt.figure(figsize=(8, 5))
    sorted_langs = dict(
        sorted(lang_counts.items(), key=lambda item: item[1], reverse=True)[:8]
    )
    plt.bar(sorted_langs.keys(), sorted_langs.values(), color="#6c5ce7")
    plt.title(f"GitHub Languages ({period.capitalize()})")
    plt.xticks(rotation=30)
    plt.tight_layout()
    plt.savefig(img_path)
    plt.close()

    return {
        "period": period,
        "top_repo_name": top_repo["name"],
        "top_repo_stars": top_repo["stars"],
        "top_repo_url": top_repo.get("url", "#"),  # 新增：传递 URL
        "top_lang": top_lang,
        "img_filename": img_name,
        "repos": data[:10],
    }


def run_processor():
    periods = ["daily", "weekly", "monthly", "yearly", "all"]
    final_summary = {
        "date": DATE_STR,
        "update_time": datetime.datetime.now().strftime("%H:%M:%S"),
        "data": {},
    }

    print(">>> 开始处理数据...")
    for p in periods:
        res = process_single_period(p)
        final_summary["data"][p] = res

    with open(SUMMARY_FILE, "w", encoding="utf-8") as f:
        json.dump(final_summary, f, ensure_ascii=False, indent=4)
    print(f"[SUCCESS] 汇总数据已写入: {SUMMARY_FILE}")


if __name__ == "__main__":
    run_processor()
