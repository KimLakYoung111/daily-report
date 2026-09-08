# -*- coding: utf-8 -*-
"""실제 config.yaml·data/*.yaml 회귀 테스트.

2026-09-08 손으로 만든 엑셀(20행이라 여겼으나, 이 파이프라인이 시안 구분
누락을 잡아내 21행이 맞다)과 2026-09-07(17행)의 행 수·구분 순서를
새 파이프라인이 재현하는지 본다.
"""
from pathlib import Path

import pytest

from report.config import load_config
from report.daydata import load_day
from report.excel import flatten

ROOT = Path(__file__).resolve().parent.parent


@pytest.fixture(scope="module")
def config():
    return load_config(ROOT / "config.yaml")


def test_실제_config_가_로딩된다(config):
    assert len(config.categories) == 9
    # 백엔드 공수산정은 config.yaml 에 display: "백엔드\n공수산정" 이 있어
    # 실제 엑셀의 구분 칸처럼 두 줄로 나온다 — 손으로 만든 시트를 그대로 재현한다.
    assert config.label("백엔드 공수산정") == "백엔드\n공수산정(85%)"


@pytest.mark.parametrize(
    "stem, expected_rows",
    [("2026-09-07", 17), ("2026-09-08", 21)],
)
def test_행_수가_손으로_만든_보고서와_같다(config, stem, expected_rows):
    report, _ = load_day(ROOT / "data" / "{}.yaml".format(stem), config)
    assert len(flatten(report, config)) == expected_rows


def test_구분이_config_순서로_나온다(config):
    report, _ = load_day(ROOT / "data" / "2026-09-08.yaml", config)
    assert [r.category for r in report.rows] == [
        "백엔드 공수산정",
        "프론트 공수산정",
        "AI 서버 공수산정",
        "시안",
        "인프라",
        "자동화",
        "교육",
    ]


def test_9월7일_구분에_시안과_GA4_가_있다(config):
    report, _ = load_day(ROOT / "data" / "2026-09-07.yaml", config)
    names = [r.category for r in report.rows]
    assert "시안" in names
    assert "GA4" in names
    # GA4 는 config 에서 자동화보다 앞이다
    assert names.index("GA4") < names.index("자동화")


def test_TC_입력_양식_항목은_저장소가_두_곳이다(config):
    report, _ = load_day(ROOT / "data" / "2026-09-08.yaml", config)
    auto = [r for r in report.rows if r.category == "자동화"][0]
    item = [i for i in auto.items if i.task == "TC 입력 양식 제정"][0]
    assert len(item.locations) == 2


def test_모든_날짜_파일에_경고가_없다(config):
    """저장소 폴더가 실제로 다 있어야 한다 — 오타를 여기서 잡는다."""
    for path in sorted((ROOT / "data").glob("*.yaml")):
        _, warnings = load_day(path, config)
        assert warnings == [], "{}: {}".format(path.name, warnings)
