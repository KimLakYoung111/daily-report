#!/usr/bin/env python3
"""로컬 Claude Code 세션 기록에서 하루치 작업 목록을 뽑는다.
사용법: python3 daily_report.py [YYYY-MM-DD]   (생략 시 오늘)
"""
import json, sys, glob, os, datetime, collections

day = sys.argv[1] if len(sys.argv) > 1 else datetime.date.today().isoformat()
target = datetime.date.fromisoformat(day)
local = datetime.datetime.now().astimezone().tzinfo

sessions = {}
for f in glob.glob(os.path.expanduser("~/.claude/projects/**/*.jsonl"), recursive=True):
    for line in open(f, encoding="utf-8", errors="replace"):
        try:
            o = json.loads(line)
        except Exception:
            continue
        ts = o.get("timestamp")
        if not ts:
            continue
        t = datetime.datetime.fromisoformat(ts.replace("Z", "+00:00")).astimezone(local)
        if t.date() != target:
            continue
        s = sessions.setdefault(f, {"first": t, "last": t, "cwd": None, "branches": set(), "prompts": [], "n": 0})
        s["first"] = min(s["first"], t); s["last"] = max(s["last"], t)
        s["cwd"] = s["cwd"] or o.get("cwd")
        if o.get("gitBranch"):
            s["branches"].add(o["gitBranch"])
        s["n"] += 1
        if o.get("type") == "user" and o.get("userType") == "external":
            m = o.get("message", {}).get("content")
            if isinstance(m, list):
                m = " ".join(c.get("text", "") for c in m if isinstance(c, dict))
            if isinstance(m, str) and m.strip() and not m.startswith("<"):
                s["prompts"].append(m.strip().replace("\n", " ")[:120])

by_proj = collections.defaultdict(list)
for f, s in sessions.items():
    by_proj[os.path.basename(s["cwd"] or os.path.dirname(f))].append(s)

print(f"# Claude Code 일일 작업 보고 — {target}\n")
for proj in sorted(by_proj):
    ss = sorted(by_proj[proj], key=lambda x: x["first"])
    print(f"## {proj}  (세션 {len(ss)}건)")
    for s in ss:
        br = ", ".join(sorted(s["branches"])) or "-"
        print(f"- {s['first']:%H:%M}~{s['last']:%H:%M} | 브랜치 {br} | 이벤트 {s['n']}")
        for p in s["prompts"][:6]:
            print(f"    · {p}")
    print()
