import os
import time
import subprocess
from datetime import datetime
from pathlib import Path

# 针对「探微」的监控配置
# 探微监控知微的 WebSocket 心跳状态
LOG_FILE = Path.home() / "logs" / "ws_heartbeat.json"
SERVICE_NAME = "com.zhiwei.bot"
TIMEOUT_SECONDS = 1800  # 放宽至 30 分钟

def check_bot():
    if not LOG_FILE.exists():
        return
    
    mtime = LOG_FILE.stat().st_mtime
    age = time.time() - mtime
    
    # 增加进程心跳判定
    if age > TIMEOUT_SECONDS:
        print(f"[{datetime.now()}] ⚠️ 监控发现静默超时 ({int(age)}s). 尝试热重启 {SERVICE_NAME}...")
        subprocess.run(["launchctl", "kickstart", "-k", f"gui/501/{SERVICE_NAME}"])
        # 重置 mtime 防止连续重启
        LOG_FILE.touch()

if __name__ == "__main__":
    print(f"🚀 开始运行「探微」管家哨兵 (Timeout: {TIMEOUT_SECONDS}s)")
    while True:
        check_bot()
        time.sleep(60)
