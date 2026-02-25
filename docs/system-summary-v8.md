# 系统总结文档 v8 (2026-02-25)

> **用途**：新对话的起始上下文。粘贴此文档即可恢复完整系统认知。
> **更新**：v8 知微机器人（完整 Agent 能力）

---

## 一、整体架构
Mac 宿主机 (MacBook Pro Apple Silicon)
├── Docker Desktop
│ ├── clawdbot 容器 (OpenClaw 2026.2.21-2) ✅
│ │ ├── 4 Agent（知微/探微/筑微/通微）
│ │ ├── 35 Skills（含 douyin-video-insight）
│ │ └── bailian provider（Coding Plan）
│ └── situation-monitor 容器 ✅
│
├── ~/tanwei-bot/ (核心引擎)
│ ├── RSS 采集 + 新闻去重 ✅
│ ├── LLM 分析 (Coding Plan)
│ └── 钉钉 + 飞书推送 ✅
│
├── ~/feishu-gateway/ (探微情报机器人)
│ ├── 新闻/早报触发
│ ├── 视频分析
│ ├── 模型切换 m1-m8
│ └── AI 简单问答
│
├── ~/zhiwei-bot/ (知微机器人) ✅ 新增
│ ├── 完整 Agent 能力 = WebUI
│ ├── 多轮对话记忆
│ ├── 工具调用、文件读写
│ └── 模型切换同步
│
├── ~/logs/current_model.json (模型同步)
└── 10 个 launchd 定时任务



---

## 二、飞书机器人对比

| 机器人 | App ID | 职责 | 能力 |
|--------|--------|------|------|
| **探微情报** | cli_a917bc583a78dbcc | 情报推送 + 简单问答 | 新闻/早报/视频/模型切换 |
| **知微** | cli_a9142bd071bd1bd9 | 完整 Agent | = OpenClaw WebUI 全能力 |

### 探微情报命令
新闻/早报/状态
模型 / m1-m8
视频链接 → 自动分析
其他 → AI 问答



### 知微命令
/help - 帮助
/reset - 重置对话
/session - 查看会话
m1-m8 - 切换模型
其他 → OpenClaw Agent



---

## 三、LLM 模型配置

### 可用模型

| 序号 | 模型 | 场景 | 命令 |
|------|------|------|------|
| 1 | qwen3.5-plus | 通用 | m1 |
| 2 | qwen3-coder-plus | 编程 | m2 |
| 3 | qwen3-max | 最强 | m3 |
| 4 | kimi-k2.5 | 长文 | m4 |
| 5 | glm-5 | 智谱 | m5 |
| 6 | MiniMax-M2.5 | MiniMax | m6 |
| 7 | qwen-plus | 按量 | m7 |
| 8 | qwen-max | 按量 | m8 |

### 切换方式

# 飞书（两个机器人通用）
m2              # 切换到编程模型

# 终端
ocmodel 2       # 同步到飞书和 OpenClaw

# 同步机制
~/logs/current_model.json  # 三端共享
四、关键操作速查

# === 知微机器人 ===
launchctl list | grep zhiwei
tail -f ~/logs/zhiwei-bot.log
launchctl stop com.liufang.zhiwei-bot
launchctl start com.liufang.zhiwei-bot

# === 探微情报 ===
launchctl list | grep feishu-gateway
tail -f ~/logs/feishu-gateway.log

# === 模型切换 ===
ocmodel           # 查看当前
ocmodel 2         # 切换编程模型
cat ~/logs/current_model.json

# === tanwei-bot ===
cd ~/tanwei-bot && source venv/bin/activate
tanwei-bot run news-intel
tanwei-bot usage

# === Git ===
cd ~/zhiwei-bot && git status       # 新增
cd ~/feishu-gateway && git status
cd ~/tanwei-bot && git status
cd ~/clawdbot-docker && git status
五、工作流与定时任务

静默时段：23:00 - 08:00

工作流（6个）：
  08:00  daily-report  → tanwei-bot 全量推送
  09:30  market-am     → zhiwei 分析
  15:30  market-pm     → zhiwei 分析  
  每2h   news-push     → tanwei-bot 增量推送
  每4h   crypto-push   → zhiwei 分析
  00:00  system-check  → 系统巡检

监控（3个）：
  每1m   health-monitor
  每10m  metrics-sample
  每1h   disk-watch

常驻服务（2个）：
  feishu-gateway  → 探微情报
  zhiwei-bot      → 知微 Agent ✅ 新增
六、新增能力（v8）

1. 知微机器人 ✅
   - 完整 Agent 能力 = WebUI
   - 多轮对话记忆
   - 工具调用
   - 模型切换同步

2. 会话管理 ✅
   - 私聊独立会话
   - 群聊按用户隔离
   - /reset 重置对话

3. 命令增强 ✅
   - /help 帮助
   - /session 查看会话
   - m1-m8 快速切换模型
七、相关文件

~/zhiwei-bot/
├── ws_client.py              # 主程序
├── venv/                     # 虚拟环境
└── .git/                     # Git 仓库

~/Library/LaunchAgents/
└── com.liufang.zhiwei-bot.plist

~/logs/
├── zhiwei-bot.log           # 运行日志
├── zhiwei-bot.error.log     # 错误日志
└── current_model.json       # 模型同步配置
八、重启自愈

Mac 开机
→ Docker Desktop 自启 ✅
→ clawdbot 容器自启 ✅
→ feishu-gateway 自启（探微情报）✅
→ zhiwei-bot 自启（知微）✅ 新增
→ 定时任务按时触发 ✅
→ 模型配置同步恢复 ✅
九、后续待办
短期

✅ 知微机器人（已完成）
□ 飞书私聊优化
□ 更多 RSS 源
中期

□ 用量统计可视化
□ Web UI 管理界面
□ 定时任务健康报告
文档生成时间：2026-02-25 15:00 CST
版本：v8.0
