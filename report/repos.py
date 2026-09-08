# -*- coding: utf-8 -*-
"""저장소 발견과 git 수집.

저장소는 두 소스의 합집합으로 찾는다 — 세션 cwd(git 루트로 정규화)와
config.yaml 에 등록된 저장소. 한쪽만 쓰면 구멍이 난다. 세션만 쓰면 등록됐는데
그날 세션이 없던 저장소를 놓치고, config 만 쓰면 새로 등장한 저장소가
조용히 사라진다.
"""
from __future__ import annotations

import datetime as dt
import subprocess
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

from .config import Config, normalize_repo
from .sessions import SessionEvent

_SEP = "\x1f"  # git --pretty 필드 구분자. 커밋 제목에 나올 일이 없다


@dataclass(frozen=True)
class Commit:
    sha: str
    time: str
    subject: str
    email: str


def _git(repo: str | Path, *args: str) -> str | None:
    """git 명령을 돌려 stdout 을 준다. 실패하면 None.

    core.quotepath=false 를 매 호출에 강제한다 — 안 그러면 한글처럼 ASCII 가
    아닌 경로를 git 이 8진수 이스케이프 문자열로 따옴표 처리해버려서 (예:
    "\\355\\225\\234...") uncommitted() 결과가 사람도 코드도 못 읽는 값이 된다.

    exit code 가 0 이 아니어도 대부분은 조용히 None 을 준다 — discover() 가
    "git 저장소가 아닌 cwd"를 이 경로로 걸러내기 때문에, 저장소가 아닌 게
    죄가 아니다. 다만 git 이 옵션 자체를 못 알아들었을 때만 예외로 시끄럽게
    한다 — 이건 우리 쪽 인자가 잘못됐다는 뜻이라(예: git 버전이 낮아 새
    플래그를 모름) 조용히 넘어가면 커밋이 통째로 사라진 채 아무도 모른다.
    """
    argv = ["git", "-c", "core.quotepath=false", "-C", str(repo), *args]
    try:
        out = subprocess.run(
            argv,
            capture_output=True, text=True, encoding="utf-8", errors="replace",
        )
    except OSError:
        return None
    if out.returncode != 0:
        stderr = out.stderr or ""
        if "unknown option" in stderr.lower() or "unrecognized" in stderr.lower():
            raise RuntimeError(
                "git 이 인자를 인식하지 못함: {} — {}".format(argv, stderr.strip())
            )
        return None
    return out.stdout


def git_root(path: str | Path) -> str | None:
    p = Path(path)
    if not p.exists():
        return None
    out = _git(p, "rev-parse", "--show-toplevel")
    if not out or not out.strip():
        return None
    return str(Path(out.strip()).resolve())


def to_rel(abs_path: str, dev_root: str) -> str:
    """dev_root 기준 상대 경로. 밖이면 절대 경로를 / 로 정규화해 준다."""
    try:
        rel = Path(abs_path).resolve().relative_to(Path(dev_root).resolve())
    except (ValueError, OSError):
        return normalize_repo(abs_path)
    return normalize_repo(str(rel))


def branch(repo: str | Path) -> str | None:
    out = _git(repo, "rev-parse", "--abbrev-ref", "HEAD")
    return out.strip() if out and out.strip() else None


def commits(
    repo: str | Path, day: dt.date, me: Sequence[str]
) -> tuple[list[Commit], int]:
    """(본인 커밋 목록, 제외한 타인 커밋 수). git 저장소가 아니면 ([], 0)."""
    since = day.isoformat()
    until = (day + dt.timedelta(days=1)).isoformat()
    out = _git(
        repo,
        "log", "--all",
        # --since 는 순수 필터가 아니라 히스토리 워크 조기종료 최적화다 —
        # HEAD 쪽에서 범위 밖 커밋을 만나면 그 밑은 안 본다. 테스트 픽스처처럼
        # 가장 최근에 만든 커밋의 committer date 가 더 예전이면(리베이스 등도
        # 마찬가지) 그 아래 있는 진짜 대상 커밋들을 통째로 놓친다. 조용히
        # 커밋이 사라지는 걸 막기 위해 --since-as-filter 로 순수 필터링한다.
        "--since-as-filter={}T00:00".format(since),
        "--until={}T00:00".format(until),
        "--pretty=%h{s}%ad{s}%ae{s}%s".format(s=_SEP),
        "--date=format:%H:%M",
    )
    if out is None:
        return [], 0

    mine: list[Commit] = []
    skipped = 0
    lowered = {e.lower() for e in me}
    for line in out.splitlines():
        parts = line.split(_SEP, 3)
        if len(parts) != 4:
            continue
        sha, when, email, subject = parts
        if email.lower() in lowered:
            mine.append(
                Commit(sha=sha, time=when, subject=subject, email=email)
            )
        else:
            skipped += 1
    mine.reverse()  # git log 는 최신순 — 시간 오름차순으로 뒤집는다
    return mine, skipped


def uncommitted(repo: str | Path) -> list[str]:
    out = _git(repo, "status", "--porcelain")
    if out is None:
        return []
    return [ln for ln in out.splitlines() if ln.strip()]


def discover(events: Sequence[SessionEvent], config: Config) -> list[str]:
    """저장소 상대 경로 목록. 세션에서 발견된 것 ∪ config 등록분."""
    found: set[str] = set()
    seen_cwd: set[str] = set()

    for ev in events:
        if ev.cwd in seen_cwd:
            continue
        seen_cwd.add(ev.cwd)
        root = git_root(ev.cwd)
        # git 저장소가 아니어도 근거에서 빼지 않는다 (교육 폴더 등)
        found.add(to_rel(root or ev.cwd, config.dev_root))

    for cat in config.categories:
        found.update(cat.repos)

    return sorted(found)
