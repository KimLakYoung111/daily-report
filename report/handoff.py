# -*- coding: utf-8 -*-
"""HANDOFF.md 에서 진행률 판단에 쓰는 헤딩만 뽑는다.

HANDOFF.md 는 최신 판이 맨 위에 쌓인다. 파일 전체는 1,500줄이 넘을 수 있어
최신 섹션만 보고, 그 안에서도 필요한 헤딩만 싣는다.
함정·검증 명령·파일 경로표는 제외한다 — 필요하면 경로로 직접 읽는다.
"""
from __future__ import annotations

import re
from pathlib import Path

#: 소문자로 비교한다. 헤딩 텍스트에 이 중 하나가 들어 있으면 싣는다.
WANTED: tuple[str, ...] = (
    "한 일",
    "what was done",
    "current status",
    "안 한 것",
    "다음 단계",
    "remaining",
    "uncommitted changes",
)

_TOP_HEADING = re.compile(r"^#\s+HANDOFF", re.MULTILINE)
_ANY_HEADING = re.compile(r"^(#{1,6})\s+(.*)$")


def latest_section(text: str) -> str:
    """두 번째 '# HANDOFF' 헤딩 전까지. 하나뿐이거나 없으면 전체."""
    hits = list(_TOP_HEADING.finditer(text))
    if len(hits) < 2:
        return text
    return text[: hits[1].start()]


def select_headings(text: str) -> str:
    """WANTED 에 걸리는 헤딩 블록만 이어붙인다."""
    out: list[str] = []
    keeping = False

    for line in text.splitlines():
        m = _ANY_HEADING.match(line)
        if m:
            title = m.group(2).strip().lower()
            # '# HANDOFF: ...' 같은 최상위 제목은 블록 경계로만 쓴다
            keeping = any(w in title for w in WANTED)
            if keeping:
                out.append(line)
            continue
        if keeping:
            out.append(line)

    return "\n".join(out).strip()


def read(repo_abs: str | Path) -> str | None:
    """저장소 루트의 HANDOFF.md 를 읽어 발췌한다. 없으면 None."""
    path = Path(repo_abs) / "HANDOFF.md"
    if not path.is_file():
        return None
    text = path.read_text(encoding="utf-8", errors="replace")
    return select_headings(latest_section(text))
