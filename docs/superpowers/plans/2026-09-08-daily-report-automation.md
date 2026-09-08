# 일일보고 엑셀 생성 자동화 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 날짜 하나를 지정하면 그날 작업의 근거를 전수로 모아 한 파일에 담고, 사람이 판단해 쓴 날짜별 데이터 파일로 기존 보고 양식의 엑셀을 만든다.

**Architecture:** `report/` 패키지에 수집·검증·렌더링을 책임별로 나눈 모듈을 두고, CLI 엔트리 두 개(`collect_evidence.py`, `build_report.py`)가 그걸 조립한다. 스크립트는 근거만 모으고 행 초안은 만들지 않는다 — 판단은 사람(Claude)이 `data/YYYY-MM-DD.yaml`에 쓴다. 구분 목록·모듈 진행률·본인 식별은 `config.yaml`에서 사람이 관리한다.

**Tech Stack:** Python 3.12 / 표준 라이브러리 / `openpyxl` 3.1.5 / `PyYAML` 6.0.1 / `pytest` 7.4.3

**Spec:** `docs/superpowers/specs/2026-09-08-daily-report-automation-design.md`

## Global Constraints

- 의존성은 표준 라이브러리 + `openpyxl` + `PyYAML`만. 다른 패키지를 추가하지 않는다.
- 모든 주석·docstring·출력 문구는 한국어로 쓴다. 기존 `build_report.py`·`daily_report.py` 관례다.
- Windows 환경이다. `PYTHONIOENCODING` 없이도 동작해야 하므로, 콘솔에 쓰는 엔트리 스크립트는 `sys.stdout.reconfigure(encoding="utf-8")`를 먼저 호출한다. (기존 `daily_report.py`가 cp949로 죽는 버그다.)
- 파일을 읽을 때 인코딩을 항상 명시한다: `encoding="utf-8", errors="replace"`. 생략하면 Windows에서 cp949로 열려 조용히 깨진다.
- 엑셀 열 구성은 고정이다: `A 날짜 / B 구분 / C 세부 작업 / D 진행률 / E 비고 / F 폴더 위치`.
- 엑셀 열 너비는 `(12, 17, 42, 9, 36, 50)`.
- 엑셀 본문 글꼴은 `맑은 고딕` 10pt. F열만 `Consolas` 8pt, 색 `444444`.
- 셀 테두리는 전체 `thin`, 색 `000000`. 정렬은 A·B·D열 가운데, C·E·F열 왼쪽, 전부 `wrap_text=True`.
- 행 높이는 30. F열 값이 개행 3개 이상이면 58.
- 구분 순서는 `config.yaml`의 `categories` 순서를 따른다. **날짜 데이터 파일의 순서는 무시한다.**
- 브랜치는 날짜 데이터 파일에 적힌 값을 쓴다. **렌더링 시점에 git에서 조회하지 않는다.**
- `config.yaml`의 `me` 목록에 없는 작성자의 커밋은 근거에서 제외한다.
- 저장소 경로는 `config.yaml`의 `dev_root` 기준 상대 경로로 표기한다(`qmeet/backend2`). 구분자는 `/`로 정규화한다.
- 행 초안을 생성하지 않는다. 근거 파일에 표 행 형태의 출력을 넣지 않는다.
- 산출물은 `output/` 아래에만 쓴다(`.gitignore` 처리됨). `data/`는 커밋 대상이다.

---

## File Structure

| 파일 | 책임 |
|---|---|
| `report/__init__.py` | 빈 패키지 표시 |
| `report/config.py` | `config.yaml` 로딩·검증. `Config`·`Category` |
| `report/sessions.py` | 세션 `*.jsonl` → 이벤트 목록. **이벤트별 cwd** |
| `report/repos.py` | git 루트 정규화, 저장소 발견, 커밋·미커밋·브랜치 |
| `report/handoff.py` | `HANDOFF.md` 최신 섹션에서 필요한 헤딩만 추출 |
| `report/evidence.py` | 근거 마크다운 + 커버리지 사이드카 렌더 |
| `report/daydata.py` | `data/*.yaml` 로딩·검증. `DayReport`·`Row`·`Item`·`Location` |
| `report/excel.py` | 엑셀·TSV 렌더 (현행 `build_report.py`의 렌더링부 이관) |
| `collect_evidence.py` | CLI 엔트리 — 근거 수집 |
| `build_report.py` | CLI 엔트리 — 개편. `REPORTS` 딕셔너리 제거 |
| `config.yaml` | 사람이 관리하는 설정 |
| `data/2026-09-07.yaml`, `data/2026-09-08.yaml` | 현행 `REPORTS`에서 이관 |
| `tests/` | 모듈별 pytest |
| `pytest.ini` | pytest 설정 |
| `requirements.txt` | `openpyxl`·`PyYAML`·`pytest` 추가 |

`daily_report.py`는 건드리지 않는다. 범용 세션 조회용으로 남긴다(스펙 「구성」).

---

### Task 1: 테스트 기반과 `report/config.py`

**Files:**
- Create: `pytest.ini`
- Create: `report/__init__.py`
- Create: `report/config.py`
- Create: `config.yaml`
- Create: `tests/__init__.py`
- Create: `tests/test_config.py`
- Modify: `requirements.txt`

**Interfaces:**
- Consumes: 없음 (첫 태스크)
- Produces:
  - `report.config.ConfigError(Exception)`
  - `report.config.Category` — 동결 데이터클래스, 필드 `name: str`, `progress: str | None`, `repos: tuple[str, ...]`, `by_content: bool`
  - `report.config.Config` — 동결 데이터클래스, 필드 `me: tuple[str, ...]`, `categories: tuple[Category, ...]`, `dev_root: str`, `ignore_prompts: tuple[str, ...]`
  - `Config.category(name: str) -> Category | None`
  - `Config.category_for_repo(repo: str) -> str | None` — 저장소 상대 경로로 구분 이름을 찾는다. 없으면 `None`
  - `Config.order_index(name: str) -> int` — `categories` 안의 위치. 없으면 `len(categories)`
  - `Config.label(name: str) -> str` — 엑셀 B열 표기. `progress`가 있으면 `"백엔드 공수산정(85%)"`, 없으면 `"자동화"`
  - `report.config.load_config(path: str | Path) -> Config`

- [ ] **Step 1: `pytest.ini`와 `requirements.txt`를 만든다**

`pytest.ini`:

```ini
[pytest]
testpaths = tests
python_files = test_*.py
addopts = -q
```

`requirements.txt` (전체 내용으로 교체):

```
streamlit
openpyxl
PyYAML
pytest
```

- [ ] **Step 2: 실패하는 테스트를 쓴다**

`tests/__init__.py`는 빈 파일로 만든다.

`tests/test_config.py`:

```python
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
```

- [ ] **Step 3: 테스트를 돌려 실패를 확인한다**

Run: `python -m pytest tests/test_config.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'report'`

- [ ] **Step 4: 최소 구현을 쓴다**

`report/__init__.py`는 빈 파일로 만든다.

`report/config.py`:

```python
# -*- coding: utf-8 -*-
"""config.yaml 로딩과 검증.

사람이 관리하는 값만 담는다 — 본인 식별, 구분 목록, 저장소 매핑,
모듈 진행률, 수집 루트, 걸러낼 자동 세션 프롬프트.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

import yaml

PROGRESS_RE = re.compile(r"^\d{1,3}%$")


class ConfigError(Exception):
    """config.yaml 이 규칙에 맞지 않을 때."""


def normalize_repo(value: str) -> str:
    """저장소 상대 경로의 구분자를 / 로 맞추고 양끝 슬래시를 없앤다."""
    return str(value).replace("\\", "/").strip("/")


@dataclass(frozen=True)
class Category:
    name: str
    progress: str | None = None
    repos: tuple[str, ...] = ()
    by_content: bool = False


@dataclass(frozen=True)
class Config:
    me: tuple[str, ...]
    categories: tuple[Category, ...]
    dev_root: str
    ignore_prompts: tuple[str, ...] = ()
    # dict 은 해시가 안 되므로 eq/hash 에서 뺀다. 안 빼면 frozen 데이터클래스가
    # 만드는 __hash__ 가 터진다.
    _by_repo: dict[str, str] = field(
        default_factory=dict, repr=False, compare=False
    )

    def category(self, name: str) -> Category | None:
        for c in self.categories:
            if c.name == name:
                return c
        return None

    def category_for_repo(self, repo: str) -> str | None:
        return self._by_repo.get(normalize_repo(repo))

    def order_index(self, name: str) -> int:
        for i, c in enumerate(self.categories):
            if c.name == name:
                return i
        return len(self.categories)

    def label(self, name: str) -> str:
        c = self.category(name)
        if c is None or not c.progress:
            return name
        return "{}({})".format(c.name, c.progress)


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
    by_repo: dict[str, str] = {}

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
            if r in by_repo:
                raise ConfigError(
                    "저장소 {} 가 두 구분에 속한다: {} / {}".format(
                        r, by_repo[r], name
                    )
                )
            by_repo[r] = name

        categories.append(
            Category(
                name=name,
                progress=progress,
                repos=repos,
                by_content=bool(entry.get("by_content")),
            )
        )

    if not categories:
        raise ConfigError("categories 가 비어 있다")

    return Config(
        me=me,
        categories=tuple(categories),
        dev_root=dev_root,
        ignore_prompts=tuple(str(x) for x in (raw.get("ignore_prompts") or [])),
        _by_repo=by_repo,
    )
```

- [ ] **Step 5: 테스트를 돌려 통과를 확인한다**

Run: `python -m pytest tests/test_config.py -v`
Expected: PASS — 10 passed

- [ ] **Step 6: 실제 `config.yaml`을 만든다**

프로젝트 루트에 `config.yaml`:

