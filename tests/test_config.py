# -*- coding: utf-8 -*-
"""config.yaml 로딩·검증 테스트."""
import pytest

from report.config import Config, ConfigError, load_config

SAMPLE = """\
me:
  - klyhja@l-walk.com
  - 61999720+KimLakYoung111@users.noreply.github.com
categories:
  - name: 백엔드 공수산정
    progress: 85%
    repos: [qmeet/backend2]
  - name: GA4
    by_content: true
  - name: 자동화
    repos: [e2etest/qmeet, e2etest/playwright_base]
dev_root: C:\\Users\\klyhj\\dev
ignore_prompts:
  - "Review this change for security vulnerabilities"
"""

# 부모 폴더 하나에 여러 git 저장소가 걸린 경우를 재현하는 설정.
# 교육 카테고리는 저장소 자체가 아니라 상위 폴더를 등록해 두고,
# 실제로는 그 아래 자식 저장소가 여럿 발견된다.
SAMPLE_PREFIX = """\
me:
  - klyhja@l-walk.com
categories:
  - name: 교육
    repos: [leadwalk_study/2026/second-half-automation-training]
  - name: 정확일치
    repos: [a/b]
  - name: 백엔드 공수산정
    progress: 85%
    repos: [qmeet/backend2, qmeet/backend2/sub]
dev_root: C:\\Users\\klyhj\\dev
"""


def write(tmp_path, text):
    p = tmp_path / "config.yaml"
    p.write_text(text, encoding="utf-8")
    return p


def test_기본_필드를_읽는다(tmp_path):
    cfg = load_config(write(tmp_path, SAMPLE))
    assert isinstance(cfg, Config)
    assert cfg.me == (
        "klyhja@l-walk.com",
        "61999720+KimLakYoung111@users.noreply.github.com",
    )
    assert cfg.dev_root == r"C:\Users\klyhj\dev"
    assert cfg.ignore_prompts == ("Review this change for security vulnerabilities",)
    assert [c.name for c in cfg.categories] == ["백엔드 공수산정", "GA4", "자동화"]


def test_구분을_이름으로_찾는다(tmp_path):
    cfg = load_config(write(tmp_path, SAMPLE))
    assert cfg.category("GA4").by_content is True
    assert cfg.category("백엔드 공수산정").progress == "85%"
    assert cfg.category("없는구분") is None


def test_저장소로_구분을_찾는다(tmp_path):
    cfg = load_config(write(tmp_path, SAMPLE))
    assert cfg.category_for_repo("qmeet/backend2") == "백엔드 공수산정"
    assert cfg.category_for_repo("e2etest/playwright_base") == "자동화"
    assert cfg.category_for_repo("golfzone/admin") is None


def test_구분_순서를_돌려준다(tmp_path):
    cfg = load_config(write(tmp_path, SAMPLE))
    assert cfg.order_index("백엔드 공수산정") == 0
    assert cfg.order_index("자동화") == 2
    # 목록에 없는 구분은 맨 뒤로 밀린다
    assert cfg.order_index("없는구분") == 3


def test_엑셀_라벨에_모듈_진행률을_붙인다(tmp_path):
    cfg = load_config(write(tmp_path, SAMPLE))
    assert cfg.label("백엔드 공수산정") == "백엔드 공수산정(85%)"
    assert cfg.label("자동화") == "자동화"


def test_구분_이름이_겹치면_에러(tmp_path):
    text = SAMPLE.replace("  - name: GA4", "  - name: 백엔드 공수산정")
    with pytest.raises(ConfigError, match="구분 이름이 중복"):
        load_config(write(tmp_path, text))


def test_한_저장소가_두_구분에_속하면_에러(tmp_path):
    text = SAMPLE.replace(
        "  - name: GA4\n    by_content: true",
        "  - name: GA4\n    repos: [qmeet/backend2]",
    )
    with pytest.raises(ConfigError, match="두 구분에 속"):
        load_config(write(tmp_path, text))


def test_진행률_형식이_틀리면_에러(tmp_path):
    with pytest.raises(ConfigError, match="진행률 형식"):
        load_config(write(tmp_path, SAMPLE.replace("progress: 85%", "progress: 높음")))


def test_me_가_비면_에러(tmp_path):
    text = SAMPLE.replace(
        "me:\n  - klyhja@l-walk.com\n"
        "  - 61999720+KimLakYoung111@users.noreply.github.com",
        "me: []",
    )
    with pytest.raises(ConfigError, match="me 목록이 비어"):
        load_config(write(tmp_path, text))


def test_저장소_경로_구분자를_정규화한다(tmp_path):
    text = SAMPLE.replace("[qmeet/backend2]", r"['qmeet\backend2']")
    cfg = load_config(write(tmp_path, text))
    assert cfg.category_for_repo("qmeet/backend2") == "백엔드 공수산정"


# --- 경로 세그먼트 경계 기준 프리픽스 매칭 ---
# 브리프의 정확 일치만으로는, 상위 폴더 하나에 여러 git 저장소가 걸린
# 경우(예: 교육생 5명 폴더)를 다루지 못한다. 등록된 저장소 경로가
# 조회 경로의 상위 경로일 때도 구분을 찾아내야 한다.


def test_상위_폴더에_걸린_구분이_하위_저장소에도_적용된다(tmp_path):
    cfg = load_config(write(tmp_path, SAMPLE_PREFIX))
    assert (
        cfg.category_for_repo(
            "leadwalk_study/2026/second-half-automation-training/repos/automation-study-eunchae"
        )
        == "교육"
    )


def test_경로_경계가_없으면_매칭하지_않는다(tmp_path):
    cfg = load_config(write(tmp_path, SAMPLE_PREFIX))
    # a/b 가 등록돼 있어도 a/bc 는 다른 저장소이므로 매칭되면 안 된다
    assert cfg.category_for_repo("a/bc") is None


def test_정확_일치가_짧은_프리픽스_일치보다_우선한다(tmp_path):
    cfg = load_config(write(tmp_path, SAMPLE_PREFIX))
    # qmeet/backend2 와 qmeet/backend2/sub 이 모두 등록돼 있을 때
    # qmeet/backend2 자신을 조회하면 정확 일치가 이긴다
    assert cfg.category_for_repo("qmeet/backend2") == "백엔드 공수산정"


def test_가장_긴_프리픽스가_이긴다(tmp_path):
    cfg = load_config(write(tmp_path, SAMPLE_PREFIX))
    # qmeet/backend2 와 qmeet/backend2/sub 둘 다 등록된 상태에서
    # qmeet/backend2/sub 아래를 조회하면 더 긴(더 구체적인) 쪽이 이긴다
    assert cfg.category_for_repo("qmeet/backend2/sub/child") == "백엔드 공수산정"


def test_매칭되는_구분이_없으면_None(tmp_path):
    cfg = load_config(write(tmp_path, SAMPLE_PREFIX))
    assert cfg.category_for_repo("golfzone/admin") is None
