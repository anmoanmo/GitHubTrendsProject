from flask import Flask, render_template, jsonify, request
import os
import json
import datetime
import subprocess
import glob
import atexit
from apscheduler.schedulers.background import BackgroundScheduler

app = Flask(__name__)

# --- 配置路径 ---
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "data/processed")
BIN_DIR = os.path.join(BASE_DIR, "bin")


# --- 定时任务逻辑 ---
def auto_run_task():
    """定时执行采集脚本"""
    print(f"[{datetime.datetime.now()}] ⏰ 触发定时采集任务...")
    script_path = os.path.join(BIN_DIR, "main.sh")
    try:
        # 设置超时时间为 300秒 (5分钟)
        subprocess.run(
            ["/bin/bash", script_path], capture_output=True, text=True, timeout=300
        )
    except Exception as e:
        print(f"[ERROR] 定时任务执行失败: {e}")


# 初始化调度器: 每 4 小时执行一次
scheduler = BackgroundScheduler()
scheduler.add_job(func=auto_run_task, trigger="interval", hours=4)
scheduler.start()
atexit.register(lambda: scheduler.shutdown())


# --- 辅助函数 ---
def get_available_dates():
    """获取所有已存在的历史数据日期列表"""
    files = glob.glob(os.path.join(DATA_DIR, "summary_all_*.json"))
    dates = []
    for f in files:
        try:
            basename = os.path.basename(f)
            # 提取 YYYY-MM-DD
            date_part = basename.replace("summary_all_", "").replace(".json", "")
            dates.append(date_part)
        except:
            continue
    return sorted(dates, reverse=True)


# --- 路由定义 ---
@app.route("/")
def index():
    # 1. 获取日期列表
    available_dates = get_available_dates()

    # 2. 确定当前显示的日期 (URL参数优先 > 今天 > 最近有一天)
    today_str = datetime.datetime.now().strftime("%Y-%m-%d")
    selected_date = request.args.get("date", today_str)

    target_file = os.path.join(DATA_DIR, f"summary_all_{selected_date}.json")

    # 如果请求的日期没数据，且有历史数据，回退到最近的一天
    if not os.path.exists(target_file) and available_dates:
        selected_date = available_dates[0]
        target_file = os.path.join(DATA_DIR, f"summary_all_{selected_date}.json")

    data = None
    if os.path.exists(target_file):
        try:
            with open(target_file, "r", encoding="utf-8") as f:
                loaded_data = json.load(f)
            # 简单校验数据结构
            if loaded_data and "data" in loaded_data:
                # 检查是否包含 v1.0 以上的结构 (含 top_repo 对象)
                first_key = next(iter(loaded_data["data"]))
                if "top_repo" in loaded_data["data"][first_key]:
                    data = loaded_data
        except Exception as e:
            print(f"[ERROR] 读取数据文件失败: {e}")

    return render_template(
        "index.html",
        summary=data,
        available_dates=available_dates,
        current_date=selected_date,
    )


@app.route("/repo_history")
def repo_history():
    """API: 获取指定项目的过去30天趋势"""
    repo_name = request.args.get("name")
    if not repo_name:
        return jsonify([])

    dates = get_available_dates()
    history = []

    # 只看最近 30 天的数据
    target_dates = sorted(dates)[-30:]

    for date_str in target_dates:
        file_path = os.path.join(DATA_DIR, f"summary_all_{date_str}.json")
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                d = json.load(f)
                # 在 daily 榜单中查找该项目
                daily_repos = d.get("data", {}).get("daily", {}).get("repos", [])

                # 查找匹配的项目
                item = next((r for r in daily_repos if r["name"] == repo_name), None)
                if item:
                    history.append(
                        {
                            "date": date_str,
                            "stars": item.get("stars_total", 0),
                            "increase": item.get("stars_period", 0),
                        }
                    )
                # 如果没上榜，这里暂时不填充 0，因为不知道实际数据
        except:
            continue

    return jsonify(history)


@app.route("/run_task", methods=["POST"])
def run_task():
    """手动触发采集"""
    script_path = os.path.join(BIN_DIR, "main.sh")
    try:
        result = subprocess.run(
            ["/bin/bash", script_path], capture_output=True, text=True, timeout=300
        )
        if result.returncode == 0:
            return jsonify({"status": "success", "message": "任务已在后台执行完成！"})
        else:
            return jsonify({"status": "error", "message": f"脚本错误: {result.stderr}"})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
