# -*- coding: utf-8 -*-
"""config.yaml 로딩과 검증.

사람이 관리하는 값만 담는다 — 본인 식별, 구분 목록, 저장소 매핑,
모듈 진행률, 수집 루트, 걸러낼 자동 세션 프롬프트.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
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
    # 매칭 키(name)와 화면 표기를 분리한다. 예: 이름은 "백엔드 공수산정"
    # 그대로 두고, 표기만 "백엔드\n공수산정"처럼 줄바꿈을 넣고 싶을 때 쓴다.
    display: str | None = None


@dataclass(frozen=True)
class Config:
    me: tuple[str, ...]
    categories: tuple[Category, ...]
    dev_root: str
    ignore_prompts: tuple[str, ...] = ()

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

        categories 를 직접 훑는다. 예전에는 load_config 가 만든 저장소→구분
        딕셔너리를 캐시로 들고 있었는데, 프리픽스 매칭으로 바뀐 뒤로는
        어차피 전부 훑어 가장 긴 일치를 찾아야 해서 아무것도 아껴 주지
        않았다. 반면 Config 를 직접 만들면(테스트가 그렇게 한다) 그 캐시가
        비어 있어, categories[].repos 에 값이 있는데도 None 이 나오는
        조용한 오답이 됐다.
        """
        best_name: str | None = None
        best_len = -1
        for cat in self.categories:
            for p in cat.repos:
                if is_under(p, repo) and len(p) > best_len:
                    best_len = len(p)
                    best_name = cat.name
        return best_name

    def order_index(self, name: str) -> int:
        for i, c in enumerate(self.categories):
            if c.name == name:
                return i
        return len(self.categories)

    def label(self, name: str) -> str:
        c = self.category(name)
        if c is None:
            return name
        base = c.display or c.name
        if not c.progress:
            return base
        return "{}({})".format(base, c.progress)


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
    # 한 저장소가 두 구분에 걸리는 설정 오류를 잡기 위한 장부. 로딩이 끝나면
    # 버린다 — 조회는 category_for_repo 가 categories 를 직접 훑는다.
    seen_repos: dict[str, str] = {}

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
            if r in seen_repos:
                raise ConfigError(
                    "저장소 {} 가 두 구분에 속한다: {} / {}".format(
                        r, seen_repos[r], name
                    )
                )
            seen_repos[r] = name

        display = entry.get("display")
        if display is not None:
            display = str(display)

        categories.append(
            Category(
                name=name,
                progress=progress,
                repos=repos,
                by_content=bool(entry.get("by_content")),
                display=display,
            )
        )

    if not categories:
        raise ConfigError("categories 가 비어 있다")

    return Config(
        me=me,
        categories=tuple(categories),
        dev_root=dev_root,
        ignore_prompts=tuple(str(x) for x in (raw.get("ignore_prompts") or [])),
    )
