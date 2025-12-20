from flask import Flask, render_template, jsonify
import os
import json
import datetime
import subprocess

app = Flask(__name__)

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "data/processed")
BIN_DIR = os.path.join(BASE_DIR, "bin")


@app.route("/")
def index():
    date_str = datetime.datetime.now().strftime("%Y-%m-%d")
    summary_file = os.path.join(DATA_DIR, f"summary_all_{date_str}.json")

    data = None
    if os.path.exists(summary_file):
        try:
            with open(summary_file, "r", encoding="utf-8") as f:
                loaded_data = json.load(f)

            # --- 关键修复：数据格式校验 ---
            # 检查 daily 数据是否存在，且是否包含新的 'top_repo' 字段
            # 如果是旧格式 (含有 top_repo_name 但没有 top_repo 对象)，则视为无效
            if loaded_data and "data" in loaded_data:
                first_key = next(iter(loaded_data["data"]))
                if "top_repo" in loaded_data["data"][first_key]:
                    data = loaded_data
                else:
                    print("[WARN] 检测到旧版数据格式，已忽略，等待重新采集。")
        except Exception as e:
            print(f"[ERROR] 读取数据出错: {e}")

    return render_template("index.html", summary=data)


@app.route("/run_task", methods=["POST"])
def run_task():
    script_path = os.path.join(BIN_DIR, "main.sh")
    try:
        # 设置超时时间，避免前端等太久
        result = subprocess.run(
            ["/bin/bash", script_path],
            capture_output=True,
            text=True,
            timeout=180,  # 增加超时时间因为包含了翻译
        )
        if result.returncode == 0:
            return jsonify({"status": "success", "message": "采集与翻译完成！"})
        else:
            return jsonify({"status": "error", "message": f"脚本错误: {result.stderr}"})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