```yaml
# 일일보고 설정 — 사람이 관리한다.
# 스펙: docs/superpowers/specs/2026-09-08-daily-report-automation-design.md

# 본인 식별. 이 목록에 없는 작성자의 커밋은 보고서에서 제외한다.
me:
  - klyhja@l-walk.com
  - 61999720+KimLakYoung111@users.noreply.github.com   # PR 병합 시 찍히는 주소

# 구분 목록 — 엑셀에 나타날 순서. 여기 없는 구분은 쓰지 않는다.
# progress 는 모듈 전체 진행률로, 자동 갱신되지 않는다. 직접 고친다.
categories:
  - name: 백엔드 공수산정
    progress: 85%
    repos: [qmeet/backend2]
  - name: 프론트 공수산정
    progress: 20%
    repos: [qmeet/front]
  - name: AI 서버 공수산정
    repos: [qmeet/qmeet_ai]
  - name: 시안
    repos: [qmeet/front_design_prototype]
  - name: 인프라
    repos: [qmeet/qmeet-dev-ssh]
  - name: GA4
    by_content: true       # 저장소로 안 갈라짐 — 내용으로 판단한다
  - name: CRM
    by_content: true
  - name: 자동화
    repos: [e2etest/qmeet, e2etest/playwright_base]
  - name: 교육
    repos: [leadwalk_study/2026/second-half-automation-training]

# 수집 대상 루트. 이 아래 git 저장소를 자동 발견한다.
dev_root: C:\Users\klyhj\dev

# 근거에서 걸러낼 자동 생성 세션 (사람이 시킨 작업이 아니다).
ignore_prompts:
  - "Review this change for security vulnerabilities"
  - "This session is being continued from a previous conversation"
```

- [ ] **Step 7: 실제 `config.yaml`이 로딩되는지 확인한다**

Run:

```bash
python -c "from report.config import load_config; c = load_config('config.yaml'); print(len(c.categories), '구분'); print(c.label('백엔드 공수산정')); print(c.category_for_repo('e2etest/qmeet'))"
```

Expected: `9 구분` / `백엔드 공수산정(85%)` / `자동화`

- [ ] **Step 8: 커밋한다**

```bash
git add pytest.ini requirements.txt config.yaml report/__init__.py report/config.py tests/__init__.py tests/test_config.py
git commit -m "feat: config.yaml 로딩·검증 — 구분 목록과 본인 식별을 설정으로 뺀다"
```

---

### Task 2: `report/sessions.py` — 이벤트별 cwd로 세션을 읽는다

`daily_report.py`는 세션 파일의 **첫 cwd**로 전체를 집계해서, 세션 중간에 디렉터리를 옮기면 그쪽 작업이 통째로 다른 저장소에 붙는다. 2026-09-08 이벤트 최다였던 `qmeet-dev-ssh`(3,034건)가 보고서에 안 나온 원인이다. 여기서 고친다.

**Files:**
- Create: `report/sessions.py`
- Create: `tests/test_sessions.py`

**Interfaces:**
- Consumes: `report.config.Config` (`ignore_prompts` 필드만 쓴다)
- Produces:
  - `report.sessions.SessionEvent` — 동결 데이터클래스, 필드 `ts: datetime` (로컬 시간대), `cwd: str` (원본 절대 경로), `prompt: str | None`
  - `report.sessions.load_events(day: date, projects_root: str | Path, ignore_prompts: Sequence[str] = ()) -> list[SessionEvent]` — `ts` 오름차순 정렬

- [ ] **Step 1: 실패하는 테스트를 쓴다**

`tests/test_sessions.py`:

```python
# -*- coding: utf-8 -*-
"""세션 jsonl 파싱 테스트 — 이벤트별 cwd 로 집계해야 한다."""
import datetime as dt
import json

from report.sessions import load_events

DAY = dt.date(2026, 9, 8)


def line(ts, cwd, **extra):
    o = {"timestamp": ts, "cwd": cwd}
    o.update(extra)
    return json.dumps(o, ensure_ascii=False)


def user_line(ts, cwd, text):
    return line(
        ts,
        cwd,
        type="user",
        userType="external",
        message={"content": [{"type": "text", "text": text}]},
    )


def write_session(root, name, lines):
    d = root / "proj"
    d.mkdir(parents=True, exist_ok=True)
    p = d / name
    p.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return p


def test_이벤트마다_cwd_를_따로_본다(tmp_path):
    """한 세션이 디렉터리를 옮기면 양쪽이 다 잡혀야 한다."""
    write_session(
        tmp_path,
        "a.jsonl",
        [
            line("2026-09-08T00:10:00.000Z", r"C:\dev\front"),
            line("2026-09-08T01:10:00.000Z", r"C:\dev\infra"),
            line("2026-09-08T02:10:00.000Z", r"C:\dev\infra"),
        ],
    )
    events = load_events(DAY, tmp_path)
    cwds = [e.cwd for e in events]
    assert cwds.count(r"C:\dev\front") == 1
    assert cwds.count(r"C:\dev\infra") == 2


def test_다른_날짜는_버린다(tmp_path):
    write_session(
        tmp_path,
        "a.jsonl",
        [
            line("2026-09-07T05:00:00.000Z", r"C:\dev\front"),
            line("2026-09-08T05:00:00.000Z", r"C:\dev\front"),
            line("2026-09-09T05:00:00.000Z", r"C:\dev\front"),
        ],
    )
    assert len(load_events(DAY, tmp_path)) == 1


def test_사용자_프롬프트만_담는다(tmp_path):
    write_session(
        tmp_path,
        "a.jsonl",
        [
            user_line("2026-09-08T05:00:00.000Z", r"C:\dev\front", "핸드오프 확인해줘"),
            line(
                "2026-09-08T05:01:00.000Z",
                r"C:\dev\front",
                type="assistant",
                message={"content": [{"type": "text", "text": "네"}]},
            ),
        ],
    )
    events = load_events(DAY, tmp_path)
    prompts = [e.prompt for e in events if e.prompt]
    assert prompts == ["핸드오프 확인해줘"]


def test_시스템_리마인더_프롬프트는_버린다(tmp_path):
    write_session(
        tmp_path,
        "a.jsonl",
        [
            user_line("2026-09-08T05:00:00.000Z", r"C:\dev\front", "<system-reminder>x"),
            user_line("2026-09-08T05:01:00.000Z", r"C:\dev\front", "진짜 요청"),
        ],
    )
    prompts = [e.prompt for e in load_events(DAY, tmp_path) if e.prompt]
    assert prompts == ["진짜 요청"]


def test_ignore_prompts_에_걸리면_버린다(tmp_path):
    write_session(
        tmp_path,
        "a.jsonl",
        [
            user_line(
                "2026-09-08T05:00:00.000Z",
                r"C:\dev\front",
                "Review this change for security vulnerabilities. Changed files: ...",
            ),
            user_line("2026-09-08T05:01:00.000Z", r"C:\dev\front", "사람이 시킨 일"),
        ],
    )
    events = load_events(
        DAY, tmp_path, ignore_prompts=["Review this change for security vulnerabilities"]
    )
    prompts = [e.prompt for e in events if e.prompt]
    assert prompts == ["사람이 시킨 일"]
    # 프롬프트만 버리고 이벤트 자체는 남는다 (활동량 집계에 쓰인다)
    assert len(events) == 2


def test_깨진_줄과_timestamp_없는_줄은_건너뛴다(tmp_path):
    write_session(
        tmp_path,
        "a.jsonl",
        [
            "{{{ 깨진 json",
            json.dumps({"cwd": r"C:\dev\front"}),
            line("2026-09-08T05:00:00.000Z", r"C:\dev\front"),
        ],
    )
    assert len(load_events(DAY, tmp_path)) == 1


def test_cwd_없는_줄은_건너뛴다(tmp_path):
    write_session(
        tmp_path,
        "a.jsonl",
        [
            json.dumps({"timestamp": "2026-09-08T05:00:00.000Z"}),
            line("2026-09-08T05:00:00.000Z", r"C:\dev\front"),
        ],
    )
    assert len(load_events(DAY, tmp_path)) == 1


def test_시간_오름차순으로_정렬한다(tmp_path):
    write_session(
        tmp_path,
        "a.jsonl",
        [
            line("2026-09-08T09:00:00.000Z", r"C:\dev\b"),
            line("2026-09-08T01:00:00.000Z", r"C:\dev\a"),
        ],
    )
    events = load_events(DAY, tmp_path)
    assert [e.cwd for e in events] == [r"C:\dev\a", r"C:\dev\b"]


def test_하위_디렉터리를_재귀로_찾는다(tmp_path):
    deep = tmp_path / "x" / "y" / "z"
    deep.mkdir(parents=True)
    (deep / "s.jsonl").write_text(
        line("2026-09-08T05:00:00.000Z", r"C:\dev\front") + "\n", encoding="utf-8"
    )
    assert len(load_events(DAY, tmp_path)) == 1
```

- [ ] **Step 2: 테스트를 돌려 실패를 확인한다**

Run: `python -m pytest tests/test_sessions.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'report.sessions'`

- [ ] **Step 3: 최소 구현을 쓴다**

`report/sessions.py`:

