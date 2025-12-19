#!/bin/bash

# 获取脚本所在目录的上一级目录作为项目根目录
PROJECT_HOME=$(dirname $(dirname "$(readlink -f "$0")"))
LOG_DIR="$PROJECT_HOME/logs"
LOG_FILE="$LOG_DIR/project_run.log"

# 确保日志目录存在
mkdir -p "$LOG_DIR"

echo "========== 任务启动: $(date) ==========" >> "$LOG_FILE"

# 1. 执行采集 (注意：这里去掉了 /usr/bin/ 前缀)
echo ">>> [1/2] 正在执行采集..." >> "$LOG_FILE"
python3 "$PROJECT_HOME/bin/collector.py" >> "$LOG_FILE" 2>&1
if [ $? -ne 0 ]; then
    echo "[ERROR] 采集脚本执行失败，请查看日志。" >> "$LOG_FILE"
    exit 1
fi

# 2. 执行处理 (注意：这里去掉了 /usr/bin/ 前缀)
echo ">>> [2/2] 正在执行处理..." >> "$LOG_FILE"
python3 "$PROJECT_HOME/bin/processor.py" >> "$LOG_FILE" 2>&1
if [ $? -ne 0 ]; then
    echo "[ERROR] 处理脚本执行失败，请查看日志。" >> "$LOG_FILE"
    exit 1
fi

echo "========== 任务结束: $(date) ==========" >> "$LOG_FILE"
echo "" >> "$LOG_FILE"