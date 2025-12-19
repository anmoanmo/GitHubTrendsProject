#!/bin/bash

# 解决 crontab 环境变量问题
export PATH=/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin

PROJECT_HOME=$(dirname $(dirname $(readlink -f "$0")))
# 确保 logs 目录存在
mkdir -p "$PROJECT_HOME/logs"
LOG_FILE="$PROJECT_HOME/logs/project_run.log"

echo "========== 任务开始: $(date) ==========" >> "$LOG_FILE"

# 1. 执行采集
echo ">>> [1/3] 正在执行采集..." >> "$LOG_FILE"
python3 "$PROJECT_HOME/bin/collector.py" >> "$LOG_FILE" 2>&1
if [ $? -ne 0 ]; then
    echo "[ERROR] 采集失败，终止后续步骤" >> "$LOG_FILE"
    exit 1
fi

# 2. 执行处理
echo ">>> [2/3] 正在执行处理..." >> "$LOG_FILE"
python3 "$PROJECT_HOME/bin/processor.py" >> "$LOG_FILE" 2>&1

# 3. 执行发布
echo ">>> [3/3] 正在生成网页..." >> "$LOG_FILE"
bash "$PROJECT_HOME/bin/publisher.sh" >> "$LOG_FILE" 2>&1

# 4. 检查 Web 服务器
# 使用 pgrep 检查更简洁，或者继续使用 lsof
if ! lsof -i:8000 > /dev/null; then
    echo ">>> 启动 Web 服务器..." >> "$LOG_FILE"
    cd "$PROJECT_HOME/web"
    # 使用 nohup 后台运行
    nohup python3 -m http.server 8000 >> "$PROJECT_HOME/logs/web_server.log" 2>&1 &
fi

echo "========== 任务结束: $(date) ==========" >> "$LOG_FILE"
echo "" >> "$LOG_FILE"