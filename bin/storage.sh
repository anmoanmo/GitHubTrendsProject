#!/bin/bash

# ========================================================
# 模块名称：数据存储与归档模块 
# 功能描述：满足文档“数据存储和处理”要求 -> “每日追加合并为单文件”
# 优势说明：采用 Shell 脚本原生命令 (cat, grep, date) 实现
# ========================================================

# 1. 路径定义
BASE_DIR=$(dirname $(dirname $(readlink -f "$0")))
RAW_DATA_DIR="$BASE_DIR/data/raw"
ARCHIVE_DIR="$BASE_DIR/data/archive"
LOG_DIR="$BASE_DIR/logs"
DATE_STR=$(date +%F)

# 确保目录存在
mkdir -p "$ARCHIVE_DIR"
mkdir -p "$LOG_DIR"

# 2. 定义归档文件 (所有历史数据合并在此)
MASTER_FILE="$ARCHIVE_DIR/github_trend_master.txt"
DAILY_SOURCE_FILE="$RAW_DATA_DIR/github_daily_${DATE_STR}.json"
LOG_FILE="$LOG_DIR/storage_run.log"

log_msg() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1"
}

# 3. 执行归档逻辑
{
    log_msg "启动 Shell 数据归档任务..."
    
    if [ -f "$DAILY_SOURCE_FILE" ]; then
        # 写入分隔符和日期头 (文档要求：文件名含日期信息或特殊字符串分割)
        echo "" >> "$MASTER_FILE"
        echo "==========================================" >> "$MASTER_FILE"
        echo "ARCHIVE_DATE: $DATE_STR" >> "$MASTER_FILE"
        echo "SOURCE_FILE: $(basename "$DAILY_SOURCE_FILE")" >> "$MASTER_FILE"
        echo "==========================================" >> "$MASTER_FILE"
        
        # 追加文件内容
        cat "$DAILY_SOURCE_FILE" >> "$MASTER_FILE"
        
        log_msg "✅ 成功将今日数据追加至归档文件: $MASTER_FILE"
        
        # 额外加分点：简单的 Shell 数据统计 (如统计今日项目数)
        # 使用 grep -c 统计 "name": 出现的次数作为项目数估算
        COUNT=$(grep -c "\"name\":" "$DAILY_SOURCE_FILE")
        log_msg "📊 今日数据简报: 采集到约 $COUNT 个项目"
        
    else
        log_msg "⚠️ 未找到今日源文件 ($DAILY_SOURCE_FILE)，跳过归档。"
    fi
    
    log_msg "Shell 存储任务结束。"

} >> "$LOG_FILE" 2>&1