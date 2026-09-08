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
    """'2026.9.8' → data/2026-09-08.yaml"""
    y, m, d = (int(x) for x in day_arg.replace("-", ".").split("."))
    return DATA_DIR / "{}-{:02d}-{:02d}.yaml".format(y, m, d)


def active_repos_for(stem: str) -> list[str]:
    """근거 사이드카에서 활동 있던 저장소 목록을 읽는다. 없으면 빈 목록."""
    path = EVIDENCE_DIR / "{}.repos.json".format(stem)
    if not path.is_file():
        return []
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
    if not active:
        print("  [경고] 근거 사이드카가 없다 — 커버리지를 확인하지 못했다. "
              "`python collect_evidence.py {}` 를 먼저 돌린다.".format(report.date))
    for warn in coverage_warnings(report, active):
        print("  [경고] {}".format(warn))

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    stem = "일일보고-{}".format(path.stem)

    xlsx_path, total = write_xlsx(report, config, OUT_DIR / (stem + ".xlsx"))
    write_tsv(report, config, OUT_DIR / (stem + ".tsv"))

    if xlsx_path.name.startswith("_"):
        print("  [대기] 원본이 열려 있어 {} 로 저장했다".format(xlsx_path.name))
    print("  {}  ({}행 x 6열)".format(xlsx_path.relative_to(HERE), total))
    print("  {}".format((OUT_DIR / (stem + ".tsv")).relative_to(HERE)))
    return total


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8")
    config = load_config(HERE / "config.yaml")

    if len(sys.argv) > 1:
        paths = []
        for arg in sys.argv[1:]:
            p = data_path(arg)
            if not p.is_file():
                print("[없음] {} — 먼저 근거를 보고 이 파일을 쓴다".format(
                    p.relative_to(HERE)))
                return 1
            paths.append(p)
    else:
        paths = sorted(DATA_DIR.glob("*.yaml"))
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
