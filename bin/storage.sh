#!/bin/bash

# ========================================================
# 模块名称：数据存储与归档模块 (Storage - Optimized)
# 功能描述：将每日数据转换为 NDJSON 格式并追加归档
# 优化点：
# 1. 归档文件名包含年份 (满足文件名带日期要求)
# 2. 去除 JSON 数组外壳，改为逐行存储 (解决 [...][...] 格式问题)
# ========================================================

# 1. 路径定义
BASE_DIR=$(dirname $(dirname $(readlink -f "$0")))
RAW_DATA_DIR="$BASE_DIR/data/raw"
ARCHIVE_DIR="$BASE_DIR/data/archive"
LOG_DIR="$BASE_DIR/logs"
DATE_STR=$(date +%F)
YEAR_STR=$(date +%Y)  # 获取当前年份

# 确保目录存在
mkdir -p "$ARCHIVE_DIR"
mkdir -p "$LOG_DIR"

# 2. 定义归档文件 (优化：按年份生成归档文件，满足“文件名包含日期信息”)
# 例如：data/archive/github_trends_archive_2025.txt
MASTER_FILE="$ARCHIVE_DIR/github_trends_archive_${YEAR_STR}.txt"
DAILY_SOURCE_FILE="$RAW_DATA_DIR/github_daily_${DATE_STR}.json"
LOG_FILE="$LOG_DIR/storage_run.log"

log_msg() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1"
}

# 3. 执行归档逻辑
{
    log_msg "启动 Shell 数据归档任务..."
    
    if [ -f "$DAILY_SOURCE_FILE" ]; then
        # 写入分隔符 (满足“用特殊字符串分割”要求)
        echo "" >> "$MASTER_FILE"
        echo ">>> START_BATCH: $DATE_STR <<<" >> "$MASTER_FILE"
        
        # 核心优化：使用 Python 将 JSON 数组 ([a,b]) 转换为 NDJSON (a\nb)
        # 这样追加到文件中也是合法的，不会出现 [...][...]
        python3 -c "import json, sys; data=json.load(open('$DAILY_SOURCE_FILE')); [print(json.dumps(r, ensure_ascii=False)) for r in data]" >> "$MASTER_FILE"
        
        echo ">>> END_BATCH: $DATE_STR <<<" >> "$MASTER_FILE"
        
        log_msg "✅ 成功归档今日数据至: $MASTER_FILE (NDJSON格式)"
        
        # 统计今日条目数
        COUNT=$(grep -c "START_BATCH: $DATE_STR" "$MASTER_FILE") # 仅作简单标记统计
        log_msg "📊 归档完成，当前文件大小: $(du -h "$MASTER_FILE" | cut -f1)"
        
    else
        log_msg "⚠️ 未找到今日源文件 ($DAILY_SOURCE_FILE)，跳过归档。"
    fi
    
    log_msg "Shell 存储任务结束。"

} >> "$LOG_FILE" 2>&1