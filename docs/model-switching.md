# 模型切换说明文档

> 更新时间: 2026-02-25
> 版本: v1.0

## 一、可用模型列表

### 包月模型（Coding Plan，推荐）

| 序号 | 模型 ID | 名称 | 推荐场景 |
|------|---------|------|---------|
| 1 | qwen3.5-plus | Qwen 3.5 Plus | 通用任务（默认） |
| 2 | qwen3-coder-plus | Qwen Coder | 编程任务 |
| 3 | qwen3-max-2026-01-23 | Qwen Max | 复杂推理 |
| 4 | kimi-k2.5 | Kimi K2.5 | 超长文档 |
| 5 | glm-5 | GLM-5 | 智谱模型 |
| 6 | MiniMax-M2.5 | MiniMax M2.5 | MiniMax |

### 按量模型（DashScope）

| 序号 | 模型 ID | 名称 | 推荐场景 |
|------|---------|------|---------|
| 7 | qwen-plus | Qwen Plus | 日常任务 |
| 8 | qwen-max | Qwen Max | 复杂任务 |

---

## 二、切换方式

### 飞书切换
模型 # 查看可用模型列表
m1 # 切换到 Qwen 3.5 Plus
m2 # 切换到 Qwen Coder（编程）
m3 # 切换到 Qwen Max（最强）
m4 # 切换到 Kimi K2.5（长文）
m5 # 切换到 GLM-5
m6 # 切换到 MiniMax M2.5
m7 # 切换到 Qwen Plus（按量）
m8 # 切换到 Qwen Max（按量）
状态 # 查看当前使用的模型


### 终端切换（ocmodel 命令）

ocmodel      # 查看帮助和当前模型
ocmodel 1    # 切换到 Qwen 3.5 Plus
ocmodel 2    # 切换到 Qwen Coder（编程）
ocmodel 3    # 切换到 Qwen Max（最强）
ocmodel 4    # 切换到 Kimi K2.5（长文）
ocmodel 5    # 切换到 GLM-5
ocmodel 6    # 切换到 MiniMax M2.5
ocmodel 7    # 切换到 Qwen Plus（按量）
ocmodel 8    # 切换到 Qwen Max（按量）
OpenClaw WebUI 切换
打开 Dashboard: docker exec clawdbot openclaw dashboard
进入 Config → Raw
修改 agents.defaults.model.primary 字段
或使用终端命令 ocmodel <数字>
三、同步机制
飞书和 OpenClaw 共享同一个模型配置：

配置文件: ~/logs/current_model.json
飞书切换 → 自动同步到 OpenClaw
终端 ocmodel 切换 → 自动同步到飞书
四、推荐使用场景
场景	推荐模型	命令
日常问答	Qwen 3.5 Plus	m1
写代码/调试	Qwen Coder	m2
复杂分析/报告	Qwen Max	m3
长文档处理	Kimi K2.5	m4
中文任务	GLM-5	m5
五、API 配置
环境变量（~/tanwei-bot/.env）

# Coding Plan（包月）
CODING_PLAN_API_KEY=sk-sp-xxxxxx

# DashScope（按量）
DASHSCOPE_API_KEY=sk-xxxxxx
Provider 配置
Provider	API Endpoint	计费
coding-plan (bailian)	https://coding.dashscope.aliyuncs.com/v1	包月
dashscope	https://dashscope.aliyuncs.com/compatible-mode/v1	按量
六、相关文件

~/logs/current_model.json                    # 共享模型配置
~/feishu-gateway/ws_client.py                # 飞书机器人
~/clawdbot-docker/workspace/scripts/switch_model.sh  # 切换脚本
/usr/local/bin/ocmodel                       # 快捷命令
七、故障排查
模型切换不同步

# 查看共享配置
cat ~/logs/current_model.json

# 查看 OpenClaw 配置
docker exec clawdbot grep '"primary"' /root/.openclaw/openclaw.json

# 手动同步
ocmodel 1
飞书模型不生效

# 重启飞书网关
launchctl stop com.liufang.feishu-gateway
launchctl start com.liufang.feishu-gateway

# 检查日志
tail -20 ~/logs/feishu-gateway.log
