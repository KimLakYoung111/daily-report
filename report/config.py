# -*- coding: utf-8 -*-
"""config.yaml 로딩과 검증.

사람이 관리하는 값만 담는다 — 본인 식별, 구분 목록, 저장소 매핑,
모듈 진행률, 수집 루트, 걸러낼 자동 세션 프롬프트.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

import yaml

PROGRESS_RE = re.compile(r"^\d{1,3}%$")


class ConfigError(Exception):
    """config.yaml 이 규칙에 맞지 않을 때."""


def normalize_repo(value: str) -> str:
    """저장소 상대 경로의 구분자를 / 로 맞추고 양끝 슬래시를 없앤다."""
    return str(value).replace("\\", "/").strip("/")


def is_under(parent: str, child: str) -> bool:
    """child 가 parent 자신이거나 parent 아래(경로 세그먼트 경계 기준)에 있는지.

    양쪽 다 normalize_repo 로 정규화한 뒤 비교한다. 예를 들어 a/b 는
    a/bc 를 덮지 않는다 — 세그먼트 경계(/) 없이 문자열만 접두하면 안 된다.
    """
    p = normalize_repo(parent)
    c = normalize_repo(child)
    return c == p or c.startswith(p + "/")


@dataclass(frozen=True)
class Category:
    name: str
    progress: str | None = None
    repos: tuple[str, ...] = ()
    by_content: bool = False


@dataclass(frozen=True)
class Config:
    me: tuple[str, ...]
    categories: tuple[Category, ...]
    dev_root: str
    ignore_prompts: tuple[str, ...] = ()
    # dict 은 해시가 안 되므로 eq/hash 에서 뺀다. 안 빼면 frozen 데이터클래스가
    # 만드는 __hash__ 가 터진다.
    _by_repo: dict[str, str] = field(
        default_factory=dict, repr=False, compare=False
    )

    def category(self, name: str) -> Category | None:
        for c in self.categories:
            if c.name == name:
                return c
        return None

    def category_for_repo(self, repo: str) -> str | None:
        """저장소 상대 경로로 구분 이름을 찾는다.

        일부 구분은 저장소 하나가 아니라 git 저장소 여러 개를 품은
        상위 폴더를 등록해 둔다(예: 교육 — 교육생 5명 폴더 아래 각자
        저장소). 그래서 정확히 일치하는 등록이 없어도, 등록된 경로가
        조회 경로의 상위 경로(경로 세그먼트 경계 기준)면 그 구분을
        돌려준다. 후보가 여럿이면 가장 긴(가장 구체적인) 등록이 이긴다
        — 정확 일치는 항상 자신보다 짧은 프리픽스보다 길므로 자동으로
        우선한다.
        """
        best_name: str | None = None
        best_len = -1
        for p, name in self._by_repo.items():
            if is_under(p, repo):
                if len(p) > best_len:
                    best_len = len(p)
                    best_name = name
        return best_name

    def order_index(self, name: str) -> int:
        for i, c in enumerate(self.categories):
            if c.name == name:
                return i
        return len(self.categories)

    def label(self, name: str) -> str:
        c = self.category(name)
        if c is None or not c.progress:
            return name
        return "{}({})".format(c.name, c.progress)


def load_config(path: str | Path) -> Config:
    raw = yaml.safe_load(Path(path).read_text(encoding="utf-8")) or {}

    me = tuple(str(x) for x in (raw.get("me") or []))
    if not me:
        raise ConfigError("me 목록이 비어 있다 — 본인 커밋을 가려낼 수 없다")

    dev_root = str(raw.get("dev_root") or "").rstrip("\\/")
    if not dev_root:
        raise ConfigError("dev_root 가 없다")

    categories: list[Category] = []
    seen_names: set[str] = set()
    by_repo: dict[str, str] = {}

    for entry in raw.get("categories") or []:
        name = str(entry.get("name") or "").strip()
        if not name:
            raise ConfigError("이름 없는 구분이 있다")
        if name in seen_names:
            raise ConfigError("구분 이름이 중복된다: {}".format(name))
        seen_names.add(name)

        progress = entry.get("progress")
        if progress is not None:
            progress = str(progress).strip()
            if not PROGRESS_RE.match(progress):
                raise ConfigError(
                    "진행률 형식이 아니다 ({} → {!r}) — 'NN%' 로 적는다".format(
                        name, progress
                    )
                )

        repos = tuple(normalize_repo(r) for r in (entry.get("repos") or []))
        for r in repos:
            if r in by_repo:
                raise ConfigError(
                    "저장소 {} 가 두 구분에 속한다: {} / {}".format(
                        r, by_repo[r], name
                    )
                )
            by_repo[r] = name

        categories.append(
            Category(
                name=name,
                progress=progress,
                repos=repos,
                by_content=bool(entry.get("by_content")),
            )
        )

    if not categories:
        raise ConfigError("categories 가 비어 있다")

    return Config(
        me=me,
        categories=tuple(categories),
        dev_root=dev_root,
        ignore_prompts=tuple(str(x) for x in (raw.get("ignore_prompts") or [])),
        _by_repo=by_repo,
    )
