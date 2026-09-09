# HANDOFF: 일일보고 도구 첫 실사용 — 2026-09-09 보고서 18행 생성

## Goal

대표님께 제출하는 일일보고(스프레드시트 한 장)를 자동 생성한다. 핵심 설계는
**스크립트가 근거를 전수로 모으고, 판단은 사람이 한다**. 스크립트는 행 초안을
만들지 않는다 — 그럴듯한 초안이 있으면 근거를 다시 읽지 않게 되고, 그래서 실제로
작업 6행을 놓친 사고가 이 프로젝트의 출발점이다.

도구 개발 8태스크는 2026-09-08 세션에서 끝났다(맨 아래 아카이브). **이 세션은 그
도구를 개발이 아니라 실사용한 첫 날이다** — 9/09 보고서를 뽑았고, 그 과정에서
드러난 인계 문서 부정확 3갈래를 고쳤다.

## Current Status: Completed

- `main` = `465572e`. **`origin/main` 보다 1커밋 앞서 있다 — 푸시 안 됨**
  (`/handoff-push` 의 main/master 보호 규칙으로 중단)
- 테스트 **127 passed** (`python -m pytest -q`)
- 산출물 `output/일일보고-2026-09-09.xlsx` (18행 × 6열) + `.tsv`

### What Was Done

| 한 일 | 검증 |
|---|---|
| 인계 문서를 실제 저장소 상태와 대조 | 테스트 127·워크북 17/21행·`is_under` 술어 전부 일치 확인 |
| 9/09 근거 수집 | `output/evidence/2026-09-09.md` — 1,026줄 · 저장소 11곳 · 본인 커밋 46건 |
| `data/2026-09-09.yaml` 판단·작성 | 근거 1,026줄 전문을 읽고 18행 |
| 보고서 렌더 | 18행 × 6열 · 진행률 표기·B1 개행 워크북 실측 |
| `output/_일일보고-2026-09-0{7,8}.xlsx` 삭제 | 엑셀 잠금 폴백 잔재 |
| `HANDOFF.md` 3갈래 수정 | 경고 4건을 실측해 검증 블록에 반영 |
| 커밋 `465572e` | `data/2026-09-09.yaml` + `HANDOFF.md` |

**인계 문서를 고친 3갈래** — 낡은 것만 있는 게 아니었다.

1. **낡음** — "머지·PR 안 함"·"엑셀이 열려 있다" 둘 다 이미 해결돼 있었다.
   지우지 않고 취소선으로 남겨 언제 무엇으로 닫혔는지 보이게 했다.
2. **틀림** — 개발 세션 커밋 수 17 → **18**. 핸드오프 커밋 자신이 빠져 있었다.
3. **이번 변경이 거짓으로 만든 것** — `data/` 에 날짜가 셋이 되어 무인자
   `build_report.py` 가 3일치를 돈다. 검증 블록의 "날짜별 경고 1건씩" 이 그대로면
   다음 사람이 4건을 보고 고장으로 읽는다. 실측해 고쳤다.

### 이 세션의 판정 3건

| 대상 | 판정 | 누가 |
|---|---|---|
| 모듈 진행률 (백엔드 85% / 프론트 20%) | **이월값 그대로 간다.** 갱신 안 함 | 사용자 |
| `daily-report/blank-app` | 보고에서 **뺀다** (도구 자체 저장소) | 사용자 |
| `qmeet/qmeet-dev-ssh` | 보고에서 **뺀다** — 오늘 활동이 아니다 (Gotcha 2) | 나 |

### What Was NOT Done

1. **푸시 안 함.** `/handoff-push` 의 main/master 보호 규칙에 걸렸다.
2. **보고 내용 판단 4건 미확정** — 초안대로 커밋돼 있다. Remaining Work 1번.
3. 개발 세션에서 이월된 미결(Ruling 19 3건, 진행률 갱신, 9/08 시안 문구)은 그대로다.

## What Worked

- **근거를 발췌가 아니라 전문으로 읽은 것.** 1,026줄을 다 읽었더니 「인계 문서
  발췌」가 그날 작업이 아닌 경우(Gotcha 3)와 인계 문서의 "미커밋" 이 이미 거짓인
  경우(Gotcha 1)가 둘 다 나왔다. 발췌만 훑었으면 9/08 작업을 9/09 에 중복 보고했다.
- **기각한 경고에 근거를 남긴 것.** 기각 2건의 이유를 `data/2026-09-09.yaml` 주석 ·
  커밋 메시지 · 이 문서의 검증 블록 세 곳에 적었다. 다음에 같은 경고를 보면 다시
  조사하지 않아도 된다.
- **파일을 쓰지 않고 검증한 것.** 엑셀이 열려 있어 렌더를 돌리면 `_` 파일이 또
  생기는 상황에서, `load_day` + `coverage_warnings` 를 직접 불러 경고 4건만 확인했다.

