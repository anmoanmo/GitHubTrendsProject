#!/bin/bash

# 获取脚本所在目录的上一级目录作为项目根目录
PROJECT_HOME=$(dirname $(dirname "$(readlink -f "$0")"))
LOG_DIR="$PROJECT_HOME/logs"
LOG_FILE="$LOG_DIR/project_run.log"

# 确保日志目录存在
mkdir -p "$LOG_DIR"

echo "========== 全流程任务启动: $(date) ==========" >> "$LOG_FILE"

# --- 模块 1: 数据收集 (Python爬虫/API) ---
echo ">>> [1/4] 正在执行数据收集 (Collector)..." >> "$LOG_FILE"
python3 "$PROJECT_HOME/bin/collector.py" >> "$LOG_FILE" 2>&1
if [ $? -ne 0 ]; then
    echo "[ERROR] 采集脚本执行失败，请查看日志。" >> "$LOG_FILE"
    exit 1
fi

# ... (数据收集代码) ...

# --- [新增] 模块 1.5: 数据校验 (Shell模块拓展) ---
echo ">>> [Check] 正在执行数据校验..." >> "$LOG_FILE"
/bin/bash "$PROJECT_HOME/bin/validator.sh" >> "$LOG_FILE" 2>&1
if [ $? -ne 0 ]; then
    echo "[CRITICAL] 数据校验未通过，终止后续流程！" >> "$LOG_FILE"
    exit 1
fi

# ... (数据处理代码) ...

# --- 模块 2.1: 数据清洗与翻译 (Python处理 - 高级功能) ---
echo ">>> [2/4] 正在执行数据清洗 (Processor - Python)..." >> "$LOG_FILE"
python3 "$PROJECT_HOME/bin/processor.py" >> "$LOG_FILE" 2>&1
if [ $? -ne 0 ]; then
    echo "[ERROR] Python处理脚本执行失败，请查看日志。" >> "$LOG_FILE"
    exit 1
fi

# --- 模块 2.2: 数据归档 (Shell处理 - 对应文档加分项) ---
# 新增步骤：调用 storage.sh 完成“合并存储”要求
echo ">>> [3/4] 正在执行数据归档 (Storage - Shell)..." >> "$LOG_FILE"
/bin/bash "$PROJECT_HOME/bin/storage.sh" >> "$LOG_FILE" 2>&1
if [ $? -ne 0 ]; then
    echo "[WARNING] Shell归档脚本执行异常，但不影响主流程。" >> "$LOG_FILE"
fi

# --- 模块 3: 结果发布 (Shell发布) ---
# 新增步骤：调用 publisher.sh 完成“发布至Web目录”要求
echo ">>> [4/4] 正在执行结果发布 (Publisher)..." >> "$LOG_FILE"
/bin/bash "$PROJECT_HOME/bin/publisher.sh" >> "$LOG_FILE" 2>&1
if [ $? -ne 0 ]; then
    echo "[ERROR] 发布脚本执行失败，请查看日志。" >> "$LOG_FILE"
    exit 1
fi

echo "========== 全流程任务结束: $(date) ==========" >> "$LOG_FILE"
echo "" >> "$LOG_FILE"