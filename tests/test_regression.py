# -*- coding: utf-8 -*-
"""실제 config.yaml·data/*.yaml 회귀 테스트.

2026-09-08 손으로 만든 엑셀(20행이라 여겼으나, 이 파이프라인이 시안 구분
누락을 잡아내 21행이 맞다)과 2026-09-07(17행)의 행 수·구분 순서를
새 파이프라인이 재현하는지 본다.
"""
from pathlib import Path

import pytest
import yaml

from report.config import load_config
from report.daydata import load_day
from report.excel import flatten

ROOT = Path(__file__).resolve().parent.parent
DAY_FILES = sorted((ROOT / "data").glob("[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9].yaml"))


@pytest.fixture(scope="module")
def config():
    return load_config(ROOT / "config.yaml")


def test_실제_config_가_로딩된다(config):
    """구분 개수는 못 박지 않는다.

    예전에는 `len(config.categories) == 9` 였는데, 사용자가 구분을 하나
    더하는 정상적인 편집만으로 테스트가 깨졌다. 대신 비어 있지 않은지와,
    data/*.yaml 이 실제로 참조하는 구분이 config 에 다 있는지를 본다.
    """
    assert config.categories

    referenced: set[str] = set()
    for path in DAY_FILES:
        raw = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        for entry in raw.get("rows") or []:
            referenced.add(str(entry.get("category") or "").strip())
    assert referenced, "data/*.yaml 이 구분을 하나도 참조하지 않는다"

    missing = sorted(n for n in referenced if config.category(n) is None)
    assert missing == [], "config.yaml 에 없는 구분: {}".format(missing)

    # 백엔드 공수산정은 config.yaml 에 display: "백엔드\n공수산정" 이 있어
    # 실제 엑셀의 구분 칸처럼 두 줄로 나온다 — 손으로 만든 시트를 그대로
    # 재현한다. 진행률 숫자는 사람이 고치는 값이므로 못 박지 않고,
    # 줄바꿈이 살아 있는지만 본다.
    label = config.label("백엔드 공수산정")
    assert label.startswith("백엔드\n공수산정(")
    assert label.endswith("%)")


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


def test_최신_날짜_파일에_경고가_없다(config):
    """저장소 폴더가 실제로 다 있어야 한다 — 오타를 여기서 잡는다.

    두 가지를 좁혔다.

    첫째, dev_root 는 이 사용자 기계의 경로다. 없는 환경(CI·다른 기계)에서는
    검사 자체가 성립하지 않으므로 건너뛴다. 예전에는 그대로 실패했다.

    둘째, 폴더 존재를 단언하는 대상은 가장 최신 날짜 파일 하나뿐이다.
    저장소를 옮기거나 이름을 바꾸면 과거 날짜 파일은 영구히 못 맞추게 되고
    (그날 그 경로였다는 건 바꿀 수 없는 사실이다), data/ 가 쌓이는 만큼
    테스트가 끝없이 무거워진다. 오타는 오늘 쓰는 파일에서 생기므로 최신
    파일만 단언해도 잡으려던 실수는 그대로 잡힌다. 과거 파일은 출력만 한다.
    """
    if not Path(config.dev_root).is_dir():
        pytest.skip(
            "dev_root 가 없다 ({}) — 이 기계의 폴더 구성에만 의존하는 검사다".format(
                config.dev_root
            )
        )

    assert DAY_FILES, "data/ 에 날짜 파일이 없다"

    for path in DAY_FILES[:-1]:
        _, warnings = load_day(path, config)
        if warnings:
            print("[참고] {} (과거 파일이라 단언하지 않는다): {}".format(
                path.name, warnings))

    latest = DAY_FILES[-1]
    _, warnings = load_day(latest, config)
    assert warnings == [], "{}: {}".format(latest.name, warnings)
