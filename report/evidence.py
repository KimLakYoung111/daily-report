# -*- coding: utf-8 -*-
"""근거 마크다운 렌더.

행 초안을 만들지 않는다. 커밋 로그라는 그럴듯한 초안을 믿고 근거 전체를
다시 읽지 않아 미커밋 작업을 놓친 사고가 있었다. 여기서는 근거만 싣고,
진행률·구분 판단은 사람이 한다.
"""
from __future__ import annotations

import datetime as dt
from collections.abc import Sequence
from dataclasses import dataclass

from .repos import Commit

WEEKDAYS = "월화수목금토일"
PROMPT_LIMIT = 8


@dataclass(frozen=True)
class RepoEvidence:
    repo: str
    category: str | None
    branch: str | None
    commits: tuple[Commit, ...]
    skipped: int
    uncommitted: tuple[str, ...]
    event_count: int
    prompts: tuple[str, ...]
    handoff: str | None
    is_git: bool


def _has_activity(row: RepoEvidence) -> bool:
    return bool(row.commits or row.uncommitted or row.event_count)


def active_repos(rows: Sequence[RepoEvidence], is_past: bool) -> list[str]:
    """`data/*.yaml`에 옮겨졌어야 할 저장소만. build_report 의 커버리지 경고가 이걸 쓴다.

    `_has_activity`(근거 마크다운에 절을 렌더할지)와는 다른 질문이다.
    미커밋 여부는 git status — 즉 수집 시점 상태 — 라서 과거 날짜를 말해줄 수
    없다. 그래서 과거 날짜는 미커밋만으로는 활동으로 안 친다. 세션 이벤트만
    있고 커밋도 남은 프롬프트도 없으면(예: /compact 만 찍힌 세션) 사람이
    시킨 일이 없었다는 뜻이므로 오늘이든 과거든 활동이 아니다.
    """
    def is_active(r: RepoEvidence) -> bool:
        if r.commits:
            return True
        if r.prompts:
            return True
        if r.uncommitted and not is_past:
            return True
        return False

    return [r.repo for r in rows if is_active(r)]


def render(
    day: dt.date,
    rows: Sequence[RepoEvidence],
    collected_at: dt.datetime,
    is_past: bool,
) -> str:
    total_mine = sum(len(r.commits) for r in rows)
    total_skipped = sum(r.skipped for r in rows)
    out: list[str] = []

    out.append("# 근거 묶음 — {} ({})".format(day.isoformat(), WEEKDAYS[day.weekday()]))
    out.append(
        "> 수집 {:%Y-%m-%d %H:%M} · 저장소 {}곳 · 본인 커밋 {}건 (타인 {}건 제외)".format(
            collected_at, len(rows), total_mine, total_skipped
        )
    )
    if is_past:
        out.append(
            "> ⚠️ **과거 날짜다.** 미커밋 정보는 그날 상태가 아니라 "
            "수집 시점 상태이므로 신뢰할 수 없다."
        )
    else:
        out.append("> ⚠️ 미커밋 정보는 수집 시점 상태다.")
    out.append("")
    out.append("행 초안은 일부러 만들지 않는다. 아래 근거를 읽고 직접 판단해 "
               "`data/{}.yaml` 을 쓴다.".format(day.isoformat()))
    out.append("")

    out.append("## 커버리지 점검")
    out.append("")
    out.append("| 저장소 | 구분(config) | 커밋 | 미커밋 | 세션 이벤트 | 인계 |")
    out.append("|---|---|---|---|---|---|")
    for r in rows:
        category = r.category or "**구분 미지정**"
        commit_cell = "(git 아님)" if not r.is_git else str(len(r.commits))
        if r.skipped:
            commit_cell += " (+타인 {} 제외)".format(r.skipped)
        out.append(
            "| {} | {} | {} | {} | {:,} | {} |".format(
                r.repo,
                category,
                commit_cell,
                "—" if not r.is_git else len(r.uncommitted),
                r.event_count,
                "✓" if r.handoff else "—",
            )
        )
    out.append("")

    for r in rows:
        if not _has_activity(r):
            continue
        head = "## {}".format(r.repo)
        head += "  `[{}]`".format(r.branch) if r.branch else "  `[git 아님]`"
        head += "  →  {}".format(r.category or "**구분 미지정**")
        out.append("---")
        out.append(head)
        out.append("")

        if r.commits:
            out.append("### 커밋 {}건".format(len(r.commits)))
            for c in r.commits:
                out.append("- {} `{}` {}".format(c.time, c.sha, c.subject))
        else:
            out.append("### 커밋 — 없음")
        out.append("")

        label = "미커밋"
        if is_past:
            label += " **[신뢰 불가 — 과거 날짜]**"
        if r.uncommitted:
            out.append("### {} {}건".format(label, len(r.uncommitted)))
            for line in r.uncommitted:
                out.append("- `{}`".format(line))
        else:
            out.append("### {} — 없음".format(label))
        out.append("")

        if r.handoff:
            out.append("### 인계 문서 (HANDOFF.md 최신 섹션 · 발췌)")
            out.append("")
            out.append(r.handoff)
            out.append("")

        if r.prompts:
            out.append(
                "### 세션 프롬프트 (자동 세션 제외 · 최대 {}건)".format(PROMPT_LIMIT)
            )
            for p in r.prompts[:PROMPT_LIMIT]:
                out.append("- {}".format(p))
            out.append("")

    return "\n".join(out).rstrip() + "\n"