## What Didn't Work / Gotchas

개발 세션의 11건은 아래 아카이브에 그대로 있다. **아래는 이 세션에서 새로 물린 것이다.**

1. **인계 문서의 "미커밋" 은 다음 날 거짓일 수 있다.** `qmeet/front` 인계 문서가
   애니메이션 3파일을 미커밋이라 적었으나 실제로는 **9/08 17:09 `fdbbbc5` 로 커밋**돼
   있었다. 그대로 믿었으면 9/08 보고 항목을 9/09 에 또 적었다.
   → 미커밋 주장은 `git log -1 --format='%ad %s' -- <파일>` 로 확인할 것.
2. **미추적 파일은 수정 시각을 봐야 한다.** `qmeet-dev-ssh` 가 커밋 0·세션 이벤트 0
   인데 활동으로 잡혔다. 활동의 근거였던 미추적 PNG 9개가 **전부 5~6월** 파일이었다.
   개발 세션 Gotcha 11 이 예고한 헛경고의 **첫 실제 사례**다.
   → `ls -la --time-style=+%Y-%m-%d` 로 확인하고, 오래됐으면 행을 만들지 말 것.
3. **근거의 「인계 문서 발췌」는 그날 한 일이 아니다.** `qmeet_ai` 발췌는 법무 질의·
   파기 경로 조사였는데 9/09 세션 프롬프트 6건은 전부 PPT 프리스캔이었다. 발췌는
   저장소의 **현재 상태**지 그날의 작업 기록이 아니다.
   → 그날 일은 **커밋 + 세션 프롬프트**로만 판단하고, 발췌는 맥락으로만 쓸 것.
4. **`data/` 에 날짜를 추가하면 이 문서의 검증 블록이 즉시 거짓이 된다.** 무인자
   `build_report.py` 가 `data/` 전체를 돌기 때문이다. 날짜를 추가할 때마다 아래
   「Verification Commands」의 경고 목록도 같이 고칠 것.
5. **엑셀을 열어둔 채로 검증하려고 렌더를 돌리지 말 것.** `output/~$일일보고-*.xlsx`
   가 있으면 열려 있는 것이고, 돌리면 `_` 접두사 파일이 또 생긴다. 경고만 볼 거면
   `load_day` + `coverage_warnings` 를 직접 부르면 파일을 안 쓴다.
