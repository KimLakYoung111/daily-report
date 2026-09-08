#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""일일보고 엑셀 생성 — data/*.yaml 을 읽어 기존 보고 양식으로 렌더한다.

사용법:
    python build_report.py            # data/ 아래 전체 날짜
    python build_report.py 2026.9.8   # 특정 날짜

출력: output/일일보고-YYYY-MM-DD.xlsx (+ .tsv)
근거는 collect_evidence.py 가 모은다. 판단은 사람이 data/*.yaml 에 쓴다.
"""
from __future__ import annotations

import datetime as dt
import json
import sys
from pathlib import Path

from report.config import load_config
from report.daydata import DayDataError, coverage_warnings, load_day
from report.excel import write_tsv, write_xlsx

HERE = Path(__file__).resolve().parent
DATA_DIR = HERE / "data"
OUT_DIR = HERE / "output"
EVIDENCE_DIR = OUT_DIR / "evidence"


def data_path(day_arg: str) -> Path:
    """'2026.9.8' → data/2026-09-08.yaml. 날짜가 아니면 ValueError."""
    y, m, d = (int(x) for x in day_arg.replace("-", ".").split("."))
    return DATA_DIR / "{}.yaml".format(dt.date(y, m, d).isoformat())


def active_repos_for(stem: str) -> list[str] | None:
    """근거 사이드카의 활동 저장소 목록. 파일 자체가 없으면 None.

    "사이드카가 없다"(근거를 아직 안 모았다)와 "사이드카는 있는데 활동
    저장소가 0곳이다"(정말 활동이 없었거나 수집이 아무것도 못 잡았다)는
    다른 상황이고 해야 할 조치도 다르다. 둘 다 빈 목록으로 뭉개면
    사용자가 근거를 안 모은 건지 모으고도 비었는지 알 수 없다.
    """
    path = EVIDENCE_DIR / "{}.repos.json".format(stem)
    if not path.is_file():
        return None
    try:
        return list(json.loads(path.read_text(encoding="utf-8")))
    except (ValueError, OSError):
        return []


def build_one(path: Path, config) -> int:
    print("== {} ==".format(path.stem))
    report, warnings = load_day(path, config)

    for warn in warnings:
        print("  [경고] {}".format(warn))

    active = active_repos_for(path.stem)
    if active is None:
        print("  [경고] 근거 사이드카가 없다 — 커버리지를 확인하지 못했다. "
              "`python collect_evidence.py {}` 를 먼저 돌린다.".format(report.date))
        active = []
    elif not active:
        print("  [경고] 근거 사이드카는 있는데 활동 저장소가 0곳이다 — "
              "커버리지 검사가 아무것도 걸러내지 못한다. 그날 정말 활동이 "
              "없었는지 근거 파일을 확인한다.")
    for warn in coverage_warnings(report, active):
        print("  [경고] {}".format(warn))

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    stem = "일일보고-{}".format(path.stem)

    xlsx_path, total = write_xlsx(report, config, OUT_DIR / (stem + ".xlsx"))
    tsv_path = write_tsv(report, config, OUT_DIR / (stem + ".tsv"))

    for written in (xlsx_path, tsv_path):
        if written.name.startswith("_"):
            print("  [대기] 원본이 열려 있어 {} 로 저장했다".format(written.name))
    print("  {}  ({}행 x 6열)".format(xlsx_path.relative_to(HERE), total))
    print("  {}".format(tsv_path.relative_to(HERE)))
    return total


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8")
    config = load_config(HERE / "config.yaml")

    if len(sys.argv) > 1:
        paths = []
        for arg in sys.argv[1:]:
            try:
                p = data_path(arg)
            except ValueError:
                print("[에러] 날짜를 읽을 수 없다: {!r}".format(arg))
                print("       사용법: python build_report.py [YYYY.M.D]  "
                      "(예: 2026.9.8)")
                return 1
            if not p.is_file():
                print("[없음] {} — 먼저 근거를 보고 이 파일을 쓴다".format(
                    p.relative_to(HERE)))
                return 1
            paths.append(p)
    else:
        # 날짜 모양만 고른다. `*.yaml` 로 훑으면 _template.yaml 같은 파일이
        # 그대로 일일보고-_template.xlsx 로 나가버린다.
        paths = sorted(DATA_DIR.glob("[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9].yaml"))
        if not paths:
            print("[없음] data/ 에 날짜 파일이 없다")
            return 1

    failed = 0
    for path in paths:
        try:
            build_one(path, config)
        except DayDataError as exc:
            print("  [에러] {}".format(exc))
            failed += 1
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
