# -*- coding: utf-8 -*-
"""data/YYYY-MM-DD.yaml 로딩과 검증.

사람이 근거를 읽고 판단한 결과만 담는다. 구분 순서는 config.yaml 을 따르고
파일 순서는 무시한다 — 날짜별로 구분이 뒤바뀌면 추이를 못 본다.
"""
from __future__ import annotations

import datetime as dt
import re
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

import yaml

from .config import PROGRESS_RE, Config, is_under, normalize_repo

#: date 라벨은 자유 형식이다("2026.9.08", "2026-09-08", "2026.9.8 (화)" …).
#: 연·월·일 세 덩어리만 뽑아 파일명과 맞춰 본다.
_DATE_IN_LABEL = re.compile(r"(\d{4})\D+(\d{1,2})\D+(\d{1,2})")


class DayDataError(Exception):
    """날짜 데이터 파일이 규칙에 맞지 않을 때."""


def _parse_label_date(text: str) -> dt.date | None:
    """자유 형식 문자열에서 날짜를 뽑는다. 못 읽으면 None."""
    m = _DATE_IN_LABEL.search(text)
    if not m:
        return None
    try:
        return dt.date(*(int(g) for g in m.groups()))
    except ValueError:
        return None


@dataclass(frozen=True)
class Location:
    repo: str
    branch: str


@dataclass(frozen=True)
class Item:
    task: str
    progress: str
    note: str = ""
    locations: tuple[Location, ...] = ()


@dataclass(frozen=True)
class Row:
    category: str
    items: tuple[Item, ...]


@dataclass(frozen=True)
class DayReport:
    date: str
    rows: tuple[Row, ...]


def _location(raw: dict, where: str) -> Location:
    if not isinstance(raw, dict):
        raise DayDataError("{}: 위치는 repo·branch 를 가진 매핑이어야 한다".format(where))
    repo = normalize_repo(str(raw.get("repo") or ""))
    if not repo:
        raise DayDataError("{}: repo 가 비었다".format(where))
    return Location(repo=repo, branch=str(raw.get("branch") or "").strip())