6. **문서 치환 스크립트로 역슬래시 줄 연속(`\`)이 든 블록을 통짜로 매칭하지 말 것.**
   아래 검증 블록의 여러 줄짜리 `python -c` 를 한 덩어리로 잡으려다 0건 매칭으로
   실패했다. 역슬래시가 없는 한 줄(파일 목록)만 앵커로 잡으면 된다.

## Remaining Work

1. **보고 내용 판단 4건 확정.** `data/2026-09-09.yaml` 이 초안대로 커밋돼 있다.
   고칠 것이 있으면 **해당 항목만** 바꾸고 `python build_report.py 2026.9.9` 재실행.
   - 백엔드·프론트 두 행은 **커밋 0건**이다(로컬 기동·시안 확인만). 뺄지 결정.
   - 교육 행이 9/08 의 "5명 전원 전달 완료" 와 겹쳐 보인다. 뺄지 결정.
   - 자동화 「고객사 실행가이드·런북」 80% 는 미커밋 상태를 보고 내가 잡은 값이다.
   - 시안의 참고 이미지·2Pager 커밋(`4c96f2d`, 3.7MB)은 자료 등록이라 행에서 뺐다.
2. **푸시** — `git push origin main`. 이 세션에서 main 보호 규칙으로 중단했다.
3. **다른 저장소 3곳의 9/09 작업물이 미커밋이다** (9/09 근거로 실측).
   한 세션에서 3곳을 건드리면 어느 변경이 어디 것인지 섞이므로 저장소별로 나눌 것.
   - `e2etest/playwright_base` — CI 콘솔 한글 깨짐 수정 + 고객사 문서 3종 (미커밋 11건)
   - `e2etest/qmeet` — `docs/RUNBOOK.md` + 동기화 잔여 (미커밋 11건)
   - `qmeet/qmeet_ai` — PPT 프리스캔 판별 `ppt_extract.py` + 테스트 (미커밋)
4. **Ruling 19의 3건 결정** (개발 세션 이월, 원장 532행 부근). 단일 진입점 `daily.py` /
   `--scaffold` / 사이드카를 `data/` 로 이동. `--scaffold` 는 스펙 「설계 결정 4」를
   직접 건드리므로 진행 시 `docs/superpowers/specs/...-design.md` 를 함께 고칠 것.
5. **모듈 진행률을 사람이 갱신할 것** — `config.yaml` 의 `categories[].progress`.
   자동 갱신되지 않는다(설계 결정 3). 이 세션에서는 사용자 지시로 이월값을 유지했다.
6. **9/08 시안 행 문구 확인** (개발 세션 이월) — `data/2026-09-08.yaml` 의
   `결과 화면 테스트 플랫폼 시안 수정` 은 커밋 1건에서 뽑은 판단이다.

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
| 회귀 기준선 (17행 / 21행 — 9/09 는 손으로 만든 원본이 없어 기준선 없음) | `tests/test_regression.py` |
| 보고서 행 데이터 (소스 오브 트루스) | `data/2026-09-07.yaml` · `2026-09-08.yaml` · `2026-09-09.yaml` |
| 판정 22건 근거 | `docs/superpowers/decisions/2026-09-08-daily-report-automation-ledger.md` |
| 설계 결정 4개와 「한계」 | `docs/superpowers/specs/2026-09-08-daily-report-automation-design.md` |
| 8태스크 구현 계획 | `docs/superpowers/plans/2026-09-08-daily-report-automation.md` |
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
#   9/07 → golfzone/admin          (/compact 프롬프트, 아카이브 Gotcha 4)
#   9/08 → daily-report/blank-app  (도구 자체 저장소, Ruling 9)
#   9/09 → daily-report/blank-app  (같은 이유 · 2026-09-09 사용자 결정으로 제외)
#   9/09 → qmeet/qmeet-dev-ssh     (커밋 0·이벤트 0. 활동으로 잡힌 미추적 PNG 9개가
#                                   전부 5~6월 파일이다 — 위 Gotcha 2)

# 엑셀을 열어둔 상태라면 위 build_report 대신 이것 — 파일을 쓰지 않고 경고만 본다
python -c "import sys; sys.stdout.reconfigure(encoding='utf-8'); sys.path.insert(0,'.'); \
from pathlib import Path; from report.config import load_config; \
from report.daydata import load_day, coverage_warnings; \
from build_report import active_repos_for; c = load_config(Path('config.yaml')); \
[print(p.stem, coverage_warnings(load_day(p, c)[0], active_repos_for(p.stem) or [])) \
 for p in sorted(Path('data').glob('2026-*.yaml'))]"

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
?? daily-report.JPG    ← 세션 작업물 아님. 개발 세션 시작 시점부터 계속 untracked.
```

이 세션의 작업물은 `465572e` 로 전부 커밋됐다(`data/2026-09-09.yaml` + `HANDOFF.md`).
`output/` 은 `.gitignore` 대상이고 `data/` 는 추적 대상(소스 오브 트루스)이다.

⚠️ `output/~$일일보고-2026-09-09.xlsx` 가 있다 — 엑셀이 9/09 워크북을 **열고 있다**는
표시다. 닫기 전에 렌더를 돌리면 `_` 접두사 파일이 또 생긴다.

---

## Previous Handoff (archived) — 2026-09-08 개발 세션

> 도구를 만든 세션의 기록이다. **아래 Gotchas 11건은 전부 아직 유효하다.**
> 그 세션의 「Remaining Work」·「Uncommitted Changes」·「Key File Paths」·
> 「Verification Commands」는 위 본문이 대체했다.

설계·계획·판정 근거는 중복하지 않는다. 아래 문서를 볼 것:

| 문서 | 내용 |
|---|---|
| `docs/superpowers/specs/2026-09-08-daily-report-automation-design.md` | 설계 결정 4개와 「한계」 |
| `docs/superpowers/plans/2026-09-08-daily-report-automation.md` | 8태스크 구현 계획 |
| `docs/superpowers/decisions/2026-09-08-daily-report-automation-ledger.md` | **판정 22건의 발견·이유·틀렸을 때 비용** |
| `README.md` | 사용법·config 관리 항목·한계 |

#### What Was Done

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

#### What Was NOT Done

1. ~~머지·PR 안 함~~ — **2026-09-09 `main`에 머지·푸시하고 브랜치를 지웠다.**
2. **최종 리뷰어 제안 3건 보류** — 스펙을 건드려서 사용자 승인 대기 (원장 Ruling 19):
   단일 진입점 `daily.py` / `--scaffold`(골격 생성 — 「행 초안 금지」 결정을 직접
   건드림) / 사이드카를 추적 대상 `data/`로 이동.
3. **이월 minor 12건** — 원장의 `minor (deferred)` 줄. 최종 리뷰가 6건은 "그대로 둬도
   된다"로 트리아지했고 5건은 수정 웨이브에서 처리했다. 남은 것은 전부 미관·폴리시.
4. **git worktree 이중 계수** — 고치지 않고 스펙 「한계」에 기록 (Ruling 18).

### What Worked

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

### What Didn't Work / Gotchas

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
