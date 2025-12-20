#!/bin/bash
# ========================================================
# 模块名称：自动化测试套件 (Test Suite) - [部署与测试]
# 功能描述：模拟一次完整流程，但不写入生产数据库，用于验证环境
# ========================================================

echo "========== 开始系统自检 (Test Mode) =========="

# 1. 检查 Python 环境
python3 --version > /dev/null 2>&1
if [ $? -eq 0 ]; then
    echo "[PASS] Python 环境正常"
else
    echo "[FAIL] Python 未安装"
fi

# 2. 检查依赖库
pip3 show requests > /dev/null 2>&1
if [ $? -eq 0 ]; then
    echo "[PASS] Python 依赖 (requests) 已安装"
else
    echo "[FAIL] 依赖缺失，请运行 pip install -r requirements.txt"
fi

# 3. 检查脚本权限
for script in bin/*.sh; do
    if [ -x "$script" ]; then
        echo "[PASS] 脚本具有执行权限: $script"
    else
        echo "[WARN] 修正权限: $script"
        chmod +x "$script"
    fi
done

# 4. 模拟网络连通性 (测试 GitHub API)
HTTP_CODE=$(curl -o /dev/null -s -w "%{http_code}\n" https://api.github.com)
if [ "$HTTP_CODE" == "200" ]; then
    echo "[PASS] GitHub API 连接正常"
else
    echo "[WARN] GitHub API 连接可能有问题 (Code: $HTTP_CODE)，请检查代理"
fi

echo "========== 自检完成 =========="