def load_day(path: str | Path, config: Config) -> tuple[DayReport, list[str]]:
    """(보고서, 경고 목록). 규칙 위반은 DayDataError."""
    path = Path(path)
    raw = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    if not isinstance(raw, dict):
        raise DayDataError(
            "{}: 파일 최상단이 date·rows 를 가진 매핑이어야 한다".format(path.name)
        )
    warnings: list[str] = []

    date_label = str(raw.get("date") or "").strip()
    if not date_label:
        raise DayDataError("{}: date 가 없다".format(path.name))

    # 어제 파일을 틀로 복사해 date 만 안 고치는 실수를 여기서 잡는다.
    # 그냥 두면 A열에 어제 날짜가 박힌 문서가 대표님께 가는데, 커버리지
    # 검사는 파일명으로 사이드카를 찾으므로 경고 하나 없이 통과한다.
    stem_date = _parse_label_date(path.stem)
    if stem_date is not None:
        label_date = _parse_label_date(date_label)
        if label_date is None:
            warnings.append(
                "date 를 날짜로 읽을 수 없어 파일명과 비교하지 못했다: {!r}".format(
                    date_label
                )
            )
        elif label_date != stem_date:
            raise DayDataError(
                "{}: date 가 파일명과 다르다 — {!r} (파일명은 {})".format(
                    path.name, date_label, stem_date.isoformat()
                )
            )

    raw_rows = raw.get("rows") or []
    if not isinstance(raw_rows, list):
        raise DayDataError("{}: rows 는 목록이어야 한다".format(path.name))

    rows: list[Row] = []
    seen: set[str] = set()

    for entry in raw_rows:
        if not isinstance(entry, dict):
            raise DayDataError(
                "{}: 구분은 category·items 를 가진 매핑이어야 한다 — {!r}".format(
                    path.name, entry
                )
            )
        category = str(entry.get("category") or "").strip()
        if config.category(category) is None:
            raise DayDataError(
                "{}: config.yaml 에 없는 구분이다 — {!r}".format(path.name, category)
            )
        if category in seen:
            raise DayDataError(
                "{}: 같은 구분이 두 번 나온다 — {!r}".format(path.name, category)
            )
        seen.add(category)

        where = "{} / {}".format(path.name, category)
        default_raw = entry.get("default_location")
        default = _location(default_raw, where) if default_raw else None

        raw_items = entry.get("items") or []
        if not isinstance(raw_items, list):
            raise DayDataError("{}: items 는 목록이어야 한다".format(where))
        if not raw_items:
            raise DayDataError("{}: 항목이 없는 구분이다".format(where))

        items: list[Item] = []
        for raw_item in raw_items:
            if not isinstance(raw_item, dict):
                raise DayDataError(
                    "{}: 항목은 task·progress 를 가진 매핑이어야 한다 — {!r}".format(
                        where, raw_item
                    )
                )
            task = str(raw_item.get("task") or "").strip()
            if not task:
                raise DayDataError("{}: 작업명이 비었다".format(where))

            progress = str(raw_item.get("progress") or "").strip()
            if not PROGRESS_RE.match(progress):
                raise DayDataError(
                    "{} / {}: 진행률 형식이 아니다 ({!r}) — 'NN%' 로 적는다".format(
                        where, task, progress
                    )
                )

            raw_locs = raw_item.get("locations")
            if raw_locs:
                locations = tuple(
                    _location(x, "{} / {}".format(where, task)) for x in raw_locs
                )
            elif default is not None:
                locations = (default,)
            else:
                raise DayDataError(
                    "{} / {}: locations 도 default_location 도 없다".format(where, task)
                )

            items.append(
                Item(
                    task=task,
                    progress=progress,
                    note=str(raw_item.get("note") or "").strip(),
                    locations=locations,
                )
            )

        rows.append(Row(category=category, items=tuple(items)))

    if not rows:
        raise DayDataError("{}: rows 가 비었다".format(path.name))

    # 저장소 폴더 존재는 경고만 — 비git 경로·삭제된 저장소를 허용한다
    dev_root = Path(config.dev_root)
    for row in rows:
        for item in row.items:
            for loc in item.locations:
                if not (dev_root / loc.repo).exists():
                    warnings.append(
                        "저장소 폴더가 없다: {} ({} / {})".format(
                            loc.repo, row.category, item.task
                        )
                    )

    rows.sort(key=lambda r: config.order_index(r.category))
    return DayReport(date=date_label, rows=tuple(rows)), warnings


def coverage_warnings(report: DayReport, active: Sequence[str]) -> list[str]:
    """근거에는 활동이 있는데 표에 한 줄도 없는 저장소를 지적한다.

    2026-09-08 e2etest/qmeet 의 작업 6행을 놓친 사고를 여기서 잡는다.

    표에 적힌 저장소 P 는 활동 저장소 Q 가 P 자신이거나 P 아래(경로
    세그먼트 경계 기준)에 있을 때 Q 를 덮는다 — config.py 의
    category_for_repo 와 같은 규칙(is_under)이다. 상위 폴더 하나에
    git 저장소 여러 개가 걸린 구성(예: 교육생 5명 폴더, qmeet/front
    아래의 cypress-example-kitchensink)에서 표에는 부모 경로만 적기
    때문에, 단순 집합 멤버십으로 비교하면 매번 스푸리어스 경고가
    쏟아져 아무도 경고 목록을 읽지 않게 된다. 단, 형제 경로는 절대
    흡수하지 않는다 — qmeet/front 는 qmeet/front_design_prototype 을
    덮지 않는다. 이 둘은 서로 다른 구분(시안 vs 프론트 공수산정)이고,
    그 경계를 뭉개는 것이 바로 이 도구가 잡아야 할 누락이다.
    """
    used = {
        loc.repo
        for row in report.rows
        for item in row.items
        for loc in item.locations
    }
    return [
        "근거에는 활동이 있는데 표에 없다: {}".format(repo)
        for repo in active
        if not any(is_under(p, repo) for p in used)
    ]
