# -*- coding: utf-8 -*-
"""근거 마크다운 렌더 테스트."""
import datetime as dt

from report.evidence import RepoEvidence, active_repos, render
from report.repos import Commit

DAY = dt.date(2026, 9, 8)
AT = dt.datetime(2026, 9, 8, 19, 30)


def ev(repo, **kw):
    base = dict(
        repo=repo, category=None, branch="main", commits=(), skipped=0,
        uncommitted=(), event_count=0, prompts=(), handoff=None, is_git=True,
    )
    base.update(kw)
    return RepoEvidence(**base)


BACKEND = ev(
    "qmeet/backend2",
    category="백엔드 공수산정",
    branch="feature/ai_effortEstimate_20260901",
    commits=(Commit("66fe6f12", "09:29", "feat: 플랫폼을 저장한다", "me@example.com"),),
    skipped=5,
    event_count=2164,
    prompts=("핸드오프 확인",),
    handoff="## Remaining Work\n\n1. 재검증이 최우선이다",
)
E2E = ev(
    "e2etest/qmeet",
    category="자동화",
    uncommitted=("?? pages/x.py", " M fixtures/auth.py"),
    event_count=1693,
)
# config.yaml 에 없는 저장소를 재현하는 합성 픽스처. 실제 저장소 이름을
# 쓰면 안 된다 — 예전에는 golfzone/admin 을 썼는데, 그 저장소는 실제로는
# 살아남은 /compact 프롬프트가 1건 있어서 운영에서 정당하게 커버리지 경고를
# 낸다. 즉 픽스처가 실제 저장소의 실제 동작과 반대되는 걸 단언하고 있었다.
UNKNOWN = ev("합성/구분없는저장소", event_count=14)
IDLE = ev("qmeet/front", category="프론트 공수산정", event_count=0)


def test_머리말에_수집시각과_집계를_적는다():
    got = render(DAY, [BACKEND, E2E], AT, is_past=False)
    assert "2026-09-08" in got
    assert "2026-09-08 19:30" in got
    assert "본인 커밋 1건" in got
    assert "타인 5건 제외" in got


def test_커버리지_표에_저장소마다_한_줄():
    got = render(DAY, [BACKEND, E2E, UNKNOWN], AT, is_past=False)
    assert "qmeet/backend2" in got
    assert "e2etest/qmeet" in got
    assert "합성/구분없는저장소" in got


def test_config_에_없는_저장소를_구분_미지정으로_표시한다():
    got = render(DAY, [UNKNOWN], AT, is_past=False)
    assert "구분 미지정" in got


def test_커밋을_시각과_해시로_싣는다():
    got = render(DAY, [BACKEND], AT, is_past=False)
    assert "09:29" in got
    assert "66fe6f12" in got
    assert "feat: 플랫폼을 저장한다" in got


def test_미커밋_줄을_싣는다():
    got = render(DAY, [E2E], AT, is_past=False)
    assert "pages/x.py" in got
    assert "fixtures/auth.py" in got


def test_인계_발췌를_싣는다():
    got = render(DAY, [BACKEND], AT, is_past=False)
    assert "재검증이 최우선이다" in got


def test_브랜치를_싣는다():
    got = render(DAY, [BACKEND], AT, is_past=False)
    assert "feature/ai_effortEstimate_20260901" in got


def test_과거_날짜면_미커밋에_신뢰_불가를_붙인다():
    got = render(DAY, [E2E], AT, is_past=True)
    assert "신뢰 불가" in got


def test_당일이면_신뢰_불가를_안_붙인다():
    got = render(DAY, [E2E], AT, is_past=False)
    assert "신뢰 불가" not in got


def test_행_초안을_만들지_않는다():
    """근거는 판단을 대신하지 않는다 — 진행률 칸이 있으면 안 된다."""
    got = render(DAY, [BACKEND, E2E], AT, is_past=False)
    assert "100%" not in got
    assert "진행률" not in got


