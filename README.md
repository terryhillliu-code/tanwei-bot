# 🔬 探微 Bot (tanwei-bot)

配置驱动的 AI 信息监控与推送工具。用 YAML 定义工作流，AI 自动采集、分析、推送。

## ✨ 特性

- **配置驱动** — YAML 定义工作流，不写代码
- **多信息源** — RSS（更多信息源开发中）
- **AI 分析** — 接入大模型自动分析研判
- **多渠道推送** — 钉钉（企微/Telegram 开发中）
- **定时调度** — 自然语言定义调度规则
- **降级容错** — 采集失败自动降级
- **Docker 部署** — 一键启动

## 🚀 快速开始

### 1. 克隆项目

git clone https://github.com/yourname/tanwei-bot.git
cd tanwei-bot
2. 配置环境变量

cp .env.example .env
# 编辑 .env，填写 API Key 和钉钉 Webhook
3. 启动
Docker 方式（推荐）：

docker compose up -d
本地运行：

pip install -e .
tanwei-bot start
📖 使用
手动触发工作流

tanwei-bot run news-intel
tanwei-bot run daily-report
查看状态

tanwei-bot status
验证配置

tanwei-bot check
⚙️ 配置
主配置 (config/bot.yaml)

name: "我的 Bot"
providers:
  dashscope:
    api_key: "${DASHSCOPE_API_KEY}"
    base_url: "https://dashscope.aliyuncs.com/compatible-mode/v1"
default_model:
  provider: dashscope
  model: qwen3.5-plus
channels:
  my-dingtalk:
    type: dingtalk
    webhook: "${DINGTALK_WEBHOOK}"
    secret: "${DINGTALK_SECRET}"
workflows:
  - news-intel
工作流 (config/workflows/*.yaml)

name: "全球要闻"
schedule: "every 2h"
steps:
  - id: collect
    action: collect
    sources:
      - type: rss
        url: "https://news.ycombinator.com/rss"
        label: "Hacker News"
    output: raw_news
  - id: analyze
    action: analyze
    input: "${raw_news}"
    prompt: "templates/news_analysis.md"
    output: analysis
  - id: push
    action: publish
    input: "${analysis}"
    channel: my-dingtalk
    format:
      title: "📰 {date} 要闻"
调度规则
"every 2h" — 每 2 小时
"every 30m" — 每 30 分钟
"daily 08:00" — 每天 8 点
"daily 09:00,18:00" — 每天 9 点和 18 点
null — 仅手动触发
📡 支持的信息源
类型	状态	说明
RSS	✅	任意 RSS/Atom feed
API	🔜	自定义 API 接入
Web	🔜	网页抓取
📤 支持的推送渠道
渠道	状态	说明
钉钉	✅	Webhook + 签名
企业微信	🔜	开发中
Telegram	🔜	开发中
Email	🔜	开发中
🏗️ 自定义工作流
复制 config/workflows/_example.yaml
修改信息源、分析规则、推送渠道
在 config/bot.yaml 的 workflows 列表中添加文件名
重启 Bot
📄 License
MIT