```python
# -*- coding: utf-8 -*-
"""Claude Code 세션 기록(*.jsonl)에서 하루치 이벤트를 읽는다.

daily_report.py 는 세션 파일의 첫 cwd 로 전체를 집계해, 세션 중간에
디렉터리를 옮기면 그쪽 작업이 다른 저장소에 붙는 버그가 있다.
여기서는 이벤트마다 cwd 를 따로 본다.
"""
from __future__ import annotations

import datetime as dt
import json
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

PROMPT_MAX = 120


@dataclass(frozen=True)
class SessionEvent:
    ts: dt.datetime
    cwd: str
    prompt: str | None = None


def _local_tz() -> dt.tzinfo:
    return dt.datetime.now().astimezone().tzinfo


def _extract_prompt(obj: dict, ignore_prompts: Sequence[str]) -> str | None:
    """사람이 직접 넣은 프롬프트만 돌려준다. 아니면 None."""
    if obj.get("type") != "user" or obj.get("userType") != "external":
        return None
    content = (obj.get("message") or {}).get("content")
    if isinstance(content, list):
        content = " ".join(
            c.get("text", "") for c in content if isinstance(c, dict)
        )
    if not isinstance(content, str):
        return None
    text = content.strip().replace("\n", " ")
    if not text or text.startswith("<"):
        return None
    if any(pat in text for pat in ignore_prompts):
        return None
    return text[:PROMPT_MAX]


def load_events(
    day: dt.date,
    projects_root: str | Path,
    ignore_prompts: Sequence[str] = (),
) -> list[SessionEvent]:
    """projects_root 아래 모든 *.jsonl 에서 day 에 해당하는 이벤트를 모은다."""
    tz = _local_tz()
    events: list[SessionEvent] = []

    for path in sorted(Path(projects_root).rglob("*.jsonl")):
        with open(path, encoding="utf-8", errors="replace") as fh:
            for raw in fh:
                try:
                    obj = json.loads(raw)
                except (ValueError, TypeError):
                    continue
                if not isinstance(obj, dict):
                    continue
                ts_raw, cwd = obj.get("timestamp"), obj.get("cwd")
                if not ts_raw or not cwd:
                    continue
                try:
                    ts = dt.datetime.fromisoformat(
                        str(ts_raw).replace("Z", "+00:00")
                    ).astimezone(tz)
                except ValueError:
                    continue
                if ts.date() != day:
                    continue
                events.append(
                    SessionEvent(
                        ts=ts,
                        cwd=str(cwd),
                        prompt=_extract_prompt(obj, ignore_prompts),
                    )
                )

    events.sort(key=lambda e: e.ts)
    return events
```

- [ ] **Step 4: 테스트를 돌려 통과를 확인한다**

Run: `python -m pytest tests/test_sessions.py -v`
Expected: PASS — 9 passed

- [ ] **Step 5: 실제 세션 기록으로 cwd 버그가 고쳐졌는지 확인한다**

Run:

```bash
python -c "
import datetime as dt, os, collections
from report.sessions import load_events
ev = load_events(dt.date(2026,9,8), os.path.expanduser('~/.claude/projects'))
c = collections.Counter(e.cwd for e in ev)
for k, v in c.most_common(6): print(v, k)
"
```

Expected: `qmeet-dev-ssh`가 최상위 근처에 **보인다.** 기존 `daily_report.py` 출력에는 없었다. (이벤트 수 자체는 정확히 일치하지 않아도 된다 — 하위 디렉터리가 따로 집계되고, Task 3에서 git 루트로 접어 올린다.)

- [ ] **Step 6: 커밋한다**

```bash
git add report/sessions.py tests/test_sessions.py
git commit -m "fix: 세션 집계를 이벤트별 cwd 로 바꿔 저장소가 소실되던 버그를 없앤다"
```

---

### Task 3: `report/repos.py` — 저장소 발견과 git 수집

**Files:**
- Create: `report/repos.py`
- Create: `tests/test_repos.py`

**Interfaces:**
- Consumes: `report.config.Config`, `report.config.normalize_repo`, `report.sessions.SessionEvent`
- Produces:
  - `report.repos.Commit` — 동결 데이터클래스, 필드 `sha: str`, `time: str` (`"09:29"`), `subject: str`, `email: str`
  - `report.repos.git_root(path: str | Path) -> str | None` — git 저장소 루트 절대 경로. 저장소가 아니면 `None`
  - `report.repos.to_rel(abs_path: str, dev_root: str) -> str` — `dev_root` 기준 상대 경로, 구분자 `/`. `dev_root` 밖이면 절대 경로를 `/`로 정규화해 돌려준다
  - `report.repos.discover(events: Sequence[SessionEvent], config: Config) -> list[str]` — 저장소 상대 경로 목록. 세션 cwd(git 루트로 정규화) ∪ `config` 등록 저장소. 정렬됨
  - `report.repos.commits(repo_abs: str | Path, day: date, me: Sequence[str]) -> tuple[list[Commit], int]` — `(본인 커밋 목록, 제외한 타인 커밋 수)`
  - `report.repos.uncommitted(repo_abs: str | Path) -> list[str]` — `git status --porcelain` 줄 목록
  - `report.repos.branch(repo_abs: str | Path) -> str | None`

- [ ] **Step 1: 실패하는 테스트를 쓴다**

`tests/test_repos.py`:

```python
# -*- coding: utf-8 -*-
"""저장소 발견과 git 수집 테스트."""
import datetime as dt
import subprocess

import pytest

from report.config import Config, Category
from report.repos import (
    Commit,
    branch,
    commits,
    discover,
    git_root,
    to_rel,
    uncommitted,
)
from report.sessions import SessionEvent

DAY = dt.date(2026, 9, 8)


def run(cwd, *args):
    subprocess.run(
        ["git", *args], cwd=str(cwd), check=True,
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    )


@pytest.fixture
def repo(tmp_path):
    """커밋 3건이 있는 저장소. 2건은 본인, 1건은 타인. 날짜는 2026-09-08."""
    d = tmp_path / "dev" / "proj" / "app"
    d.mkdir(parents=True)
    run(d, "init", "-q", "-b", "main")
    run(d, "config", "user.name", "나")
    run(d, "config", "user.email", "me@example.com")

    env_times = [
        ("첫 커밋이다", "me@example.com", "나", "2026-09-08T09:29:00+09:00"),
        ("남의 커밋이다", "other@example.com", "남", "2026-09-08T10:00:00+09:00"),
        ("둘째 커밋이다", "me@example.com", "나", "2026-09-08T14:15:00+09:00"),
        ("어제 커밋이다", "me@example.com", "나", "2026-09-07T09:00:00+09:00"),
    ]
    for i, (subject, email, name, when) in enumerate(env_times):
        (d / "f{}.txt".format(i)).write_text(str(i), encoding="utf-8")
        run(d, "add", "-A")
        subprocess.run(
            ["git", "commit", "-q", "-m", subject,
             "--author", "{} <{}>".format(name, email),
             "--date", when],
            cwd=str(d), check=True,
            env={**_env(), "GIT_COMMITTER_DATE": when},
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        )
    return d


def _env():
    import os
    return dict(os.environ)


def test_git_루트를_찾는다(repo):
    sub = repo / "src"
    sub.mkdir()
    assert git_root(sub) == str(repo.resolve())


def test_git_저장소가_아니면_None(tmp_path):
    plain = tmp_path / "plain"
    plain.mkdir()
    assert git_root(plain) is None


def test_없는_경로면_None(tmp_path):
    assert git_root(tmp_path / "없음") is None


def test_dev_root_기준_상대경로로_바꾼다(tmp_path):
    dev = str(tmp_path / "dev")
    assert to_rel(str(tmp_path / "dev" / "proj" / "app"), dev) == "proj/app"


def test_dev_root_밖이면_절대경로를_돌려준다(tmp_path):
    assert to_rel(r"D:\other\thing", str(tmp_path / "dev")) == "D:/other/thing"


def test_브랜치를_읽는다(repo):
    assert branch(repo) == "main"


def test_본인_커밋만_돌려주고_타인은_센다(repo):
    got, skipped = commits(repo, DAY, ["me@example.com"])
    assert [c.subject for c in got] == ["첫 커밋이다", "둘째 커밋이다"]
    assert skipped == 1
    assert all(isinstance(c, Commit) for c in got)


def test_커밋_시각을_시분으로_준다(repo):
    got, _ = commits(repo, DAY, ["me@example.com"])
    assert [c.time for c in got] == ["09:29", "14:15"]


def test_다른_날_커밋은_빠진다(repo):
    got, _ = commits(repo, dt.date(2026, 9, 7), ["me@example.com"])
    assert [c.subject for c in got] == ["어제 커밋이다"]


def test_git_저장소가_아니면_커밋은_빈_목록(tmp_path):
    plain = tmp_path / "plain"
    plain.mkdir()
    assert commits(plain, DAY, ["me@example.com"]) == ([], 0)


def test_미커밋_변경을_읽는다(repo):
    (repo / "새파일.txt").write_text("x", encoding="utf-8")
    (repo / "f0.txt").write_text("바뀜", encoding="utf-8")
    lines = uncommitted(repo)
    assert any("새파일.txt" in ln for ln in lines)
    assert any("f0.txt" in ln for ln in lines)


def test_깨끗하면_미커밋은_빈_목록(repo):
    assert uncommitted(repo) == []


def make_config(dev_root, repos):
    cats = (Category(name="테스트구분", repos=tuple(repos)),)
    return Config(me=("me@example.com",), categories=cats, dev_root=dev_root)


def test_세션_cwd_와_config_저장소의_합집합을_돌려준다(repo, tmp_path):
    dev = str(tmp_path / "dev")
    events = [
        SessionEvent(ts=dt.datetime.now(), cwd=str(repo / "src")),
        SessionEvent(ts=dt.datetime.now(), cwd=str(repo)),
    ]
    got = discover(events, make_config(dev, ["없는/저장소"]))
    # 세션에서 발견된 것 + config 에 등록된 것
    assert "proj/app" in got
    assert "없는/저장소" in got


def test_같은_저장소의_하위_디렉터리는_하나로_접힌다(repo, tmp_path):
    dev = str(tmp_path / "dev")
    (repo / "src").mkdir()
    events = [
        SessionEvent(ts=dt.datetime.now(), cwd=str(repo / "src")),
        SessionEvent(ts=dt.datetime.now(), cwd=str(repo)),
    ]
    got = discover(events, make_config(dev, []))
    assert got.count("proj/app") == 1


def test_git_아닌_cwd_도_상대경로로_남긴다(repo, tmp_path):
    """교육 폴더처럼 git 이 아닌 작업 위치도 근거에서 빠지면 안 된다."""
    dev = tmp_path / "dev"
    plain = dev / "study" / "week04"
    plain.mkdir(parents=True)
    events = [SessionEvent(ts=dt.datetime.now(), cwd=str(plain))]
    got = discover(events, make_config(str(dev), []))
    assert "study/week04" in got
```

- [ ] **Step 2: 테스트를 돌려 실패를 확인한다**

Run: `python -m pytest tests/test_repos.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'report.repos'`

- [ ] **Step 3: 최소 구현을 쓴다**

`report/repos.py`:

```python
# -*- coding: utf-8 -*-
"""저장소 발견과 git 수집.

저장소는 두 소스의 합집합으로 찾는다 — 세션 cwd(git 루트로 정규화)와
config.yaml 에 등록된 저장소. 한쪽만 쓰면 구멍이 난다. 세션만 쓰면 등록됐는데
그날 세션이 없던 저장소를 놓치고, config 만 쓰면 새로 등장한 저장소가
조용히 사라진다.
"""
from __future__ import annotations

import datetime as dt
import subprocess
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

from .config import Config, normalize_repo
from .sessions import SessionEvent

_SEP = "\x1f"  # git --pretty 필드 구분자. 커밋 제목에 나올 일이 없다


@dataclass(frozen=True)
class Commit:
    sha: str
    time: str
    subject: str
    email: str


def _git(repo: str | Path, *args: str) -> str | None:
    """git 명령을 돌려 stdout 을 준다. 실패하면 None."""
    try:
        out = subprocess.run(
            ["git", "-C", str(repo), *args],
            capture_output=True, text=True, encoding="utf-8", errors="replace",
        )
    except OSError:
        return None
    if out.returncode != 0:
        return None
    return out.stdout


def git_root(path: str | Path) -> str | None:
    p = Path(path)
    if not p.exists():
        return None
    out = _git(p, "rev-parse", "--show-toplevel")
    if not out or not out.strip():
        return None
    return str(Path(out.strip()).resolve())


def to_rel(abs_path: str, dev_root: str) -> str:
    """dev_root 기준 상대 경로. 밖이면 절대 경로를 / 로 정규화해 준다."""
    try:
        rel = Path(abs_path).resolve().relative_to(Path(dev_root).resolve())
    except (ValueError, OSError):
        return normalize_repo(abs_path)
    return normalize_repo(str(rel))


def branch(repo: str | Path) -> str | None:
    out = _git(repo, "rev-parse", "--abbrev-ref", "HEAD")
    return out.strip() if out and out.strip() else None


def commits(
    repo: str | Path, day: dt.date, me: Sequence[str]
) -> tuple[list[Commit], int]:
    """(본인 커밋 목록, 제외한 타인 커밋 수). git 저장소가 아니면 ([], 0)."""
    since = day.isoformat()
    until = (day + dt.timedelta(days=1)).isoformat()
    out = _git(
        repo,
        "log", "--all",
        "--since={}T00:00".format(since),
        "--until={}T00:00".format(until),
        "--pretty=%h{s}%ad{s}%ae{s}%s".format(s=_SEP),
        "--date=format:%H:%M",
    )
    if out is None:
        return [], 0

    mine: list[Commit] = []
    skipped = 0
    lowered = {e.lower() for e in me}
    for line in out.splitlines():
        parts = line.split(_SEP, 3)
        if len(parts) != 4:
            continue
        sha, when, email, subject = parts
        if email.lower() in lowered:
            mine.append(
                Commit(sha=sha, time=when, subject=subject, email=email)
            )
        else:
            skipped += 1
    mine.reverse()  # git log 는 최신순 — 시간 오름차순으로 뒤집는다
    return mine, skipped


def uncommitted(repo: str | Path) -> list[str]:
    out = _git(repo, "status", "--porcelain")
    if out is None:
        return []
    return [ln for ln in out.splitlines() if ln.strip()]


def discover(events: Sequence[SessionEvent], config: Config) -> list[str]:
    """저장소 상대 경로 목록. 세션에서 발견된 것 ∪ config 등록분."""
    found: set[str] = set()
    seen_cwd: set[str] = set()

    for ev in events:
        if ev.cwd in seen_cwd:
            continue
        seen_cwd.add(ev.cwd)
        root = git_root(ev.cwd)
        # git 저장소가 아니어도 근거에서 빼지 않는다 (교육 폴더 등)
        found.add(to_rel(root or ev.cwd, config.dev_root))

    for cat in config.categories:
        found.update(cat.repos)

    return sorted(found)
```

- [ ] **Step 4: 테스트를 돌려 통과를 확인한다**

Run: `python -m pytest tests/test_repos.py -v`
Expected: PASS — 16 passed

- [ ] **Step 5: 실제 저장소로 작성자 필터를 확인한다**

Run:

```bash
python -c "
import datetime as dt
from report.repos import commits, uncommitted, branch
me = ['klyhja@l-walk.com', '61999720+KimLakYoung111@users.noreply.github.com']
r = r'C:\Users\klyhj\dev\qmeet\qmeet_ai'
got, skipped = commits(r, dt.date(2026,9,8), me)
print('본인', len(got), '/ 타인 제외', skipped, '/ 브랜치', branch(r))
"
```

Expected: `본인 4 / 타인 제외 5 / 브랜치 feature/orchestrator`

- [ ] **Step 6: 커밋한다**

```bash
git add report/repos.py tests/test_repos.py
git commit -m "feat: 저장소 자동 발견과 git 수집 — 세션 cwd 와 config 의 합집합"
```

---

### Task 4: `report/handoff.py` — 인계 문서에서 필요한 헤딩만 뽑는다

`backend2/HANDOFF.md`는 1,500줄이 넘고 최신 섹션만 110줄, `front`는 212줄이다. 저장소 8곳 전문이면 수천 줄이 된다. 최신 섹션(파일 맨 위)에서 진행률 판단에 쓰는 헤딩만 싣는다.

**Files:**
- Create: `report/handoff.py`
- Create: `tests/test_handoff.py`

**Interfaces:**
- Consumes: 없음
- Produces:
  - `report.handoff.WANTED` — `tuple[str, ...]`. 소문자로 비교할 헤딩 키워드
  - `report.handoff.latest_section(text: str) -> str` — 두 번째 `# HANDOFF` 헤딩 전까지
  - `report.handoff.select_headings(text: str) -> str` — `WANTED`에 걸리는 헤딩 블록만 이어붙임
  - `report.handoff.read(repo_abs: str | Path) -> str | None` — `HANDOFF.md`를 읽어 위 둘을 적용. 파일이 없으면 `None`

- [ ] **Step 1: 실패하는 테스트를 쓴다**

`tests/test_handoff.py`:

````python
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
````

- [ ] **Step 2: 테스트를 돌려 실패를 확인한다**

Run: `python -m pytest tests/test_handoff.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'report.handoff'`

- [ ] **Step 3: 최소 구현을 쓴다**

`report/handoff.py`:

```python
# -*- coding: utf-8 -*-
"""HANDOFF.md 에서 진행률 판단에 쓰는 헤딩만 뽑는다.

HANDOFF.md 는 최신 판이 맨 위에 쌓인다. 파일 전체는 1,500줄이 넘을 수 있어
최신 섹션만 보고, 그 안에서도 필요한 헤딩만 싣는다.
함정·검증 명령·파일 경로표는 제외한다 — 필요하면 경로로 직접 읽는다.
"""
from __future__ import annotations

import re
from pathlib import Path

#: 소문자로 비교한다. 헤딩 텍스트에 이 중 하나가 들어 있으면 싣는다.
WANTED: tuple[str, ...] = (
    "한 일",
    "what was done",
    "current status",
    "안 한 것",
    "다음 단계",
    "remaining",
    "uncommitted changes",
)

_TOP_HEADING = re.compile(r"^#\s+HANDOFF", re.MULTILINE)
_ANY_HEADING = re.compile(r"^(#{1,6})\s+(.*)$")


def latest_section(text: str) -> str:
    """두 번째 '# HANDOFF' 헤딩 전까지. 하나뿐이거나 없으면 전체."""
    hits = list(_TOP_HEADING.finditer(text))
    if len(hits) < 2:
        return text
    return text[: hits[1].start()]


def select_headings(text: str) -> str:
    """WANTED 에 걸리는 헤딩 블록만 이어붙인다."""
    out: list[str] = []
    keeping = False

    for line in text.splitlines():
        m = _ANY_HEADING.match(line)
        if m:
            title = m.group(2).strip().lower()
            # '# HANDOFF: ...' 같은 최상위 제목은 블록 경계로만 쓴다
            keeping = any(w in title for w in WANTED)
            if keeping:
                out.append(line)
            continue
        if keeping:
            out.append(line)

    return "\n".join(out).strip()


def read(repo_abs: str | Path) -> str | None:
    """저장소 루트의 HANDOFF.md 를 읽어 발췌한다. 없으면 None."""
    path = Path(repo_abs) / "HANDOFF.md"
    if not path.is_file():
        return None
    text = path.read_text(encoding="utf-8", errors="replace")
    return select_headings(latest_section(text))
```

- [ ] **Step 4: 테스트를 돌려 통과를 확인한다**

Run: `python -m pytest tests/test_handoff.py -v`
Expected: PASS — 9 passed

- [ ] **Step 5: 실제 인계 문서로 분량이 줄었는지 확인한다**

Run:

```bash
python -c "
from pathlib import Path
from report.handoff import read
for r in (r'C:\Users\klyhj\dev\qmeet\backend2', r'C:\Users\klyhj\dev\e2etest\qmeet'):
    full = (Path(r)/'HANDOFF.md').read_text(encoding='utf-8', errors='replace')
    got = read(r) or ''
    print(Path(r).name, '전문', len(full.splitlines()), '줄 → 발췌', len(got.splitlines()), '줄')
"
```

Expected: 두 저장소 모두 발췌가 전문보다 훨씬 짧고, `안 한 것 / 다음 단계` 또는 `Remaining Work` 내용이 들어 있다.

- [ ] **Step 6: 커밋한다**

```bash
git add report/handoff.py tests/test_handoff.py
git commit -m "feat: 인계 문서에서 진행률 판단용 헤딩만 발췌한다"
```

---

### Task 5: `report/evidence.py` + `collect_evidence.py` — 근거 파일

**Files:**
- Create: `report/evidence.py`
- Create: `collect_evidence.py`
- Create: `tests/test_evidence.py`