def test_활동_없는_저장소는_활동목록에서_빠진다():
    assert active_repos([BACKEND, E2E, IDLE], is_past=False) == [
        "qmeet/backend2", "e2etest/qmeet",
    ]


def test_활동_판정에_미커밋만_있어도_포함한다():
    only_uncommitted = ev("x/y", uncommitted=(" M a.py",))
    assert active_repos([only_uncommitted], is_past=False) == ["x/y"]


def test_미커밋만_있으면_과거_날짜에서는_활동이_아니다():
    """git status 는 수집 시점 상태라 과거 날짜를 말해줄 수 없다."""
    only_uncommitted = ev("x/y", uncommitted=(" M a.py",))
    assert active_repos([only_uncommitted], is_past=False) == ["x/y"]
    assert active_repos([only_uncommitted], is_past=True) == []


def test_이벤트만_있고_커밋도_프롬프트도_없으면_활동이_아니다():
    """/compact 만 찍힌 세션처럼 사람이 시킨 일이 없으면 오늘이든 과거든 활동이 아니다."""
    events_only = ev("합성/이벤트만있는저장소", event_count=14)
    assert active_repos([events_only], is_past=False) == []
    assert active_repos([events_only], is_past=True) == []


# --- 프롬프트 상한: 잘렸다는 사실이 근거 파일에 드러나야 한다 ---


def test_프롬프트_제목에_총_건수와_실린_건수를_적는다():
    """상한이 물었는지·얼마나 물었는지를 제목만 보고 알 수 있어야 한다."""
    many = ev(
        "x/y",
        commits=(Commit("aaaaaaa", "09:00", "feat: x", "me@example.com"),),
        event_count=200,
        prompts=tuple("요청 {}".format(i) for i in range(20)),
    )
    got = render(DAY, [many], AT, is_past=False)
    assert "총 20건 중 8건" in got
    assert "요청 7" in got   # 8번째까지는 실린다
    assert "요청 8" not in got  # 9번째부터는 잘린다


def test_커밋이_없는_저장소는_프롬프트를_자르지_않는다():
    """커밋이 0건이면 프롬프트가 근거 전부다 — 자르면 그 작업이 사라진다."""
    no_commit = ev(
        "x/y",
        event_count=200,
        prompts=tuple("요청 {}".format(i) for i in range(20)),
    )
    got = render(DAY, [no_commit], AT, is_past=False)
    assert "총 20건 중 20건" in got
    assert "요청 19" in got


def test_커밋이_있으면_같은_프롬프트_수라도_잘린다():
    """같은 20건이라도 커밋이 있으면 커밋 목록이 뼈대를 잡아 주므로 자른다."""
    prompts = tuple("요청 {}".format(i) for i in range(20))
    with_commit = ev(
        "x/y",
        commits=(Commit("aaaaaaa", "09:00", "feat: x", "me@example.com"),),
        event_count=200,
        prompts=prompts,
    )
    without = ev("x/y", event_count=200, prompts=prompts)
    assert "요청 19" not in render(DAY, [with_commit], AT, is_past=False)
    assert "요청 19" in render(DAY, [without], AT, is_past=False)


def test_프롬프트가_있으면_커밋이_없어도_활동이다():
    prompted = ev("x/y", prompts=("핸드오프 확인",))
    assert active_repos([prompted], is_past=False) == ["x/y"]
    assert active_repos([prompted], is_past=True) == ["x/y"]


def test_커밋이_있으면_항상_활동이다():
    committed = ev(
        "x/y",
        commits=(Commit("66fe6f12", "09:29", "feat: x", "me@example.com"),),
    )
    assert active_repos([committed], is_past=False) == ["x/y"]
    assert active_repos([committed], is_past=True) == ["x/y"]


def test_비git_저장소도_렌더된다():
    edu = ev("leadwalk_study/2026/x", category="교육", branch=None,
             is_git=False, event_count=807)
    got = render(DAY, [edu], AT, is_past=False)
    assert "leadwalk_study/2026/x" in got
    assert "git 아님" in got
