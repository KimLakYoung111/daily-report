# HANDOFF: 일일보고 엑셀 생성 자동화 — 8태스크 완료, `main` 머지됨

## Goal

대표님께 제출하는 일일보고(스프레드시트 한 장)를 자동 생성한다. 핵심 설계는
**스크립트가 근거를 전수로 모으고, 판단은 사람이 한다**. 스크립트는 행 초안을
만들지 않는다 — 그럴듯한 초안이 있으면 근거를 다시 읽지 않게 되고, 그래서 실제로
작업 6행을 놓친 사고가 이 프로젝트의 출발점이다.

## Current Status: Completed — `main`에 머지·푸시됨

계획 8태스크 + 최종 전체 리뷰 후 수정 웨이브 1회까지 끝냈고, 2026-09-09에 작업
브랜치를 `main`에 머지·푸시하고 지웠다. 열린 PR은 없다.

- `main` = `origin/main` (작업 브랜치 `claude/claudecode-daily-report-xqj8sp` 삭제됨, merge-base `a73ef33`)
- 테스트 **127 passed** (`python -m pytest -q`)
- 태스크별 리뷰 8회 전부 클린, 최종 전체 리뷰 → 수정 웨이브 → 범위 한정 재리뷰
  "Safe to merge"

설계·계획·판정 근거는 중복하지 않는다. 아래 문서를 볼 것:

| 문서 | 내용 |
|---|---|
| `docs/superpowers/specs/2026-09-08-daily-report-automation-design.md` | 설계 결정 4개와 「한계」 |
| `docs/superpowers/plans/2026-09-08-daily-report-automation.md` | 8태스크 구현 계획 |
| `docs/superpowers/decisions/2026-09-08-daily-report-automation-ledger.md` | **판정 22건의 발견·이유·틀렸을 때 비용** |
| `README.md` | 사용법·config 관리 항목·한계 |

### What Was Done

| 모듈 | 역할 | 검증 |
|---|---|---|
| `report/config.py` | `config.yaml` 로딩·검증. `is_under` 경로 세그먼트 경계 술어 | 테스트 |
| `report/sessions.py` | 세션 `*.jsonl` → **이벤트별 cwd** 이벤트 목록 | 테스트 + 실데이터 |
| `report/repos.py` | 저장소 자동 발견(세션 cwd ∪ config), 커밋·미커밋·브랜치 | 테스트 + 실저장소 |
| `report/handoff.py` | `HANDOFF.md` 최신 섹션에서 진행률 판단용 헤딩 발췌 | 테스트 + 실문서 |
| `report/evidence.py` | 근거 마크다운 + 커버리지 사이드카 렌더 | 테스트 + 실행 |
| `report/daydata.py` | `data/*.yaml` 검증 + `coverage_warnings` | 테스트 |
| `report/excel.py` | 엑셀·TSV 렌더 (6열 양식) | 테스트 + 워크북 실측 |
| `collect_evidence.py` | CLI — 근거 수집 | 실행 (3일치) |
| `build_report.py` | CLI — 보고서 렌더 | 실행 (3일치) |
| `data/2026-09-07.yaml` `data/2026-09-08.yaml` | 보고서 행 데이터 (17행 / 21행) | 회귀 테스트 |
| `data/2026-09-09.yaml` | 보고서 행 데이터 (18행) — **개발이 아니라 실사용한 첫 날** | 회귀 기준선 없음 (손으로 만든 원본이 없다) |

**도구가 자기 값을 증명한 지점**: 첫 실제 실행에서 손으로 만든 9/08 보고서의 누락을
잡았다 — `qmeet/front_design_prototype`(시안)의 커밋 `b1a909a` 12:46. 그게 지금
21행 중 21번째 행이다. 손으로 만들 때 경로를 `dev/front_design_prototype`으로 찍어
"git 아님"을 받고 재확인하지 않은 것이 원인이었다.

### What Was NOT Done

1. ~~머지·PR 안 함~~ — **2026-09-09 `main`에 머지·푸시하고 브랜치를 지웠다.**
2. **최종 리뷰어 제안 3건 보류** — 스펙을 건드려서 사용자 승인 대기 (원장 Ruling 19):
   단일 진입점 `daily.py` / `--scaffold`(골격 생성 — 「행 초안 금지」 결정을 직접
   건드림) / 사이드카를 추적 대상 `data/`로 이동.
3. **이월 minor 12건** — 원장의 `minor (deferred)` 줄. 최종 리뷰가 6건은 "그대로 둬도
   된다"로 트리아지했고 5건은 수정 웨이브에서 처리했다. 남은 것은 전부 미관·폴리시.
4. **git worktree 이중 계수** — 고치지 않고 스펙 「한계」에 기록 (Ruling 18).

## What Worked

