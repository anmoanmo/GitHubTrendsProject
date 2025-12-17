#!/bin/bash

# 获取脚本所在目录的上一级目录作为项目根目录
PROJECT_HOME=$(dirname $(dirname $(readlink -f "$0")))
LOG_FILE="$PROJECT_HOME/logs/project_run.log"

echo "========== 任务开始: $(date) ==========" >> "$LOG_FILE"

# 1. 执行采集
echo ">>> 正在执行采集..." >> "$LOG_FILE"
/usr/bin/python3 "$PROJECT_HOME/bin/collector.py" >> "$LOG_FILE" 2>&1

# 2. 执行处理
echo ">>> 正在执行处理..." >> "$LOG_FILE"
/usr/bin/python3 "$PROJECT_HOME/bin/processor.py" >> "$LOG_FILE" 2>&1

# 3. 执行发布
echo ">>> 正在生成网页..." >> "$LOG_FILE"
/bin/bash "$PROJECT_HOME/bin/publisher.sh" >> "$LOG_FILE" 2>&1

# 4. 启动/检查 Web 服务器 (简单的部署要求) 
# 如果端口 8000 没有被占用，则启动 python http server
if ! lsof -i:8000 > /dev/null; then
    echo ">>> 启动 Web 服务器..." >> "$LOG_FILE"
    cd "$PROJECT_HOME/web"
    nohup python3 -m http.server 8000 >> "$PROJECT_HOME/logs/web_server.log" 2>&1 &
fi

echo "========== 任务结束: $(date) ==========" >> "$LOG_FILE"
echo "" >> "$LOG_FILE"