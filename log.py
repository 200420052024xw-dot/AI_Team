import os
import sys
import json
import urllib.request
import datetime
import urllib.parse

SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")

def log(agent, message, status="working"):
    data = json.dumps({
        "event_type": "agent_message",
        "agent": agent,
        "payload": {"message": message, "status": status}
    }).encode()
    req = urllib.request.Request(
        f"{SUPABASE_URL}/rest/v1/dev_events",
        data=data,
        headers={
            "apikey": SUPABASE_KEY,
            "Authorization": f"Bearer {SUPABASE_KEY}",
            "Content-Type": "application/json",
            "Prefer": "return=minimal"
        },
        method="POST"
    )
    urllib.request.urlopen(req)

def mission(title):
    data = json.dumps({
        "title": title,
        "status": "running"
    }).encode()
    req = urllib.request.Request(
        f"{SUPABASE_URL}/rest/v1/dev_missions",
        data=data,
        headers={
            "apikey": SUPABASE_KEY,
            "Authorization": f"Bearer {SUPABASE_KEY}",
            "Content-Type": "application/json",
            "Prefer": "return=representation"
        },
        method="POST"
    )
    res = urllib.request.urlopen(req)
    return json.loads(res.read())[0]["id"]

def step(mission_id, agent, step_kind, status="running"):
    data = json.dumps({
        "mission_id": mission_id,
        "assigned_to": agent,
        "step_kind": step_kind,
        "status": status
    }).encode()
    req = urllib.request.Request(
        f"{SUPABASE_URL}/rest/v1/dev_steps",
        data=data,
        headers={
            "apikey": SUPABASE_KEY,
            "Authorization": f"Bearer {SUPABASE_KEY}",
            "Content-Type": "application/json",
            "Prefer": "return=minimal"
        },
        method="POST"
    )
    urllib.request.urlopen(req)

def output(mission_id, title, content, output_type="document"):
    """存储任务产出到 dev_outputs 表"""
    data = json.dumps({
        "mission_id": mission_id,
        "title": title,
        "content": content,
        "output_type": output_type
    }).encode()
    req = urllib.request.Request(
        f"{SUPABASE_URL}/rest/v1/dev_outputs",
        data=data,
        headers={
            "apikey": SUPABASE_KEY,
            "Authorization": f"Bearer {SUPABASE_KEY}",
            "Content-Type": "application/json",
            "Prefer": "return=minimal"
        },
        method="POST"
    )
    urllib.request.urlopen(req)

def finish_mission(mission_id, total_messages=0, bugs_found=0, bugs_fixed=0):
    """任务完成时更新统计数据"""
    now = datetime.datetime.utcnow().isoformat() + 'Z'
    data = json.dumps({
        "status": "succeeded",
        "finished_at": now,
        "total_messages": total_messages,
        "bugs_found": bugs_found,
        "bugs_fixed": bugs_fixed
    }).encode()
    url = f"{SUPABASE_URL}/rest/v1/dev_missions?id=eq.{mission_id}"
    req = urllib.request.Request(url, data=data, headers={
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type": "application/json",
        "X-HTTP-Method-Override": "PATCH"
    }, method="POST")
    urllib.request.urlopen(req)

if __name__ == "__main__":
    # 命令行调用方式：
    # python log.py agent "消息内容" status
    # python log.py --mission "任务名称"
    # python log.py --step mission_id agent step_kind status
    # python log.py --output mission_id "标题" "内容" document
    # python log.py --finish mission_id 消息总数 bug数 修复数
    if sys.argv[1] == "--mission":
        mid = mission(sys.argv[2])
        print(mid)
    elif sys.argv[1] == "--step":
        step(sys.argv[2], sys.argv[3], sys.argv[4], sys.argv[5])
    elif sys.argv[1] == "--output":
        output(sys.argv[2], sys.argv[3], sys.argv[4], sys.argv[5] if len(sys.argv) > 5 else "document")
    elif sys.argv[1] == "--finish":
        finish_mission(sys.argv[2], int(sys.argv[3]), int(sys.argv[4]), int(sys.argv[5]))
    else:
        log(sys.argv[1], sys.argv[2], sys.argv[3] if len(sys.argv) > 3 else "working")