- **판정마다 "판별력 있는 테스트"를 요구한 것.** 계획은 테스트 81개를 예상했는데
  실제로 127개가 됐다. 리뷰어에게 "이 테스트를 되돌리면 실제로 실패하는가"를
  판정하게 한 결과다. Task 1에서 판별력 없는 테스트가 이월 minor로 남은 뒤로 매
  라운드 요구했다.
- **구현자에게 "브리프가 틀리면 물어보라"고 명시한 것.** 6명이 escalate했고 전원
  옳았다. 그중 2건은 **내(컨트롤러) 추론의 오류**였다 — 원장 Ruling 13·20.
- **리뷰어에게 "구현자 보고서를 신뢰하지 말라"고 요구한 것.** Task 7에서 구현자가
  "여섯 필드 전부 처리"라고 보고했으나 실제 5/6이었고 리뷰어가 diff로 잡았다.
- **추측 대신 측정.** 프롬프트 멀티블록 우려는 실측 3,541턴 중 0건이라 수정 없이
  이월했고, `--since` vs `--since-as-filter`는 저장소 6곳에서 결과 동일함을 측정해
  안전하게 교체했다.

## What Didn't Work / Gotchas

다음 사람이 같은 함정에 빠지지 않게 — 전부 이 세션에서 실제로 물린 것들이다.

1. **`git log --since`는 필터가 아니라 순회 중단 최적화다.** 범위보다 오래된 커밋을
   만나면 그 자리에서 멈춘다. 범위 밖 날짜가 HEAD면 그 아래 커밋을 전부 놓친다.
   `--since-as-filter`(git ≥ 2.34)가 진짜 필터다. `tests/test_repos.py`의 픽스처가
   일부러 비시간순 HEAD를 만들어 이 회귀를 감시한다 — 시간순으로 재배열하지 말 것.
2. **`git status --porcelain`이 한글 파일명을 8진수로 이스케이프한다**
   (`"\355\225\234..."`). `core.quotepath` 기본값이 true라서다. `_git()`이
   `-c core.quotepath=false`를 넣는다.
3. **커밋 없는 새 `git init` 저장소는 `rev-parse --abbrev-ref HEAD`가 실패하는데
   stderr에 "not a git repository"가 없다** (`fatal: ambiguous argument 'HEAD'`).
   `_git`이 이 문구도 조용한 패턴으로 갖고 있다. 빼면 `dev_root` 아래 새 폴더 하나로
   수집 전체가 크래시한다.
4. **`/compact`는 `ignore_prompts`에 걸리지 않는다.** 그 목록엔 보안 리뷰·세션
   이어받기 두 패턴뿐이다. 그래서 `golfzone/admin`이 9/07에 활동으로 잡히고 경고가
   난다 — **정상이다**(Ruling 16). 슬래시 명령 일괄 제외는 `/code-review`·`/handoff`
   같은 진짜 작업 요청을 억제하므로 하지 말 것.
5. **`daily_report.py`(구 스크립트)는 세션의 첫 cwd로만 집계한다.** 세션 중간에
   디렉터리를 옮기면 그쪽 저장소가 사라진다 — 9/08 이벤트 최다였던 `qmeet-dev-ssh`
   (3,000+)가 보고서에서 통째로 빠진 원인. `report/sessions.py`가 이벤트별 cwd로
   고쳤다. 두 파일 이름이 혼동되니 주의.
6. **교육생 폴더 5개는 각각 독립 git 저장소다.** 그래서 구분 매핑이 정확 일치가
   아니라 경로 세그먼트 경계 접두사 매칭이어야 한다. 경계(`/`)를 빼면
   `qmeet/front`가 `qmeet/front_design_prototype`을 흡수해 시안 구분이 사라진다.
7. **`qmeet/front_design_prototype`은 `dev/` 직하가 아니라 `dev/qmeet/` 아래다.**
   경로를 잘못 찍고 "git 아님"을 받으면 재확인할 것 — 이게 9/08 누락의 원인이었다.
