# -*- coding: utf-8 -*-
"""Claude Code 세션 기록(*.jsonl)에서 하루치 이벤트를 읽는다.

daily_report.py 는 세션 파일의 첫 cwd 로 전체를 집계해, 세션 중간에
디렉터리를 옮기면 그쪽 작업이 다른 저장소에 붙는 버그가 있다.
여기서는 이벤트마다 cwd 를 따로 본다.
"""
from __future__ import annotations

import datetime as dt
import json
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

PROMPT_MAX = 120


@dataclass(frozen=True)
class SessionEvent:
    ts: dt.datetime
    cwd: str
    prompt: str | None = None


def _local_tz() -> dt.tzinfo:
    return dt.datetime.now().astimezone().tzinfo


def _extract_prompt(obj: dict, ignore_prompts: Sequence[str]) -> str | None:
    """사람이 직접 넣은 프롬프트만 돌려준다. 아니면 None."""
    if obj.get("type") != "user" or obj.get("userType") != "external":
        return None
    content = (obj.get("message") or {}).get("content")
    if isinstance(content, list):
        content = " ".join(
            c.get("text", "") for c in content if isinstance(c, dict)
        )
    if not isinstance(content, str):
        return None
    text = content.strip().replace("\n", " ")
    if not text or text.startswith("<"):
        return None
    if any(pat in text for pat in ignore_prompts):
        return None
    return text[:PROMPT_MAX]


def load_events(
    day: dt.date,
    projects_root: str | Path,
    ignore_prompts: Sequence[str] = (),
) -> list[SessionEvent]:
    """projects_root 아래 모든 *.jsonl 에서 day 에 해당하는 이벤트를 모은다."""
    tz = _local_tz()
    events: list[SessionEvent] = []

    for path in sorted(Path(projects_root).rglob("*.jsonl")):
        with open(path, encoding="utf-8", errors="replace") as fh:
            for raw in fh:
                try:
                    obj = json.loads(raw)
                except (ValueError, TypeError):
                    continue
                if not isinstance(obj, dict):
                    continue
                ts_raw, cwd = obj.get("timestamp"), obj.get("cwd")
                if not ts_raw or not cwd:
                    continue
                try:
                    ts = dt.datetime.fromisoformat(
                        str(ts_raw).replace("Z", "+00:00")
                    ).astimezone(tz)
                except ValueError:
                    continue
                if ts.date() != day:
                    continue
                events.append(
                    SessionEvent(
                        ts=ts,
                        cwd=str(cwd),
                        prompt=_extract_prompt(obj, ignore_prompts),
                    )
                )

    events.sort(key=lambda e: e.ts)
    return events
