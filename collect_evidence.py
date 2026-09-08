#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""근거 수집 — 하루치 작업 근거를 한 파일에 모은다.

사용법:
    python collect_evidence.py            # 오늘
    python collect_evidence.py 2026.9.8   # 특정 날짜

출력:
    output/evidence/YYYY-MM-DD.md          사람이 읽는 근거
    output/evidence/YYYY-MM-DD.repos.json  활동 있던 저장소 목록 (커버리지 검증용)
"""
from __future__ import annotations

import datetime as dt
import json
import os
import sys
from collections import Counter, defaultdict
from pathlib import Path

from report.config import load_config
from report.evidence import RepoEvidence, active_repos, render
from report.handoff import read as read_handoff
from report.repos import branch, commits, discover, git_root, uncommitted
from report.sessions import load_events

HERE = Path(__file__).resolve().parent
OUT_DIR = HERE / "output" / "evidence"
PROJECTS_ROOT = Path(os.path.expanduser("~/.claude/projects"))


def parse_day(text: str | None) -> dt.date:
    """'2026.9.8' → date(2026, 9, 8). 날짜가 아니면 ValueError."""
    if not text:
        return dt.date.today()
    y, m, d = (int(x) for x in text.replace("-", ".").split("."))
    return dt.date(y, m, d)


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8")
    arg = sys.argv[1] if len(sys.argv) > 1 else None
    try:
        day = parse_day(arg)
    except ValueError:
        print("[에러] 날짜를 읽을 수 없다: {!r}".format(arg))
        print("       사용법: python collect_evidence.py [YYYY.M.D]  (예: 2026.9.8)")
        return 1
    config = load_config(HERE / "config.yaml")

    # 세션 폴더가 없으면 멈춘다. load_events 는 없는 트리를 빈 목록으로
    # 돌려주는데(빈 트리를 가리키는 건 정당한 호출이다), 그대로 진행하면
    # 커버리지 표의 세션 이벤트가 전부 0건이 되어 "그날 세션이 없었다"로
    # 읽힌다. Claude Code 가 저장 경로를 바꾸거나 다른 기계에서 돌릴 때
    # 조용히 근거의 절반이 사라지는 경로라 여기서 시끄럽게 끝낸다.
    if not PROJECTS_ROOT.is_dir():
        print("[에러] Claude Code 세션 폴더가 없다: {}".format(PROJECTS_ROOT))
        print("       경로가 바뀌었거나 다른 기계다. 이대로 모으면 세션 이벤트가")
        print("       전부 0건으로 나와 그날 세션이 없었던 것처럼 보인다.")
        return 1

    events = load_events(day, PROJECTS_ROOT, config.ignore_prompts)
    # 저장소 목록과 cwd→저장소 매핑을 한 번에 받는다. 여기서 같은 계산을
    # 다시 하면 discover 와 규칙이 갈릴 때 이벤트가 엉뚱한 저장소에 붙는다.
    repos, repo_of_cwd = discover(events, config)

    # 이벤트를 저장소별로 접어 넣는다 (하위 디렉터리는 git 루트로 정규화)
    counts: Counter[str] = Counter()
    prompts: dict[str, list[str]] = defaultdict(list)
    for ev in events:
        key = repo_of_cwd[ev.cwd]
        counts[key] += 1
        if ev.prompt:
            prompts[key].append("{:%H:%M} · {}".format(ev.ts, ev.prompt))

    rows: list[RepoEvidence] = []
    for repo in repos:
        abs_path = Path(config.dev_root) / repo
        is_git = git_root(abs_path) is not None
        mine, skipped = commits(abs_path, day, config.me) if is_git else ([], 0)
        rows.append(
            RepoEvidence(
                repo=repo,
                category=config.category_for_repo(repo),
                branch=branch(abs_path) if is_git else None,
                commits=tuple(mine),
                skipped=skipped,
                uncommitted=tuple(uncommitted(abs_path)) if is_git else (),
                event_count=counts.get(repo, 0),
                prompts=tuple(prompts.get(repo, ())),
                handoff=read_handoff(abs_path),
                is_git=is_git,
            )
        )

    # 활동 많은 순으로 정렬해 중요한 것부터 읽게 한다
    rows.sort(key=lambda r: (-(len(r.commits) * 100 + r.event_count), r.repo))

    is_past = day < dt.date.today()
    text = render(day, rows, dt.datetime.now(), is_past)

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    md_path = OUT_DIR / "{}.md".format(day.isoformat())
    json_path = OUT_DIR / "{}.repos.json".format(day.isoformat())
    md_path.write_text(text, encoding="utf-8")
    json_path.write_text(
        json.dumps(active_repos(rows, is_past), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    print("[OK] {}  ({}줄)".format(md_path.relative_to(HERE), len(text.splitlines())))
    print("[OK] {}".format(json_path.relative_to(HERE)))
    unknown = [r.repo for r in rows if r.category is None and (r.commits or r.event_count)]
    if unknown:
        print("[확인] config.yaml 에 없는 저장소: {}".format(", ".join(unknown)))
    if is_past:
        print("[주의] 과거 날짜다 — 미커밋 정보는 신뢰할 수 없다")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