**Interfaces:**
- Consumes: `report.config.Config`, `report.repos.Commit`, `report.sessions.SessionEvent`
- Produces:
  - `report.evidence.RepoEvidence` — 동결 데이터클래스, 필드 `repo: str`, `category: str | None`, `branch: str | None`, `commits: tuple[Commit, ...]`, `skipped: int`, `uncommitted: tuple[str, ...]`, `event_count: int`, `prompts: tuple[str, ...]`, `handoff: str | None`, `is_git: bool`
  - `report.evidence.render(day: date, rows: Sequence[RepoEvidence], collected_at: datetime, is_past: bool) -> str` — 근거 마크다운
  - `report.evidence.active_repos(rows: Sequence[RepoEvidence]) -> list[str]` — 활동이 있었던 저장소만 (커밋·미커밋·이벤트 중 하나라도 있는 것)
  - `collect_evidence.py` CLI — `python collect_evidence.py [YYYY.M.D]`. `output/evidence/YYYY-MM-DD.md`와 `output/evidence/YYYY-MM-DD.repos.json`을 쓴다

- [ ] **Step 1: 실패하는 테스트를 쓴다**

`tests/test_evidence.py`:

```python
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
UNKNOWN = ev("golfzone/admin", event_count=14)
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
    assert "golfzone/admin" in got


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
    assert active_repos([BACKEND, E2E, IDLE]) == ["qmeet/backend2", "e2etest/qmeet"]


def test_활동_판정에_미커밋만_있어도_포함한다():
    only_uncommitted = ev("x/y", uncommitted=(" M a.py",))
    assert active_repos([only_uncommitted]) == ["x/y"]


def test_비git_저장소도_렌더된다():
    edu = ev("leadwalk_study/2026/x", category="교육", branch=None,
             is_git=False, event_count=807)
    got = render(DAY, [edu], AT, is_past=False)
    assert "leadwalk_study/2026/x" in got
    assert "git 아님" in got
```

- [ ] **Step 2: 테스트를 돌려 실패를 확인한다**

Run: `python -m pytest tests/test_evidence.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'report.evidence'`

- [ ] **Step 3: `report/evidence.py`를 쓴다**

```python
# -*- coding: utf-8 -*-
"""근거 마크다운 렌더.

행 초안을 만들지 않는다. 커밋 로그라는 그럴듯한 초안을 믿고 근거 전체를
다시 읽지 않아 미커밋 작업을 놓친 사고가 있었다. 여기서는 근거만 싣고,
진행률·구분 판단은 사람이 한다.
"""
from __future__ import annotations

import datetime as dt
from collections.abc import Sequence
from dataclasses import dataclass

from .repos import Commit

WEEKDAYS = "월화수목금토일"
PROMPT_LIMIT = 8


@dataclass(frozen=True)
class RepoEvidence:
    repo: str
    category: str | None
    branch: str | None
    commits: tuple[Commit, ...]
    skipped: int
    uncommitted: tuple[str, ...]
    event_count: int
    prompts: tuple[str, ...]
    handoff: str | None
    is_git: bool


def _has_activity(row: RepoEvidence) -> bool:
    return bool(row.commits or row.uncommitted or row.event_count)


def active_repos(rows: Sequence[RepoEvidence]) -> list[str]:
    """활동이 있었던 저장소만. build_report 의 커버리지 경고가 이걸 쓴다."""
    return [r.repo for r in rows if _has_activity(r)]


def render(
    day: dt.date,
    rows: Sequence[RepoEvidence],
    collected_at: dt.datetime,
    is_past: bool,
) -> str:
    total_mine = sum(len(r.commits) for r in rows)
    total_skipped = sum(r.skipped for r in rows)
    out: list[str] = []

    out.append("# 근거 묶음 — {} ({})".format(day.isoformat(), WEEKDAYS[day.weekday()]))
    out.append(
        "> 수집 {:%Y-%m-%d %H:%M} · 저장소 {}곳 · 본인 커밋 {}건 (타인 {}건 제외)".format(
            collected_at, len(rows), total_mine, total_skipped
        )
    )
    if is_past:
        out.append(
            "> ⚠️ **과거 날짜다.** 미커밋 정보는 그날 상태가 아니라 "
            "수집 시점 상태이므로 신뢰할 수 없다."
        )
    else:
        out.append("> ⚠️ 미커밋 정보는 수집 시점 상태다.")
    out.append("")
    out.append("행 초안은 일부러 만들지 않는다. 아래 근거를 읽고 직접 판단해 "
               "`data/{}.yaml` 을 쓴다.".format(day.isoformat()))
    out.append("")

    out.append("## 커버리지 점검")
    out.append("")
    out.append("| 저장소 | 구분(config) | 커밋 | 미커밋 | 세션 이벤트 | 인계 |")
    out.append("|---|---|---|---|---|---|")
    for r in rows:
        category = r.category or "**구분 미지정**"
        commit_cell = "(git 아님)" if not r.is_git else str(len(r.commits))
        if r.skipped:
            commit_cell += " (+타인 {} 제외)".format(r.skipped)
        out.append(
            "| {} | {} | {} | {} | {:,} | {} |".format(
                r.repo,
                category,
                commit_cell,
                "—" if not r.is_git else len(r.uncommitted),
                r.event_count,
                "✓" if r.handoff else "—",
            )
        )
    out.append("")

    for r in rows:
        if not _has_activity(r):
            continue
        head = "## {}".format(r.repo)
        head += "  `[{}]`".format(r.branch) if r.branch else "  `[git 아님]`"
        head += "  →  {}".format(r.category or "**구분 미지정**")
        out.append("---")
        out.append(head)
        out.append("")

        if r.commits:
            out.append("### 커밋 {}건".format(len(r.commits)))
            for c in r.commits:
                out.append("- {} `{}` {}".format(c.time, c.sha, c.subject))
        else:
            out.append("### 커밋 — 없음")
        out.append("")

        label = "미커밋"
        if is_past:
            label += " **[신뢰 불가 — 과거 날짜]**"
        if r.uncommitted:
            out.append("### {} {}건".format(label, len(r.uncommitted)))
            for line in r.uncommitted:
                out.append("- `{}`".format(line))
        else:
            out.append("### {} — 없음".format(label))
        out.append("")

        if r.handoff:
            out.append("### 인계 문서 (HANDOFF.md 최신 섹션 · 발췌)")
            out.append("")
            out.append(r.handoff)
            out.append("")

        if r.prompts:
            out.append(
                "### 세션 프롬프트 (자동 세션 제외 · 최대 {}건)".format(PROMPT_LIMIT)
            )
            for p in r.prompts[:PROMPT_LIMIT]:
                out.append("- {}".format(p))
            out.append("")

    return "\n".join(out).rstrip() + "\n"
```

- [ ] **Step 4: 테스트를 돌려 통과를 확인한다**

Run: `python -m pytest tests/test_evidence.py -v`
Expected: PASS — 13 passed

- [ ] **Step 5: `collect_evidence.py` CLI를 쓴다**

```python
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""근거 수집 — 하루치 작업 근거를 한 파일에 모은다.

사용법:
    python collect_evidence.py            # 오늘
    python collect_evidence.py 2026.9.8   # 특정 날짜

출력:
    output/evidence/YYYY-MM-DD.md          사람이 읽는 근거
    output/evidence/YYYY-MM-DD.repos.json  활동 있던 저장소 목록 (커버리지 검증용)
"""
from __future__ import annotations

import datetime as dt
import json
import os
import sys
from collections import Counter, defaultdict
from pathlib import Path

from report.config import load_config
from report.evidence import RepoEvidence, active_repos, render
from report.handoff import read as read_handoff
from report.repos import branch, commits, discover, git_root, to_rel, uncommitted
from report.sessions import load_events

HERE = Path(__file__).resolve().parent
OUT_DIR = HERE / "output" / "evidence"
PROJECTS_ROOT = Path(os.path.expanduser("~/.claude/projects"))


def parse_day(text: str | None) -> dt.date:
    if not text:
        return dt.date.today()
    y, m, d = (int(x) for x in text.replace("-", ".").split("."))
    return dt.date(y, m, d)


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8")
    day = parse_day(sys.argv[1] if len(sys.argv) > 1 else None)
    config = load_config(HERE / "config.yaml")

    events = load_events(day, PROJECTS_ROOT, config.ignore_prompts)
    repos = discover(events, config)

    # 이벤트를 저장소별로 접어 넣는다 (하위 디렉터리는 git 루트로 정규화)
    counts: Counter[str] = Counter()
    prompts: dict[str, list[str]] = defaultdict(list)
    resolved: dict[str, str] = {}
    for ev in events:
        if ev.cwd not in resolved:
            root = git_root(ev.cwd)
            resolved[ev.cwd] = to_rel(root or ev.cwd, config.dev_root)
        key = resolved[ev.cwd]
        counts[key] += 1
        if ev.prompt:
            prompts[key].append("{:%H:%M} · {}".format(ev.ts, ev.prompt))

    rows: list[RepoEvidence] = []
    for repo in repos:
        abs_path = Path(config.dev_root) / repo
        is_git = git_root(abs_path) is not None
        mine, skipped = commits(abs_path, day, config.me) if is_git else ([], 0)
        rows.append(
            RepoEvidence(
                repo=repo,
                category=config.category_for_repo(repo),
                branch=branch(abs_path) if is_git else None,
                commits=tuple(mine),
                skipped=skipped,
                uncommitted=tuple(uncommitted(abs_path)) if is_git else (),
                event_count=counts.get(repo, 0),
                prompts=tuple(prompts.get(repo, ())),
                handoff=read_handoff(abs_path),
                is_git=is_git,
            )
        )

    # 활동 많은 순으로 정렬해 중요한 것부터 읽게 한다
    rows.sort(key=lambda r: (-(len(r.commits) * 100 + r.event_count), r.repo))

    is_past = day < dt.date.today()
    text = render(day, rows, dt.datetime.now(), is_past)

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    md_path = OUT_DIR / "{}.md".format(day.isoformat())
    json_path = OUT_DIR / "{}.repos.json".format(day.isoformat())
    md_path.write_text(text, encoding="utf-8")
    json_path.write_text(
        json.dumps(active_repos(rows), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    print("[OK] {}  ({}줄)".format(md_path.relative_to(HERE), len(text.splitlines())))
    print("[OK] {}".format(json_path.relative_to(HERE)))
    unknown = [r.repo for r in rows if r.category is None and (r.commits or r.event_count)]
    if unknown:
        print("[확인] config.yaml 에 없는 저장소: {}".format(", ".join(unknown)))
    if is_past:
        print("[주의] 과거 날짜다 — 미커밋 정보는 신뢰할 수 없다")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 6: 실제로 돌려 근거 파일을 확인한다**

Run: `python collect_evidence.py 2026.9.8`

Expected:
- `output/evidence/2026-09-08.md`가 생기고, 커버리지 표에 `qmeet/backend2`·`qmeet/front`·`qmeet/qmeet_ai`·`qmeet/qmeet-dev-ssh`·`e2etest/qmeet`·`e2etest/playwright_base`가 모두 있다.
- `e2etest/qmeet`의 미커밋 건수가 0이 아니다 (2026-09-08 누락 사고의 원인이 근거에 드러난다).
- `qmeet/qmeet_ai` 줄에 `(+타인 5 제외)`가 붙는다.
- `output/evidence/2026-09-08.repos.json`이 생긴다.
- 파일 어디에도 `진행률`·`100%` 문자열이 없다 (행 초안 미생성).

- [ ] **Step 7: 커밋한다**

```bash
git add report/evidence.py collect_evidence.py tests/test_evidence.py
git commit -m "feat: 근거 수집 CLI — 커밋·미커밋·인계·세션을 전수로 한 파일에 모은다"
```

---

### Task 6: `report/daydata.py` — 날짜 데이터 파일과 검증

**Files:**
- Create: `report/daydata.py`
- Create: `tests/test_daydata.py`

**Interfaces:**
- Consumes: `report.config.Config`, `report.config.normalize_repo`
- Produces:
  - `report.daydata.DayDataError(Exception)`
  - `report.daydata.Location` — 동결 데이터클래스, 필드 `repo: str`, `branch: str`
  - `report.daydata.Item` — 동결 데이터클래스, 필드 `task: str`, `progress: str`, `note: str`, `locations: tuple[Location, ...]`
  - `report.daydata.Row` — 동결 데이터클래스, 필드 `category: str`, `items: tuple[Item, ...]`
  - `report.daydata.DayReport` — 동결 데이터클래스, 필드 `date: str`, `rows: tuple[Row, ...]`
  - `report.daydata.load_day(path: str | Path, config: Config) -> tuple[DayReport, list[str]]` — `(보고서, 경고 목록)`. 규칙 위반은 `DayDataError`로 던진다
  - `report.daydata.coverage_warnings(report: DayReport, active: Sequence[str]) -> list[str]`

- [ ] **Step 1: 실패하는 테스트를 쓴다**

`tests/test_daydata.py`:

```python
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
```

- [ ] **Step 2: 테스트를 돌려 실패를 확인한다**

Run: `python -m pytest tests/test_daydata.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'report.daydata'`

- [ ] **Step 3: 최소 구현을 쓴다**

`report/daydata.py`:

```python
# -*- coding: utf-8 -*-
"""data/YYYY-MM-DD.yaml 로딩과 검증.

사람이 근거를 읽고 판단한 결과만 담는다. 구분 순서는 config.yaml 을 따르고
파일 순서는 무시한다 — 날짜별로 구분이 뒤바뀌면 추이를 못 본다.
"""
from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

