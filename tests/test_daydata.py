# -*- coding: utf-8 -*-
"""날짜 데이터 파일 로딩·검증 테스트."""
import pytest

from report.config import Category, Config
from report.daydata import (
    DayDataError,
    Location,
    coverage_warnings,
    load_day,
)

CFG = Config(
    me=("me@example.com",),
    categories=(
        Category(name="백엔드 공수산정", progress="85%", repos=("qmeet/backend2",)),
        Category(name="자동화", repos=("e2etest/qmeet", "e2etest/playwright_base")),
        Category(name="교육", repos=("study",)),
    ),
    dev_root=r"C:\Users\klyhj\dev",
)

SAMPLE = """\
date: 2026.9.08
rows:
  - category: 자동화
    default_location: { repo: e2etest/qmeet, branch: main }
    items:
      - task: 프로젝트 등록 TC 명세 작성
        progress: 80%
        note: QM103 확정 대기
      - task: TC 입력 양식 제정
        progress: 100%
        locations:
          - { repo: e2etest/playwright_base, branch: main }
          - { repo: e2etest/qmeet, branch: main }
  - category: 백엔드 공수산정
    default_location: { repo: qmeet/backend2, branch: feature/x }
    items:
      - task: 추천 환경 저장
        progress: 100%
"""


def write(tmp_path, text):
    p = tmp_path / "2026-09-08.yaml"
    p.write_text(text, encoding="utf-8")
    return p


def test_날짜와_행을_읽는다(tmp_path):
    rep, warns = load_day(write(tmp_path, SAMPLE), CFG)
    assert rep.date == "2026.9.08"
    assert len(rep.rows) == 2
    assert warns == []


def test_구분을_config_순서로_정렬한다(tmp_path):
    """파일에는 자동화가 먼저 나오지만 config 순서는 백엔드가 앞이다."""
    rep, _ = load_day(write(tmp_path, SAMPLE), CFG)
    assert [r.category for r in rep.rows] == ["백엔드 공수산정", "자동화"]


def test_항목_순서는_파일_순서를_지킨다(tmp_path):
    rep, _ = load_day(write(tmp_path, SAMPLE), CFG)
    auto = [r for r in rep.rows if r.category == "자동화"][0]
    assert [i.task for i in auto.items] == [
        "프로젝트 등록 TC 명세 작성",
        "TC 입력 양식 제정",
    ]


def test_locations_없으면_default_location_을_쓴다(tmp_path):
    rep, _ = load_day(write(tmp_path, SAMPLE), CFG)
    auto = [r for r in rep.rows if r.category == "자동화"][0]
    assert auto.items[0].locations == (Location("e2etest/qmeet", "main"),)


def test_locations_가_있으면_default_를_무시한다(tmp_path):
    rep, _ = load_day(write(tmp_path, SAMPLE), CFG)
    auto = [r for r in rep.rows if r.category == "자동화"][0]
    assert auto.items[1].locations == (
        Location("e2etest/playwright_base", "main"),
        Location("e2etest/qmeet", "main"),
    )


def test_note_는_생략_가능하고_빈_문자열이_된다(tmp_path):
    rep, _ = load_day(write(tmp_path, SAMPLE), CFG)
    auto = [r for r in rep.rows if r.category == "자동화"][0]
    assert auto.items[0].note == "QM103 확정 대기"
    assert auto.items[1].note == ""


def test_config_에_없는_구분이면_에러(tmp_path):
    text = SAMPLE.replace("category: 자동화", "category: 자동회")  # 오타
    with pytest.raises(DayDataError, match="config.yaml 에 없는 구분"):
        load_day(write(tmp_path, text), CFG)


def test_진행률_형식이_틀리면_에러(tmp_path):
    with pytest.raises(DayDataError, match="진행률 형식"):
        load_day(write(tmp_path, SAMPLE.replace("progress: 80%", "progress: 진행중")), CFG)


def test_진행률이_없으면_에러(tmp_path):
    text = SAMPLE.replace("        progress: 80%\n", "")
    with pytest.raises(DayDataError, match="진행률"):
        load_day(write(tmp_path, text), CFG)


def test_작업명이_비면_에러(tmp_path):
    text = SAMPLE.replace("task: 추천 환경 저장", 'task: ""')
    with pytest.raises(DayDataError, match="작업명"):
        load_day(write(tmp_path, text), CFG)


def test_date_가_없으면_에러(tmp_path):
    text = SAMPLE.replace("date: 2026.9.08\n", "")
    with pytest.raises(DayDataError, match="date"):
        load_day(write(tmp_path, text), CFG)


def test_항목이_없는_구분이면_에러(tmp_path):
    text = "date: 2026.9.08\nrows:\n  - category: 자동화\n    default_location: { repo: e2etest/qmeet, branch: main }\n    items: []\n"
    with pytest.raises(DayDataError, match="항목이 없"):
        load_day(write(tmp_path, text), CFG)


