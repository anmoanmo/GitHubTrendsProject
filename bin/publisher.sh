#!/bin/bash

BASE_DIR=$(dirname $(dirname $(readlink -f "$0")))
DATE_STR=$(date +%F)
SUMMARY_FILE="$BASE_DIR/data/processed/summary_${DATE_STR}.json"
WEB_DIR="$BASE_DIR/web"
HTML_FILE="$WEB_DIR/index.html"
# 创建专门的下载目录
DOWNLOAD_DIR="$WEB_DIR/downloads"
mkdir -p "$DOWNLOAD_DIR"

if [ ! -f "$SUMMARY_FILE" ]; then
    echo "[ERROR] 摘要文件未找到，无法发布。"
    exit 1
fi

# 解析 JSON
TOP_NAME=$(python3 -c "import json; print(json.load(open('$SUMMARY_FILE'))['top_repo_name'])")
TOP_STARS=$(python3 -c "import json; print(json.load(open('$SUMMARY_FILE'))['top_repo_stars'])")
IMG_PATH=$(python3 -c "import json; print(json.load(open('$SUMMARY_FILE'))['img_path'])")
# 获取原始文件名
RAW_FILE_NAME=$(python3 -c "import json; print(json.load(open('$SUMMARY_FILE'))['raw_file_name'])")

# --- 关键修改：将原始数据复制到 Web 下载目录 ---
cp "$BASE_DIR/data/raw/$RAW_FILE_NAME" "$DOWNLOAD_DIR/"

# 生成 HTML 报告
cat > "$HTML_FILE" <<EOF
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <title>GitHub 每日趋势报告</title>
    <style>
        body { font-family: Arial, sans-serif; background-color: #f6f8fa; padding: 20px; }
        .container { max-width: 800px; margin: 0 auto; background: white; padding: 30px; border-radius: 8px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }
        h1 { color: #24292e; border-bottom: 1px solid #e1e4e8; padding-bottom: 10px; }
        .stat-card { background: #f1f8ff; border-left: 5px solid #0366d6; padding: 15px; margin: 20px 0; }
        .highlight { font-weight: bold; color: #0366d6; font-size: 1.2em; }
        img { max-width: 100%; margin-top: 20px; border: 1px solid #e1e4e8; }
        .download-section { margin-top: 20px; padding: 10px; background: #eef; border-radius: 4px; }
        footer { margin-top: 30px; color: #586069; font-size: 0.9em; text-align: center; }
        a { color: #0366d6; text-decoration: none; }
        a:hover { text-decoration: underline; }
    </style>
</head>
<body>
    <div class="container">
        <h1>GitHub 开源趋势日报: $DATE_STR</h1>
        
        <div class="stat-card">
            <p>🏆 <strong>今日榜首项目：</strong> <span class="highlight">$TOP_NAME</span></p>
            <p>⭐ <strong>今日获得 Star：</strong> $TOP_STARS</p>
        </div>

        <h3>📊 编程语言热度分布</h3>
        <img src="$IMG_PATH" alt="Trend Chart">
        
        <div class="download-section">
            <h3>💾 数据存档</h3>
            <p>您可以下载今日采集的原始 JSON 数据进行分析：</p>
            <a href="downloads/$RAW_FILE_NAME" download>⬇️ 点击下载今日数据 ($RAW_FILE_NAME)</a>
            <p><small>查看历史数据请访问 downloads/ 目录</small></p>
        </div>

        <footer>
            <p>System developed by Linux Course Project | Generated at $(date "+%H:%M:%S")</p>
        </footer>
    </div>
</body>
</html>
EOF

echo "[INFO] 网页报告已更新，包含下载链接: $HTML_FILE"