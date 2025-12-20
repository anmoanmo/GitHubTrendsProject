from flask import Flask, render_template, jsonify, request
import os
import json
import datetime
import subprocess
import glob
import atexit
from apscheduler.schedulers.background import BackgroundScheduler

app = Flask(__name__)

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "data/processed")
BIN_DIR = os.path.join(BASE_DIR, "bin")


def auto_run_task():
    script_path = os.path.join(BIN_DIR, "main.sh")
    try:
        subprocess.run(
            ["/bin/bash", script_path], capture_output=True, text=True, timeout=300
        )
    except Exception as e:
        print(f"[ERROR] 定时任务: {e}")


scheduler = BackgroundScheduler()
scheduler.add_job(func=auto_run_task, trigger="interval", hours=4)
scheduler.start()
atexit.register(lambda: scheduler.shutdown())


def get_available_dates():
    files = glob.glob(os.path.join(DATA_DIR, "summary_all_*.json"))
    dates = []
    for f in files:
        try:
            basename = os.path.basename(f)
            dates.append(basename.replace("summary_all_", "").replace(".json", ""))
        except:
            continue
    return sorted(dates, reverse=True)


@app.route("/")
def index():
    available_dates = get_available_dates()
    today_str = datetime.datetime.now().strftime("%Y-%m-%d")
    selected_date = request.args.get("date", today_str)

    target_file = os.path.join(DATA_DIR, f"summary_all_{selected_date}.json")
    if not os.path.exists(target_file) and available_dates:
        selected_date = available_dates[0]
        target_file = os.path.join(DATA_DIR, f"summary_all_{selected_date}.json")

    data = None
    if os.path.exists(target_file):
        try:
            with open(target_file, "r", encoding="utf-8") as f:
                loaded_data = json.load(f)

            # --- 修复：健壮的数据校验，防止 NoneType Error ---
            if (
                isinstance(loaded_data, dict)
                and "data" in loaded_data
                and isinstance(loaded_data["data"], dict)
            ):
                # 确保 data 不为空
                if loaded_data["data"]:
                    data = loaded_data
                else:
                    print("[WARN] 数据文件中的 data 字段为空")
            else:
                print("[WARN] 数据文件结构不符合预期")

        except Exception as e:
            print(f"[ERROR] 读取失败: {e}")

    return render_template(
        "index.html",
        summary=data,
        available_dates=available_dates,
        current_date=selected_date,
    )


@app.route("/repo_history")
def repo_history():
    repo_name = request.args.get("name")
    if not repo_name:
        return jsonify([])
    dates = get_available_dates()
    target_dates = sorted(dates)[-30:]
    history = []

    for date_str in target_dates:
        file_path = os.path.join(DATA_DIR, f"summary_all_{date_str}.json")
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                d = json.load(f)
                repos = d.get("data", {}).get("daily", {}).get("repos", [])
                item = next((r for r in repos if r["name"] == repo_name), None)
                if item:
                    history.append(
                        {"date": date_str, "stars": item.get("stars_total", 0)}
                    )
        except:
            continue
    return jsonify(history)


@app.route("/run_task", methods=["POST"])
def run_task():
    script_path = os.path.join(BIN_DIR, "main.sh")
    try:
        subprocess.run(
            ["/bin/bash", script_path], capture_output=True, text=True, timeout=300
        )
        return jsonify({"status": "success"})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=False)