import yaml

from .config import PROGRESS_RE, Config, normalize_repo


class DayDataError(Exception):
    """날짜 데이터 파일이 규칙에 맞지 않을 때."""


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
    warnings: list[str] = []

    date_label = str(raw.get("date") or "").strip()
    if not date_label:
        raise DayDataError("{}: date 가 없다".format(path.name))

    rows: list[Row] = []
    seen: set[str] = set()

    for entry in raw.get("rows") or []:
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
        if not raw_items:
            raise DayDataError("{}: 항목이 없는 구분이다".format(where))

        items: list[Item] = []
        for raw_item in raw_items:
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
        if repo not in used
    ]
```

- [ ] **Step 4: 테스트를 돌려 통과를 확인한다**

Run: `python -m pytest tests/test_daydata.py -v`
Expected: PASS — 17 passed

- [ ] **Step 5: 커밋한다**

```bash
git add report/daydata.py tests/test_daydata.py
git commit -m "feat: 날짜 데이터 파일 검증 — 커버리지 미반영 저장소를 이름으로 지적한다"
```

---

### Task 7: `report/excel.py` + `build_report.py` 개편

현행 `build_report.py`의 렌더링 코드를 `report/excel.py`로 옮기고, `REPORTS` 딕셔너리를 `data/*.yaml` 읽기로 바꾼다. 렌더링 결과는 바뀌지 않아야 한다.

**Files:**
- Create: `report/excel.py`
- Create: `tests/test_excel.py`
- Modify: `build_report.py` (전면 교체)

**Interfaces:**
- Consumes: `report.config.Config`, `report.daydata.DayReport`, `report.daydata.Row`, `report.daydata.Item`, `report.daydata.Location`
- Produces:
  - `report.excel.location_text(locations: Sequence[Location], dev_root: str) -> str` — F열 문자열. 위치마다 `"<절대경로>\n[<브랜치>]"`, 여러 개면 개행으로 이음
  - `report.excel.flatten(report: DayReport, config: Config) -> list[tuple[str, str, str, str, str, str]]` — TSV용 6열 행 목록. 날짜는 첫 행에만, 구분은 그룹 첫 행에만
  - `report.excel.write_xlsx(report: DayReport, config: Config, path: Path) -> tuple[Path, int]` — `(실제로 쓴 경로, 데이터 행 수)`. 대상이 잠겨 있으면 `_` 접두사 경로에 쓴다
  - `report.excel.write_tsv(report: DayReport, config: Config, path: Path) -> None`

- [ ] **Step 1: 실패하는 테스트를 쓴다**

`tests/test_excel.py`:

```python
# -*- coding: utf-8 -*-
"""엑셀·TSV 렌더 테스트."""
from openpyxl import load_workbook

from report.config import Category, Config
from report.daydata import DayReport, Item, Location, Row
from report.excel import flatten, location_text, write_tsv, write_xlsx

CFG = Config(
    me=("me@example.com",),
    categories=(
        Category(name="백엔드 공수산정", progress="85%", repos=("qmeet/backend2",)),
        Category(name="자동화", repos=("e2etest/qmeet",)),
    ),
    dev_root=r"C:\Users\klyhj\dev",
)

REPORT = DayReport(
    date="2026.9.08",
    rows=(
        Row(
            category="백엔드 공수산정",
            items=(
                Item("추천 환경 저장", "100%", "",
                     (Location("qmeet/backend2", "feature/x"),)),
                Item("문서 기준 정정", "100%", "",
                     (Location("qmeet/backend2", "feature/x"),)),
            ),
        ),
        Row(
            category="자동화",
            items=(
                Item("TC 명세 작성", "80%", "QM103 대기",
                     (Location("e2etest/qmeet", "main"),)),
            ),
        ),
    ),
)


def test_F열에_절대경로와_브랜치를_넣는다():
    got = location_text((Location("qmeet/front", "feature/y"),), CFG.dev_root)
    assert got == "C:\\Users\\klyhj\\dev\\qmeet\\front\n[feature/y]"


def test_저장소가_여러_곳이면_개행으로_이어붙인다():
    got = location_text(
        (Location("a/b", "main"), Location("c/d", "main")), CFG.dev_root
    )
    assert got.count("[main]") == 2
    assert got.count("\n") == 3


def test_날짜는_첫_행에만_구분은_그룹_첫_행에만():
    rows = flatten(REPORT, CFG)
    assert [r[0] for r in rows] == ["2026.9.08", "", ""]
    assert [r[1] for r in rows] == ["백엔드 공수산정(85%)", "", "자동화"]


def test_작업_진행률_비고를_그대로_옮긴다():
    rows = flatten(REPORT, CFG)
    assert rows[2][2] == "TC 명세 작성"
    assert rows[2][3] == "80%"
    assert rows[2][4] == "QM103 대기"


def test_엑셀을_쓰고_행수를_돌려준다(tmp_path):
    path, total = write_xlsx(REPORT, CFG, tmp_path / "out.xlsx")
    assert total == 3
    assert path.exists()


def test_엑셀_열구성과_병합이_양식에_맞는다(tmp_path):
    path, _ = write_xlsx(REPORT, CFG, tmp_path / "out.xlsx")
    ws = load_workbook(path).active
    assert ws.max_row == 3
    assert ws.max_column == 6
    merged = {str(m) for m in ws.merged_cells.ranges}
    assert "A1:A3" in merged      # 날짜 전체 병합
    assert "B1:B2" in merged      # 백엔드 2행 병합
    assert "B3:B3" not in merged  # 1행짜리 구분은 병합하지 않는다
    assert ws.cell(1, 2).value == "백엔드 공수산정(85%)"
    assert ws.cell(3, 4).value == "80%"


def test_엑셀_열너비와_글꼴이_양식에_맞는다(tmp_path):
    path, _ = write_xlsx(REPORT, CFG, tmp_path / "out.xlsx")
    ws = load_workbook(path).active
    widths = [ws.column_dimensions[c].width for c in "ABCDEF"]
    assert widths == [12, 17, 42, 9, 36, 50]
    assert ws.cell(1, 3).font.name == "맑은 고딕"
    assert ws.cell(1, 6).font.name == "Consolas"
    assert ws.cell(1, 6).font.size == 8


def test_대상이_잠겨_있으면_밑줄_접두사로_쓴다(tmp_path, monkeypatch):
    target = tmp_path / "out.xlsx"

    real_save = __import__("openpyxl").Workbook.save
    calls = {"n": 0}

    def flaky(self, filename):
        calls["n"] += 1
        if calls["n"] == 1:
            raise PermissionError("열려 있음")
        return real_save(self, filename)

    monkeypatch.setattr(__import__("openpyxl").Workbook, "save", flaky)
    path, total = write_xlsx(REPORT, CFG, target)
    assert path.name == "_out.xlsx"
    assert total == 3


def test_TSV_를_탭으로_쓴다(tmp_path):
    out = tmp_path / "out.tsv"
    write_tsv(REPORT, CFG, out)
    lines = out.read_text(encoding="utf-8-sig").splitlines()
    assert len(lines) == 3
    assert lines[0].split("\t")[0] == "2026.9.08"
    assert len(lines[0].split("\t")) == 6
    # 셀 안 개행은 한 칸으로 눌러 한 줄을 유지한다
    assert "\n" not in lines[0]
```

- [ ] **Step 2: 테스트를 돌려 실패를 확인한다**

Run: `python -m pytest tests/test_excel.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'report.excel'`

- [ ] **Step 3: `report/excel.py`를 쓴다**

```python
# -*- coding: utf-8 -*-
"""엑셀·TSV 렌더. 기존 보고 양식(6열)을 그대로 유지한다.

열 구성: A 날짜 / B 구분 / C 세부 작업 / D 진행률 / E 비고 / F 폴더 위치
"""
from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path

from openpyxl import Workbook
from openpyxl.styles import Alignment, Border, Font, Side

from .config import Config
from .daydata import DayReport, Location

WIDTHS = (12, 17, 42, 9, 36, 50)
ROW_HEIGHT = 30
ROW_HEIGHT_TALL = 58

FONT = Font(name="맑은 고딕", size=10)
FONT_PATH = Font(name="Consolas", size=8, color="444444")
_THIN = Side(style="thin", color="000000")
BORDER = Border(left=_THIN, right=_THIN, top=_THIN, bottom=_THIN)
CENTER = Alignment(horizontal="center", vertical="center", wrap_text=True)
LEFT = Alignment(horizontal="left", vertical="center", wrap_text=True)


def location_text(locations: Sequence[Location], dev_root: str) -> str:
    """F열 문자열. 위치마다 '<절대경로>\\n[<브랜치>]'."""
    parts = []
    for loc in locations:
        abs_path = str(Path(dev_root) / loc.repo)
        parts.append("{}\n[{}]".format(abs_path, loc.branch))
    return "\n".join(parts)


def flatten(
    report: DayReport, config: Config
) -> list[tuple[str, str, str, str, str, str]]:
    """TSV 용 6열 행 목록. 셀 안 개행은 한 칸으로 눌러 한 줄을 유지한다."""
    out: list[tuple[str, str, str, str, str, str]] = []
    first = True
    for row in report.rows:
        group_first = True
        for item in row.items:
            out.append(
                (
                    report.date if first else "",
                    config.label(row.category) if group_first else "",
                    item.task,
                    item.progress,
                    item.note,
                    location_text(item.locations, config.dev_root).replace("\n", " "),
                )
            )
            first = False
            group_first = False
    return out


def write_xlsx(
    report: DayReport, config: Config, path: str | Path
) -> tuple[Path, int]:
    """엑셀을 쓴다. 대상이 잠겨 있으면 '_' 접두사 경로로 쓴다."""
    wb = Workbook()
    ws = wb.active
    ws.title = "일일보고"

    r = 1
    for row in report.rows:
        start = r
        for item in row.items:
            ws.cell(r, 2, config.label(row.category) if r == start else None)
            ws.cell(r, 3, item.task)
            ws.cell(r, 4, item.progress)
            ws.cell(r, 5, item.note)
            ws.cell(r, 6, location_text(item.locations, config.dev_root))
            r += 1
        if len(row.items) > 1:
            ws.merge_cells(
                start_row=start, start_column=2, end_row=r - 1, end_column=2
            )

    total = r - 1
    ws.cell(1, 1, report.date)
    ws.merge_cells(start_row=1, start_column=1, end_row=total, end_column=1)

    for cells in ws.iter_rows(min_row=1, max_row=total, min_col=1, max_col=6):
        for cell in cells:
            cell.border = BORDER
            cell.font = FONT_PATH if cell.column == 6 else FONT
            cell.alignment = CENTER if cell.column in (1, 2, 4) else LEFT

    for col, width in zip("ABCDEF", WIDTHS):
        ws.column_dimensions[col].width = width
    for i in range(1, total + 1):
        value = ws.cell(i, 6).value or ""
        ws.row_dimensions[i].height = (
            ROW_HEIGHT_TALL if value.count("\n") >= 3 else ROW_HEIGHT
        )

    path = Path(path)
    try:
        wb.save(path)
        return path, total
    except PermissionError:
        fallback = path.with_name("_" + path.name)
        wb.save(fallback)
        return fallback, total


def write_tsv(report: DayReport, config: Config, path: str | Path) -> None:
    with open(path, "w", encoding="utf-8-sig", newline="") as fh:
        for row in flatten(report, config):
            fh.write("\t".join(row) + "\r\n")
```

- [ ] **Step 4: 테스트를 돌려 통과를 확인한다**

Run: `python -m pytest tests/test_excel.py -v`
Expected: PASS — 9 passed

- [ ] **Step 5: `build_report.py`를 전면 교체한다**

```python
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
```

- [ ] **Step 6: 전체 테스트를 돌린다**

Run: `python -m pytest -v`
Expected: PASS — 73 passed (Task 1~7 합계)

- [ ] **Step 7: 커밋한다**

```bash
git add report/excel.py tests/test_excel.py build_report.py
git commit -m "refactor: REPORTS 딕셔너리를 없애고 data/*.yaml 을 읽는다"
```

---

### Task 8: 현행 데이터 이관과 회귀 확인

`build_report.py`에 있던 `REPORTS` 두 날짜분을 `data/*.yaml`로 옮기고, 새 파이프라인이 **오늘 만든 엑셀과 같은 결과**를 내는지 확인한다.

**Files:**
- Create: `data/2026-09-07.yaml`
- Create: `data/2026-09-08.yaml`
- Create: `tests/test_regression.py`

**Interfaces:**
- Consumes: `report.config.load_config`, `report.daydata.load_day`, `report.excel.flatten`
- Produces: 없음 (마지막 태스크)

- [ ] **Step 1: `data/2026-09-08.yaml`을 쓴다**

```yaml
# 2026-09-08 일일보고 데이터.
# 근거: output/evidence/2026-09-08.md (커밋·미커밋·인계 문서·세션)
date: 2026.9.08
rows:
  - category: 백엔드 공수산정
    default_location: { repo: qmeet/backend2, branch: feature/ai_effortEstimate_20260901 }
    items:
      - task: AI 추천 테스트 환경(RCMD_PLTF_CD) 저장
        progress: 100%
      - task: API 문서 공수 기준 정정(환경 1종)
        progress: 100%

  - category: 프론트 공수산정
    default_location: { repo: qmeet/front, branch: feature-ai-effortEsttimate_20260901 }
    items:
      - task: 결과 화면 AI 추천 테스트 환경 기본 선택
        progress: 100%
      - task: 결과 화면 인원·환경 수 즉시 재계산
        progress: 100%
      - task: 9/8 이전 산정 건 기존 값 유지 가드
        progress: 100%
      - task: 결과 배너 공수 숫자 애니메이션
        progress: 100%
      - task: 실제 기획서(11장) 결과 계산식 E2E 검증
        progress: 100%
        note: TC 172건·3분 10초·오류 0

  - category: AI 서버 공수산정
    default_location: { repo: qmeet/qmeet_ai, branch: feature/orchestrator }
    items:
      - task: 기획서 기준 테스트 환경 판정 후 큐밋 전달
        progress: 100%
      - task: 판정 환경 1종 기준으로 공수 산정
        progress: 100%
        note: 견적 약 3배 과다 산출 수정
      - task: 진행 화면 단계 표시 역행 수정
        progress: 100%
        note: 9곳 → 0곳
      - task: 추천 환경 값 견적 경로 누락 수정
        progress: 100%
        note: 실제 AI 재검증 대기

  - category: 인프라
    default_location: { repo: qmeet/qmeet-dev-ssh, branch: main }
    items:
      - task: v369 고정 버전 개발환경 구축
        progress: 100%
        note: v369.dev.l-walk.com 개통·결함 6건 수정

  - category: 자동화
    default_location: { repo: e2etest/qmeet, branch: main }
    items:
      - task: 프로젝트 등록 TC 명세 작성(QM101~106)
        progress: 80%
        note: QM103 검증 대상 확정 대기
      - task: 프로젝트 등록 자동화 구현(QM101·102·104~106)
        progress: 100%
        note: 테스트 11건 전체 통과 · 커밋 대기
      - task: 로그인 공통 처리·화면 모듈 2종 구현
        progress: 100%
        note: 프로젝트명 칸 data-cy 개발팀 요청 필요
      - task: 실패 증적(Evidence) 수집 검증
        progress: 100%
        note: 의도적 실패 TC로 확인
      - task: Base 예제 테스트 정리
        progress: 100%
        note: 11건·895줄 삭제, 전체 통과
      - task: TC 입력 양식 제정
        progress: 100%
        note: 양식 2종(문서·엑셀)
        locations:
          - { repo: e2etest/playwright_base, branch: main }
          - { repo: e2etest/qmeet, branch: main }
      - task: Q-Meet 데모 프로젝트 영구 위치 이전
        progress: 100%

  - category: 교육
    default_location:
      repo: leadwalk_study/2026/second-half-automation-training/repos
      branch: git 아님 · 교육생 5명 폴더
    items:
      - task: 하반기 자동화 교육 4주차 과제 피드백
        progress: 100%
        note: 5명 전원 전달 완료
```

- [ ] **Step 2: `data/2026-09-07.yaml`을 쓴다**

```yaml
# 2026-09-07 일일보고 데이터.
# 근거: 각 저장소 커밋 로그 + 세션 기록.
# 미커밋 작업은 과거 날짜라 복원할 수 없다 (스펙 「한계」).
date: 2026.9.07
rows:
  - category: 백엔드 공수산정
    default_location: { repo: qmeet/backend2, branch: feature/ai_effortEstimate_20260901 }
    items:
      - task: 진행 단계(substage) 계약 정의·문서 반영
        progress: 100%
        note: 가짜 AI 서버로 중계 확인

  - category: 프론트 공수산정
    default_location: { repo: qmeet/front, branch: feature-ai-effortEsttimate_20260901 }
    items:
      - task: 진행 화면 substage 칩 연동
        progress: 100%
        note: AI 서버 2026-09-06 변경 반영
      - task: 모바일에서 헤더가 팝업을 덮는 문제 수정
        progress: 100%
        note: 리뷰 8번
      - task: 실제 기획서(11장) 진행 화면 E2E 완주
        progress: 100%
        note: substage 칩 동작 확인
      - task: 프론트 연동 가이드 현황표 갱신
        progress: 100%

  - category: AI 서버 공수산정
    default_location: { repo: qmeet/qmeet_ai, branch: feature/orchestrator }
    items:
      - task: 기획서 영구 보관 정책·S3 보안 방안 검토
        progress: 100%
        note: 정책 검토(코드 변경 없음)
      - task: 산정 결과값(totMd·dsgnMd·expDayCnt) 로직 파악
        progress: 100%
        note: 정책 검토(코드 변경 없음)

  - category: 시안
    default_location: { repo: qmeet/front_design_prototype, branch: main }
    items:
      - task: 공수산정 진입 화면 시안 K·L·M·N 재설계
        progress: 100%
        note: 벤치마크 레이아웃 3종 · 입력→출력 대조
      - task: 공수산정 PRD·프로젝트 등록 개선 3단계 PRD 작성
        progress: 100%
      - task: 한글 파일명에서 프리커밋 훅이 죽던 문제 수정
        progress: 100%
        note: css-guard
      - task: 폐기 시안 2건·문구변경요청 양식 2건 정리
        progress: 100%

  - category: GA4
    default_location: { repo: qmeet/backend2, branch: feature/ai_effortEstimate_20260901 }
    items:
      - task: GA4 회원가입 이벤트 연동
        progress: 60%
        note: (not set) 원인 규명 · 운영 전용 전송 가드 검증
        locations:
          - { repo: qmeet/backend2, branch: feature/ai_effortEstimate_20260901 }
          - { repo: qmeet/front, branch: feature-ai-effortEsttimate_20260901 }

  - category: 자동화
    default_location: { repo: e2etest/playwright_base, branch: main }
    items:
      - task: 자동화 Base 템플릿 저장소 구축
        progress: 100%
        note: 껍데기만 유지 · 실제 자동화는 별도 저장소
      - task: 오래된 artifacts 실행 폴더 자동 정리 기능
        progress: 100%
      - task: 자동화 개발자용 스크립트 작성 가이드 작성
        progress: 100%
      - task: Claude 협업 가이드(9장)·규칙 문서 추가
        progress: 100%
      - task: 브랜치 정리 · Claude 단독 자동화 실증
        progress: 100%
```

- [ ] **Step 3: 회귀 테스트를 쓴다**

`tests/test_regression.py`:

```python
# -*- coding: utf-8 -*-
"""실제 config.yaml·data/*.yaml 회귀 테스트.

2026-09-08 손으로 만든 엑셀(20행)과 2026-09-07(17행)의 행 수·구분 순서를
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
    assert config.label("백엔드 공수산정") == "백엔드 공수산정(85%)"


@pytest.mark.parametrize(
    "stem, expected_rows",
    [("2026-09-07", 17), ("2026-09-08", 20)],
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
```

- [ ] **Step 4: 회귀 테스트를 돌려 통과를 확인한다**

Run: `python -m pytest tests/test_regression.py -v`
Expected: PASS — 8 passed

`test_모든_날짜_파일에_경고가_없다`가 실패하면 `data/*.yaml`의 `repo` 값에 오타가 있거나 실제 폴더 경로가 다르다. 경고 메시지에 저장소 이름이 나오므로 그걸 고친다.

- [ ] **Step 5: 두 날짜를 실제로 생성해 손으로 만든 결과와 대조한다**

Run:

```bash
python collect_evidence.py 2026.9.8
python collect_evidence.py 2026.9.7
python build_report.py
```

Expected:
- `output/일일보고-2026-09-07.xlsx` — 17행, 경고 없음
- `output/일일보고-2026-09-08.xlsx` — 20행, 경고 없음
- 커버리지 경고가 나오면 근거에는 활동이 있는데 `data/*.yaml`에 안 옮긴 저장소가 있다는 뜻이다. 저장소 이름이 찍히므로 근거 파일의 그 절을 읽고 항목을 추가한다.

- [ ] **Step 6: 엑셀 내용을 눈으로 확인한다**

Run:

```bash
python -c "
import sys; sys.stdout.reconfigure(encoding='utf-8')
from openpyxl import load_workbook
for f in ('output/일일보고-2026-09-07.xlsx', 'output/일일보고-2026-09-08.xlsx'):
    ws = load_workbook(f).active
    print('#', f, ws.max_row, '행 x', ws.max_column, '열')
    print('  병합:', sorted(str(m) for m in ws.merged_cells.ranges))
"
```

Expected: 9/07은 17행, 9/08은 20행. 병합 범위에 `A1:A17`·`A1:A20`이 각각 있고, 구분 그룹 병합이 2행 이상인 구분에만 있다.

- [ ] **Step 7: 전체 테스트를 돌린다**

Run: `python -m pytest -v`
Expected: PASS — 81 passed

- [ ] **Step 8: 커밋한다**

```bash
git add data/2026-09-07.yaml data/2026-09-08.yaml tests/test_regression.py
git commit -m "feat: 2026-09-07·09-08 데이터 이관 + 손으로 만든 결과와의 회귀 테스트"
```

---

## Self-Review

**1. 스펙 커버리지**

| 스펙 요구 | 담당 태스크 |
|---|---|
| 설계 결정 1 — Claude가 판단, 스크립트는 수집 | Task 5 (`collect_evidence.py`), Task 6 (`data/*.yaml`) |
| 설계 결정 2 — 고정 구분 목록 + `by_content` | Task 1 (`config.py`, `config.yaml`) |
| 설계 결정 3 — 항목 진행률은 Claude, 모듈은 사람 | Task 1 (`Category.progress`, `Config.label`), Task 6 (`Item.progress` 검증) |
| 설계 결정 4 — 행 초안 미생성 | Task 5 (`test_행_초안을_만들지_않는다`) |
| `config.yaml` 전체 필드 | Task 1 Step 6 |
| 저장소 자동 발견 (합집합) | Task 3 (`discover`) |
| cwd 집계 버그 수정 | Task 2 (`load_events`) |
| 미커밋 시간 한계 표기 | Task 5 (`render(..., is_past=)`) |
| 인계 문서 헤딩 선별 | Task 4 (`WANTED`, `select_headings`) |
| 근거 출력 형태 (커버리지 표 + 저장소별 절) | Task 5 (`render`) |
| `data/*.yaml` 형식 (`default_location`/`locations`/`note`) | Task 6 |
| 브랜치를 데이터에 박기 | Task 6 (`Location.branch`), Task 7 (`location_text`는 git 조회 안 함) |
| `build_report.py` 개편 (`REPORTS` 제거) | Task 7 |
| 구분 순서를 config 순서로 | Task 6 (`load_day` 정렬), Task 8 (`test_구분이_config_순서로_나온다`) |
| 엑셀 열 구성·너비·글꼴·병합 유지 | Task 7 (`test_엑셀_열구성과_병합이_양식에_맞는다`, `test_엑셀_열너비와_글꼴이_양식에_맞는다`) |
| 검증 — 구분 오타 에러 | Task 6 (`test_config_에_없는_구분이면_에러`) |
| 검증 — 진행률 형식 에러 | Task 1, Task 6 |
| 검증 — 저장소 없음 경고 | Task 6 (`test_없는_저장소는_경고만_낸다`) |
| 검증 — 커버리지 미반영 경고 | Task 6 (`coverage_warnings`), Task 7 (`build_one`) |
| 사고 3건 방지 (미커밋 누락 / cwd 소실 / 타인 커밋) | Task 6 / Task 2 / Task 3 |
| `requirements.txt` 갱신 | Task 1 Step 1 |
| `daily_report.py` 유지 | 어느 태스크도 건드리지 않는다 |
| cp949 크래시 방지 | Global Constraints + Task 5·7 엔트리의 `reconfigure` |

빠진 스펙 요구 없음.

**2. 플레이스홀더 점검**

`TBD`·`TODO`·"적절히 처리"류 없음. 모든 코드 단계에 실제 코드가 들어 있고, 모든 테스트 단계에 실행 명령과 기대 결과가 있다.

**3. 타입 일관성 점검**

- `PROGRESS_RE`는 Task 1 `report/config.py`에 정의하고 Task 6에서 `from .config import PROGRESS_RE`로 재사용한다. 정규식이 두 곳에 갈라지지 않는다.
- `normalize_repo`도 Task 1에 정의하고 Task 3·6에서 쓴다.
- `Location`은 Task 6 `report/daydata.py`에만 정의하고 Task 7이 `from .daydata import Location`으로 쓴다. `report/excel.py`가 자체 정의하지 않는다.
- `commits()`는 Task 3 인터페이스와 Task 5 호출부 모두 `tuple[list[Commit], int]`로 일치한다.
- `write_xlsx()`는 Task 7 인터페이스와 Task 8 검증 단계 모두 `(경로, 행 수)`를 돌려준다.
- `load_day()`는 Task 6 인터페이스와 Task 7·8 호출부 모두 `(DayReport, list[str])`로 일치한다.
- `RepoEvidence` 필드 이름은 Task 5 정의부와 `collect_evidence.py` 생성부가 일치한다 (`repo`·`category`·`branch`·`commits`·`skipped`·`uncommitted`·`event_count`·`prompts`·`handoff`·`is_git`).

---

## 테스트 수 합계

| Task | 파일 | 테스트 |
|---|---|---|
| 1 | `tests/test_config.py` | 10 |
| 2 | `tests/test_sessions.py` | 9 |
| 3 | `tests/test_repos.py` | 16 |
| 4 | `tests/test_handoff.py` | 9 |
| 5 | `tests/test_evidence.py` | 13 |
| 6 | `tests/test_daydata.py` | 17 |
| 7 | `tests/test_excel.py` | 9 |
| 8 | `tests/test_regression.py` | 8 |
| | **합계** | **81** |
