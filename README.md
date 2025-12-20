# GitHub Trends Crawler & Visualizer

这是一个专注于收集、归档和可视化 GitHub 每日趋势榜单（Trending）的开源工具。

针对 GitHub Trending 页面经常无法访问或 API 限制严格的问题，本项目采用了 **"网页爬虫 + API 降级保底"** 的双引擎机制，并特别针对 **WSL (Windows Subsystem for Linux)** 开发环境进行了网络适配，确保在国内网络环境下也能稳定运行。

## 功能特性

* **双引擎采集机制**：
  * **Engine A (爬虫)**：优先抓取 GitHub Trending 页面，获取最准确的 "今日星数 (stars today)" 增量数据。
  * **Engine B (API)**：当网页抓取失败（如反爬虫限制、网络超时）时，自动切换至 GitHub Search API 进行兜底，确保数据流不断档。
* **智能网络适配**：
  * 支持标准的 HTTP/HTTPS 环境变量代理配置。
  * **WSL 专属优化**：在 WSL2 环境下，若未手动配置代理，脚本会自动探测宿主机 IP 并连接，解决 WSL 网络连通性问题。
* **数据可视化平台**：
  * 内置 Flask Web 应用，提供日/周/月榜单的历史归档查询。
  * 支持按日期回溯查看过往的热门项目。
* **自动化与持久化**：
  * 提供 Shell 脚本支持定时任务（Cron）。
  * 包含数据校验、归档存储等完整的数据流处理工具。

## 目录结构

```text
.
├── bin/
│   ├── collector.py       # [核心] 数据采集脚本 (双引擎 + 智能代理)
│   ├── processor.py       # [核心] 数据清洗与格式化处理
│   ├── main.sh            # [入口] 主任务调度脚本
│   ├── publisher.sh       # 发布脚本 (处理生成报告/Git推送)
│   ├── storage.sh         # 存储管理脚本 (归档/清理旧数据)
│   ├── validator.sh       # 数据校验脚本 (确保 JSON 格式正确)
│   └── test_suite.sh      # 功能测试套件
├── web/
│   ├── app.py             # Flask Web 服务器
│   ├── templates/
│   │   └── index.html     # 前端主页模板
│   └── static/
│       ├── reports/       # (自动生成) 每日 HTML 静态报告
│       └── downloads/     # (自动生成) 供下载的 JSON 数据
├── data/
│   └── raw/               # 原始 JSON 数据存储 (自动生成)
├── .gitignore             # Git 忽略配置文件
├── requirements.txt       # Python 依赖库
└── README.md              # 项目说明文档
```