8. **`HANDOFF.md` 발췌는 하위 섹션까지 챙겨야 한다.** 헤딩마다 판정을 다시 하면
   `## 한 일` 아래 `### ①②③`이 WANTED에 없어 내용이 통째로 날아간다(126줄 → 18줄).
   그리고 닫히지 않은 ``` 펜스는 제외 섹션을 유출시킨다.
9. **Windows 콘솔이 cp949다.** CLI 진입점은 `sys.stdout.reconfigure(encoding="utf-8")`
   를 먼저 부른다. 파일 읽기는 항상 `encoding="utf-8"` 명시.
10. **엑셀이 파일을 열고 있으면 `~$` 잠금 파일이 생기고 저장이 막힌다.**
    `write_xlsx`/`write_tsv`가 `_` 접두사 파일로 폴백한다. 강제 덮어쓰기 금지.
11. **`git status`는 과거 날짜를 말할 수 없다.** 그래서 `active_repos(rows, is_past)`
    가 미커밋을 당일에만 활동으로 센다. 안 그러면 흩어진 미추적 파일 때문에 과거
    날짜마다 영구 헛경고가 난다.

## Remaining Work

1. ~~머지 또는 PR 결정~~ — **완료(2026-09-09).** `main`에 머지·푸시, 브랜치 삭제.
2. **Ruling 19의 3건 결정** (원장 532행 부근). `--scaffold`는 스펙 「설계 결정 4」를
   건드리므로 진행 시 `docs/superpowers/specs/...-design.md`를 함께 고칠 것.
3. ~~`output/`의 엑셀 두 개가 아직 열려 있다~~ — **해결(2026-09-09).** 닫고 다시
   돌려 정상 파일명으로 나왔고, `_` 접두사 잔재 파일 2개도 지웠다.
4. **모듈 진행률을 사람이 갱신할 것.** `config.yaml`의
   `categories[].progress` — `백엔드 공수산정 85%` / `프론트 공수산정 20%`가 9/07
   시트에서 이월된 값 그대로다. 자동 갱신되지 않는다(설계 결정 3).
5. **9/08 시안 행 문구 확인.** `data/2026-09-08.yaml`의
   `결과 화면 테스트 플랫폼 시안 수정`은 커밋 1건에서 뽑은 판단이다. 다르게 보이면
   YAML 한 항목만 고치면 된다.

## Key File Paths

| 역할 | 경로 |
|---|---|
| 사람이 관리하는 설정 | `config.yaml` |
| 근거 수집 CLI | `collect_evidence.py` |
| 보고서 렌더 CLI | `build_report.py` |
| 경로 경계 술어 `is_under` | `report/config.py` |
| cwd 버그 수정 | `report/sessions.py` |
| 저장소 발견·git 수집 | `report/repos.py` |
| 커버리지 안전망 `coverage_warnings` | `report/daydata.py` |
| 엑셀 6열 양식 렌더 | `report/excel.py` |
| 회귀 기준선 (17행 / 21행) | `tests/test_regression.py` |
| 판정 22건 근거 | `docs/superpowers/decisions/2026-09-08-daily-report-automation-ledger.md` |
| 구 세션 조회 스크립트 (cwd 버그 있음) | `daily_report.py` |

## Verification Commands

```bash
# 전체 테스트 (127 passed 여야 정상)
python -m pytest -q

# 파이프라인 실행 — 무인자 build_report 는 data/ 전체(3일치)를 돈다.
# 아래 경고 4건이 정상이고 전부 기각 근거가 있다. 그 밖의 저장소가 나오면
# 실제 누락이다 — 근거 파일을 읽고 행을 추가할 것.
python collect_evidence.py 2026.9.9
python collect_evidence.py 2026.9.8
python collect_evidence.py 2026.9.7
python build_report.py
#   9/07 → golfzone/admin          (/compact 프롬프트, Gotcha 4)
#   9/08 → daily-report/blank-app  (도구 자체 저장소, Ruling 9)
#   9/09 → daily-report/blank-app  (같은 이유 · 2026-09-09 사용자 결정으로 제외)
#   9/09 → qmeet/qmeet-dev-ssh     (커밋 0·이벤트 0. 활동으로 잡힌 미추적 PNG 9개가
#                                   전부 5~6월 파일이다 — Gotcha 11 의 실제 사례)

# 워크북 검증 (17행 / 21행 / 18행, B1 에 실제 개행)
python -c "import sys; sys.stdout.reconfigure(encoding='utf-8'); \
from openpyxl import load_workbook; \
[print(f, load_workbook(f).active.max_row, repr(load_workbook(f).active.cell(1,2).value)) \
 for f in ('output/일일보고-2026-09-07.xlsx','output/일일보고-2026-09-08.xlsx',
           'output/일일보고-2026-09-09.xlsx')]"

# 경로 경계 술어 (load-bearing — 이게 깨지면 구분이 사라진다)
python -c "from report.config import is_under; \
print(is_under('qmeet/front','qmeet/front_design_prototype'), \
      is_under('qmeet/front','qmeet/front/cypress-example-kitchensink'))"
#   False True 여야 정상
```

## Uncommitted Changes

```
?? daily-report.JPG    ← 이 세션이 만든 파일 아님. 세션 시작 시점부터 untracked.
                          커밋하지 않았다.
```

이 세션의 모든 작업물은 커밋됨 (`a73ef33..6faddd6`, 18커밋 — 핸드오프 커밋 포함). `output/`은 `.gitignore`
대상이고 `data/`는 추적 대상(소스 오브 트루스)이다.
