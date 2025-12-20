#!/bin/bash

# ========================================================
# 模块名称：数据校验模块 (Validator) 
# 功能描述：在处理前对原始数据进行完整性与合法性检查
# ========================================================

BASE_DIR=$(dirname $(dirname $(readlink -f "$0")))
RAW_DIR="$BASE_DIR/data/raw"
DATE_STR=$(date +%F)
TARGET_FILE="$RAW_DIR/github_daily_${DATE_STR}.json"

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] [VALIDATOR] $1"
}

log "开始执行数据校验..."

# 1. 检查文件是否存在
if [ ! -f "$TARGET_FILE" ]; then
    log "[ERROR] ❌ 今日原始数据文件未生成: $TARGET_FILE"
    exit 1
fi

# 2. 检查文件大小 (防止空文件)
FILE_SIZE=$(wc -c < "$TARGET_FILE")
if [ "$FILE_SIZE" -lt 10 ]; then
    log "[ERROR] ❌ 数据文件过小 ($FILE_SIZE bytes)，可能是空数据。"
    exit 1
fi

# 3. 简单的 JSON 结构校验 (利用 Python 单行脚本)
# 检查是否包含 "name" 字段，确保爬到了内容
VALID_COUNT=$(grep -o '"name":' "$TARGET_FILE" | wc -l)
if [ "$VALID_COUNT" -eq 0 ]; then
    log "[ERROR] ❌ 数据文件通过格式检查，但未包含有效项目数据 (Count=0)。"
    exit 1
fi

log "[SUCCESS] ✅ 数据校验通过！文件大小: $FILE_SIZE bytes, 有效条目数: ~$VALID_COUNT"
exit 0