def test_같은_구분이_두_번_나오면_에러(tmp_path):
    text = SAMPLE + """\
  - category: 자동화
    default_location: { repo: e2etest/qmeet, branch: main }
    items:
      - task: 중복이다
        progress: 100%
"""
    with pytest.raises(DayDataError, match="구분이 두 번"):
        load_day(write(tmp_path, text), CFG)


def test_없는_저장소는_경고만_낸다(tmp_path):
    text = SAMPLE.replace("repo: qmeet/backend2", "repo: qmeet/없는저장소")
    rep, warns = load_day(write(tmp_path, text), CFG)
    assert len(rep.rows) == 2  # 실패하지 않는다
    assert any("없는저장소" in w for w in warns)


def test_저장소_경로_구분자를_정규화한다(tmp_path):
    text = SAMPLE.replace("repo: qmeet/backend2", r"repo: qmeet\backend2")
    rep, _ = load_day(write(tmp_path, text), CFG)
    be = [r for r in rep.rows if r.category == "백엔드 공수산정"][0]
    assert be.items[0].locations[0].repo == "qmeet/backend2"


def test_근거에_있는데_표에_없는_저장소를_지적한다(tmp_path):
    rep, _ = load_day(write(tmp_path, SAMPLE), CFG)
    active = ["e2etest/qmeet", "qmeet/backend2", "qmeet/qmeet-dev-ssh"]
    warns = coverage_warnings(rep, active)
    assert len(warns) == 1
    assert "qmeet/qmeet-dev-ssh" in warns[0]


def test_모두_반영됐으면_커버리지_경고가_없다(tmp_path):
    rep, _ = load_day(write(tmp_path, SAMPLE), CFG)
    active = ["e2etest/qmeet", "e2etest/playwright_base", "qmeet/backend2"]
    assert coverage_warnings(rep, active) == []


# --- coverage_warnings: 상위 폴더 등록이 하위 저장소를 흡수하는지 ---
#
# 일부 구분은 저장소 하나가 아니라 여러 git 저장소를 품은 상위 폴더를
# 등록해 둔다(예: leadwalk_study/2026/second-half-automation-training/repos
# 아래 교육생 5명 폴더 각자가 독립된 git 저장소). 단순 집합 멤버십으로
# 비교하면 이런 구성마다 스푸리어스 경고가 쏟아져 경고 목록을 아무도
# 안 읽게 된다 — 그게 바로 이 도구가 잡으려는 실패 모드다.
#
# 위 두 기존 테스트(test_근거에_있는데_표에_없는_저장소를_지적한다,
# test_모두_반영됐으면_커버리지_경고가_없다)가 이미 "무관한 저장소는
# 경고한다"와 "정확 일치는 경고 없다"를 검증하므로, 여기서는 흡수
# 규칙 자체를 가르는 두 경우만 추가한다.

SAMPLE_PARENT_REPO = """\
date: 2026.9.08
rows:
  - category: 교육
    default_location: { repo: study, branch: main }
    items:
      - task: 교육생 진도 확인
        progress: 50%
"""


def test_상위_폴더가_참조되면_하위_활동_저장소는_경고_없다(tmp_path):
    """정확 일치가 아니라 상위 경로만 표에 적혀도, 그 아래 활동 저장소는
    흡수되어 경고가 나지 않는다 — 교육생 5명 폴더가 실제 사례다."""
    text = SAMPLE_PARENT_REPO.replace("repo: study", "repo: leadwalk_study/2026/second-half-automation-training/repos")
    rep, _ = load_day(write(tmp_path, text), CFG)
    active = [
        "leadwalk_study/2026/second-half-automation-training/repos/automation-study-eunchae",
        "leadwalk_study/2026/second-half-automation-training/repos/automation-study-jimin",
    ]
    assert coverage_warnings(rep, active) == []


def test_형제_경로는_흡수하지_않는다(tmp_path):
    """qmeet/front 가 표에 있어도, 그 아래 nested 저장소는 흡수되지만
    qmeet/front_design_prototype 은 형제 경로(다른 구분)라 여전히 경고한다."""
    text = SAMPLE_PARENT_REPO.replace("repo: study", "repo: qmeet/front")
    rep, _ = load_day(write(tmp_path, text), CFG)
    active = [
        "qmeet/front/cypress-example-kitchensink",  # nested — 흡수돼야 한다
        "qmeet/front_design_prototype",  # 형제 경로 — 경고가 남아야 한다
    ]
    warns = coverage_warnings(rep, active)
    assert len(warns) == 1
    assert "qmeet/front_design_prototype" in warns[0]
