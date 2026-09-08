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

#: 실패해도 조용히 None 을 줘야 하는(= 정상 상태인) stderr 패턴. 소문자 비교.
#:
#: - "not a git repository": discover() 가 "git 저장소가 아닌 cwd"를 이 경로로
#:   걸러낸다. 교육 폴더처럼 git 이 아닌 작업 위치가 정상적으로 존재한다.
#: - "ambiguous argument 'head'": `git init` 만 하고 커밋이 아직 없는 저장소.
#:   rev-parse --abbrev-ref HEAD 가 exit 128 로 죽는데, 새 프로젝트 폴더에서
#:   흔히 있는 정상 상태다(실측 확인). 여기 없으면 브랜치를 읽다가 수집
#:   전체가 터진다.
_QUIET_STDERR: tuple[str, ...] = (
    "not a git repository",
    "ambiguous argument 'head'",
)


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

    exit code 가 0 이 아닐 때, 조용히 None 을 주는 건 _QUIET_STDERR 에
    적힌 정상 상태뿐이다. 나머지 실패는 전부 RuntimeError 로 터뜨린다.
    옛 동작은 실패를 통째로 삼켜서, `detected dubious ownership`·깨진
    인덱스·권한 오류 같은 진짜 고장이 "커밋 0건 + (git 아님)"으로 조용히
    둔갑했다 — 근거를 다 모았다고 믿게 만드는 실패라 가장 위험하다.
    git 이 옵션 자체를 못 알아들은 경우는 우리 쪽 인자가 잘못됐다는
    뜻이므로(예: git 버전이 낮아 새 플래그를 모름) 메시지를 따로 준다.
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
        stderr = (out.stderr or "").strip()
        lowered = stderr.lower()
        if "unknown option" in lowered or "unrecognized" in lowered:
            raise RuntimeError(
                "git 이 인자를 인식하지 못함: {} — {}".format(argv, stderr)
            )
        if any(pat in lowered for pat in _QUIET_STDERR):
            return None
        raise RuntimeError(
            "git 명령이 실패했다(exit {}): {} — {}".format(
                out.returncode, argv, stderr or "(stderr 없음)"
            )
        )
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


def discover(
    events: Sequence[SessionEvent], config: Config
) -> tuple[list[str], dict[str, str]]:
    """(저장소 상대 경로 목록, 세션 cwd → 저장소 상대 경로 매핑).

    목록은 세션에서 발견된 것 ∪ config 등록분이다.

    cwd 매핑을 같이 돌려주는 이유는, 호출자가 이벤트를 저장소별로 접을 때
    같은 계산(git 루트로 정규화 → dev_root 상대경로)을 다시 하지 않게 하는
    것이다. 두 곳에서 따로 계산하면 규칙이 갈리는 순간 이벤트 수와
    프롬프트가 조용히 다른 저장소에 붙거나 아무 저장소에도 안 붙는다.
    세그먼트 경계 판정을 is_under 한 곳으로 모은 것과 같은 이유다.
    """
    by_cwd: dict[str, str] = {}

    for ev in events:
        if ev.cwd in by_cwd:
            continue
        root = git_root(ev.cwd)
        # git 저장소가 아니어도 근거에서 빼지 않는다 (교육 폴더 등)
        by_cwd[ev.cwd] = to_rel(root or ev.cwd, config.dev_root)

    found: set[str] = set(by_cwd.values())
    for cat in config.categories:
        found.update(cat.repos)

    return sorted(found), by_cwd
