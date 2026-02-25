"""LLM 用量统计"""
import json
import os
from datetime import datetime
from pathlib import Path

USAGE_FILE = Path.home() / "logs" / "llm_usage.jsonl"

def record_usage(provider: str, model: str, tokens: int, source: str = "tanwei-bot", workflow: str = ""):
    """记录一次 LLM 调用"""
    if not tokens:
        return
    USAGE_FILE.parent.mkdir(exist_ok=True)
    record = {
        "timestamp": datetime.now().isoformat(),
        "provider": provider,
        "model": model,
        "tokens": tokens,
        "source": source,
        "workflow": workflow,
    }
    with open(USAGE_FILE, "a") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")

def get_daily_usage(date: str = None) -> dict:
    """获取某天的用量统计"""
    if date is None:
        date = datetime.now().strftime("%Y-%m-%d")
    
    total = 0
    by_model = {}
    by_source = {}
    by_workflow = {}
    count = 0
    
    if not USAGE_FILE.exists():
        return {"date": date, "total": 0, "count": 0, "by_model": {}, "by_source": {}, "by_workflow": {}}
    
    with open(USAGE_FILE) as f:
        for line in f:
            if not line.strip():
                continue
            try:
                record = json.loads(line)
            except:
                continue
            if record["timestamp"].startswith(date):
                tokens = record.get("tokens", 0) or 0
                total += tokens
                count += 1
                
                model = record.get("model", "unknown")
                source = record.get("source", "unknown")
                workflow = record.get("workflow", "") or "unknown"
                
                by_model[model] = by_model.get(model, 0) + tokens
                by_source[source] = by_source.get(source, 0) + tokens
                by_workflow[workflow] = by_workflow.get(workflow, 0) + tokens
    
    return {
        "date": date,
        "total": total,
        "count": count,
        "by_model": by_model,
        "by_source": by_source,
        "by_workflow": by_workflow,
    }

def format_usage_report(date: str = None) -> str:
    """格式化用量报告"""
    usage = get_daily_usage(date)
    
    lines = [
        f"## 📊 LLM 用量统计 ({usage['date']})",
        "",
        f"**总调用**: {usage['count']} 次",
        f"**总 tokens**: {usage['total']:,}",
        "",
    ]
    
    if usage['by_model']:
        lines.append("**按模型**:")
        for model, tokens in sorted(usage['by_model'].items(), key=lambda x: -x[1]):
            lines.append(f"- {model}: {tokens:,}")
        lines.append("")
    
    if usage['by_source']:
        lines.append("**按来源**:")
        for source, tokens in sorted(usage['by_source'].items(), key=lambda x: -x[1]):
            lines.append(f"- {source}: {tokens:,}")
        lines.append("")
    
    if usage['by_workflow']:
        lines.append("**按工作流**:")
        for wf, tokens in sorted(usage['by_workflow'].items(), key=lambda x: -x[1]):
            lines.append(f"- {wf}: {tokens:,}")
    
    return "\n".join(lines)
