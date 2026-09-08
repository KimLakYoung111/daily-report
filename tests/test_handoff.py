# -*- coding: utf-8 -*-
"""HANDOFF.md 발췌 테스트."""
from report.handoff import latest_section, read, select_headings

DOC = """\
# HANDOFF: 최신 판이다

## Current Status: Partially Complete

업무 테스트 11개 전부 통과하지만 커밋은 하나도 안 했습니다.

## What Was Done

- perform_login 구현
- Page Object 2종

## What Didn't Work / Gotchas

- JS 로 input 값을 넣으면 Vue 가 못 받습니다.

## Remaining Work

1. QM103 확정 후 작성
2. 엑셀에 QM104~106 추가

## Verification Commands

```bash
pytest -q
```

---

## Previous Handoff (archived)

# HANDOFF: 옛 판이다

## What Was Done

- 옛날 작업
"""


def test_두번째_HANDOFF_헤딩_전까지만_남긴다():
    got = latest_section(DOC)
    assert "최신 판이다" in got
    assert "옛 판이다" not in got
    assert "옛날 작업" not in got


def test_HANDOFF_헤딩이_하나면_전체를_남긴다():
    text = "# HANDOFF: 하나뿐\n\n## What Was Done\n\n- 하나\n"
    assert latest_section(text) == text


def test_HANDOFF_헤딩이_없으면_전체를_남긴다():
    text = "## What Was Done\n\n- 하나\n"
    assert latest_section(text) == text


def test_필요한_헤딩만_고른다():
    got = select_headings(latest_section(DOC))
    assert "Current Status" in got
    assert "What Was Done" in got
    assert "Remaining Work" in got
    assert "perform_login 구현" in got
    assert "QM103 확정 후 작성" in got


def test_함정과_검증명령은_버린다():
    got = select_headings(latest_section(DOC))
    assert "Gotchas" not in got
    assert "Verification Commands" not in got
    assert "pytest -q" not in got


def test_한국어_헤딩도_고른다():
    text = "# HANDOFF: 한글\n\n## 한 일\n\n- 했다\n\n## 함정·주의\n\n- 조심\n\n## 안 한 것 / 다음 단계\n\n- 남았다\n"
    got = select_headings(latest_section(text))
    assert "했다" in got
    assert "남았다" in got
    assert "조심" not in got


def test_필요한_헤딩이_없으면_빈_문자열():
    text = "# HANDOFF: 없음\n\n## 함정·주의\n\n- 조심\n"
    assert select_headings(latest_section(text)) == ""


def test_파일을_읽어_발췌한다(tmp_path):
    (tmp_path / "HANDOFF.md").write_text(DOC, encoding="utf-8")
    got = read(tmp_path)
    assert "Remaining Work" in got
    assert "옛 판이다" not in got


def test_파일이_없으면_None(tmp_path):
    assert read(tmp_path) is None
