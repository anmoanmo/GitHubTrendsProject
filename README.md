# GitHub Trends Project 部署文档

> **项目简介**：基于 Shell + Python 的 GitHub 趋势全自动监控系统，符合 Linux 课程设计规范。

## 1. 环境依赖配置

本项目运行于 Linux 环境 (Ubuntu/CentOS/Debian)，需预先安装以下依赖：

### 1.1 系统工具

```bash
# 更新源并安装基础工具
sudo apt update
sudo apt install -y python3 python3-pip cron curl
```

### 1.2 Python 依赖

```bash
# 进入项目根目录安装依赖
pip3 install -r requirements.txt
# 核心库说明：
# - requests: 网络请求
# - beautifulsoup4: 网页解析
# - deep-translator: 谷歌翻译支持
# - flask: Web 展示界面
```

## 2. 目录结构说明

```text
project_root/
├── bin/              # 核心脚本目录
│   ├── main.sh       # [入口] 全流程主控脚本
│   ├── collector.py  # 数据采集模块
│   ├── validator.sh  # [拓展] 数据校验模块
│   ├── processor.py  # 数据处理与清洗模块
│   ├── storage.sh    # 数据归档模块 (Shell)
│   └── publisher.sh  # 结果发布模块 (Shell)
├── data/             # 数据存储目录 (Raw/Processed/Archive)
├── logs/             # 日志记录目录
├── web/              # Web 展示端
└── README.md         # 部署文档
```

## 3. 自动化部署 (Crontab)

本项目使用 Linux 系统级 Cron 实现每日定时触发。

1. **获取绝对路径**：
   ```bash
   pwd  # 假设输出 /home/anmo/project
   ```
2. **编辑定时任务**：
   ```bash
   crontab -e
   ```
3. **写入配置** (每日早上 08:00 执行)：
   ```cron
   0 8 * * * /bin/bash /home/anmo/project/bin/main.sh
   ```

## 4. 验证与排查

* **手动触发测试**：`./bin/main.sh`
* **查看运行日志**：`tail -f logs/project_run.log`
* **查看 Web 服务**：`python3 web/app.py` -> 访问 `http://localhost:5000`

## 5. 常见问题 (FAQ)

* **Q: 采集失败，提示连接超时？**
  * A: 脚本内置了 WSL/本地 代理自动识别功能，请检查 `collector.py` 中的 `PROXY_PORT` 是否与本机代理软件一致。

