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
                data = json.load(f)
        except:
            pass

    return render_template("index.html", summary=data)


@app.route("/run_task", methods=["POST"])
def run_task():
    script_path = os.path.join(BIN_DIR, "main.sh")
    try:
        # 运行时间会变长，因为要爬5次
        result = subprocess.run(
            ["/bin/bash", script_path], capture_output=True, text=True
        )
        if result.returncode == 0:
            return jsonify({"status": "success", "message": "全量数据采集完成！"})
        else:
            return jsonify({"status": "error", "message": f"脚本出错: {result.stderr}"})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
