# 일일보고 자동화 — 실행 원장 (판정 기록)

이 문서는 `docs/superpowers/plans/2026-09-08-daily-report-automation.md` 를
서브에이전트로 실행하는 동안 남긴 **원본 원장**이다. 정제된 문서가 아니라
스크래치 기록이며, 디스패치 부기와 판정이 섞여 있다. 그대로 남기는 이유는
**판정 22건의 근거와 "틀렸을 때 비용"이 여기에만 있기** 때문이다.

읽는 법 — `**Ruling N:`으로 시작하는 블록이 사람 대신 내린 결정이다. 각 블록은
발견 → 결정 → 이유 → 틀렸을 때 비용 순서다. 되돌리려면 그 비용 문단을 보면 된다.

계획 실행 결과: 8태스크 + 최종 수정 웨이브, 커밋 15건, 테스트 127개.

---

# SDD ledger — plan: docs/superpowers/plans/2026-09-08-daily-report-automation.md

Spec: docs/superpowers/specs/2026-09-08-daily-report-automation-design.md
Branch: claude/claudecode-daily-report-xqj8sp (main 아님 — 격리 확인)
Merge base: a73ef33b06b0b808eaa1da6334fa322c1998184c
Start HEAD: c8abfa641c4479f94313e52b0c12db19fdc03a55

## 사전 충돌 스캔

### 태스크 쌍 — 파일·인터페이스 공유

| 쌍 | 공유 | 생산 → 소비 | 결과 |
|---|---|---|---|
| 1→2 | `report/config.py` | `Config.ignore_prompts` → `load_events(..., ignore_prompts: Sequence[str])` | 맞음. sessions.py 는 Config 를 import 하지 않고 시퀀스만 받는다 |
| 1→3 | `report/config.py` | `Config`, `normalize_repo` → repos.py import | 맞음 |
| 1→6 | `report/config.py` | `PROGRESS_RE`, `Config.category`, `order_index`, `normalize_repo` → daydata.py import | 맞음. PROGRESS_RE 가 T1 모듈 최상위에 있어 재사용 가능 |
| 1→7 | `Config.label` | `label()` → `write_xlsx` 의 B열 | 맞음 |
| 1→8 | `config.yaml` | 구분 9개 → `test_실제_config_가_로딩된다` 가 `len == 9` 단정 | 맞음 (백엔드·프론트·AI서버·시안·인프라·GA4·CRM·자동화·교육 = 9) |
| 2→3 | `SessionEvent` | `(ts, cwd, prompt)` → `discover` 가 `ev.cwd` 사용 | 맞음 |
| 2→5 | `SessionEvent` | 세 필드 → `collect_evidence.py` 가 `ts`·`cwd`·`prompt` 전부 사용 | 맞음 |
| 3→5 | `report/repos.py` | `Commit`·`git_root`·`to_rel`·`discover`·`commits`·`branch`·`uncommitted` → 전부 import | 맞음 |
| 3→5 | `Commit` 필드 | `(sha, time, subject, email)` → render 가 `time`·`sha`·`subject` 사용 | 맞음 |
| 4→5 | `handoff.read` | `read(repo_abs) -> str \| None` → `read_handoff` 별칭 import | 맞음 |
| 5→7 | 근거 사이드카 | T5 가 `output/evidence/2026-09-08.repos.json` → T7 `active_repos_for(path.stem)`, path=`data/2026-09-08.yaml` | 맞음. stem 형식 일치 |
| 6→7 | `report/daydata.py` | `load_day -> (DayReport, list[str])`, `coverage_warnings`, `DayDataError` | 맞음 |
| 6→7 | `Location` | T6 에만 정의, excel.py 가 `from .daydata import` | 맞음 (excel.py 자체 정의 없음) |
| 7→8 | `excel.flatten` | T7 생산 → T8 회귀 테스트가 import | 맞음 |
| 6·7→8 | `data/*.yaml` | T8 이 두 파일 작성 → T6·T7 소비 | 맞음 |
| **1·3·6→8** | **구분↔저장소 매핑** | **config 교육 = `leadwalk_study/2026/second-half-automation-training` vs data = `.../repos` vs 실제 발견 = 학생별 5개 저장소** | **★충돌 — 아래 Ruling 1** |

### 태스크 자체 정합성

| Task | 확인 내용 | 결과 |
|---|---|---|
| 1 | 테스트가 참조하는 `Config`·`ConfigError`·`load_config` 정의됨. `field` import 됨. YAML 단일인용부호가 백슬래시를 리터럴로 보존 | 맞음 |
| 2 | `load_events(DAY, tmp_path)` 위치인자 ↔ 시그니처 `(day, projects_root, ignore_prompts=())`. `test_ignore_prompts_...` 가 `len==2` 단정 ↔ 코드가 prompt=None 이벤트를 남김 | 맞음 |
| 3 | `test_git_아닌_cwd_도...` ↔ `to_rel(root or ev.cwd, ...)`. `plain` 이 `app` 저장소 밖이라 git_root 가 None | 맞음 |
| 4 | `# HANDOFF: ...` 제목이 WANTED 에 안 걸림(keeping=False). `## Current Status:` → "current status" 걸림. 단일 헤딩 시 `latest_section` 이 원문 그대로 반환 ↔ `== text` 단정 | 맞음 |
| 5 | `WEEKDAYS[date(2026,9,8).weekday()]` = "화" ↔ 기대값. "본인 커밋 1건"(BACKEND 1 + E2E 0), "타인 5건 제외"(skipped=5). 출력에 "진행률"·"100%" 문자열 없음 ↔ 행 초안 미생성 단정 | 맞음 |
| 6 | `items: []` → `or []` → falsy → "항목이 없는 구분" 에러. `coverage_warnings` 는 Ruling 1 반영 필요 | Ruling 1 외 맞음 |
| 7 | monkeypatch 가 1회차 save 만 실패시킴 ↔ `wb.save(path)` 후 `wb.save(fallback)`. `len(items) > 1` 조건 ↔ `"B3:B3" not in merged` | 맞음 |
| 8 | 행 수 17·20 ↔ 오늘 손으로 만든 산출물과 일치(검증됨). `.../repos` 폴더 실재 ↔ daydata 폴더 존재 경고 없음 | 커버리지 경고는 Ruling 1 |

### 리뷰 루브릭이 결함으로 볼 만한데 계획이 강제하는 것

없음. 단정 없는 테스트, 논리 블록 그대로 복제 없음.

---

## Rulings (사전)

**Ruling 1: 구분↔저장소 매핑을 경로 세그먼트 경계 접두사 매칭으로 한다.**

발견: 교육생 폴더 5개(`.../repos/automation-study-eunchae` 등)가 각각 독립 git
저장소다(실측 확인). 그래서 `discover` 는 이를 5개 저장소로 잡는데,
`config.yaml` 의 교육 `repos` 는 비git 상위 폴더
`leadwalk_study/2026/second-half-automation-training` 를 가리켜 절대 일치하지
않는다(죽은 매핑). 결과로 ① 근거 커버리지 표에 교육 5줄이 전부 "구분 미지정"
② `coverage_warnings` 가 매일 경고 5건 ③ 계획 Task 8 Step 5 의 "경고 없음"
기대가 깨진다.

결정: `Config.category_for_repo` 와 `coverage_warnings` 를 **경로 세그먼트
경계 접두사 매칭**으로 한다. `repos` 항목이 발견된 저장소의 조상 경로면 그
구분으로 본다. `a/b` 가 `a/bc` 를 흡수하지 않도록 경계는 `/` 로만 인정한다.
정확 일치를 접두사보다 우선한다.

이유: 스펙 「저장소 자동 발견」의 취지(새 저장소가 조용히 사라지지 않게)를
지키면서 상위 폴더로 묶는 자연스러운 표현을 준다. 교육생이 늘어도 config 를
고치지 않는다. 그리고 오늘 손으로 만든 보고서가 교육을 **1행**(`.../repos`,
5명 전원)으로 표기했고 접두사 매칭이 그 결과를 재현한다. 대안 A(학생 저장소
5개를 config·data 에 열거)는 F열이 5줄로 늘어 검증된 산출물과 달라진다.

틀렸을 때 비용: 접두사가 너무 넓게 잡아 무관한 하위 저장소를 같은 구분으로
흡수할 수 있다. 세그먼트 경계 제한으로 완화했고, 잘못 흡수되면 근거 커버리지
표에서 구분이 틀리게 찍혀 눈에 보인다. 되돌리려면 두 함수를 정확 일치로
되돌리고 config 에 저장소를 열거하면 된다.

영향 태스크: Task 1(`category_for_repo` + 테스트), Task 6(`coverage_warnings`
+ 테스트). 각 디스패치에 이 판정을 실어 보낸다.

**Ruling 2: `git log --since/--until` 의 커밋터 날짜 필터를 유지한다.**

발견: `commits()` 는 `--since/--until` 로 범위를 자르고 `%ad`(작성자 날짜)로
시각을 찍는다. git 의 `--since/--until` 은 기본이 커밋터 날짜라 두 축이 다르다.
작성일과 커밋일이 갈리는 커밋은 엉뚱한 날에 잡힐 수 있다.

결정: 그대로 둔다.

이유: 오늘 이 방식으로 뽑은 본인 커밋 36건이 검증된 기준선이다. `%cd` 나
`--author-date-order` 로 바꾸면 그 기준선과 달라지고, Task 8 회귀 테스트가
비교할 대상이 사라진다.

틀렸을 때 비용: 리베이스·체리픽으로 작성일과 커밋일이 벌어진 커밋이 인접한
날 보고서에 잡힌다. 근거 파일에 시각이 찍히므로 사람이 읽을 때 드러난다.

**Ruling 3: 계획의 Interfaces 산문보다 코드 블록이 구속력을 가진다.**

발견: Task 7 Interfaces 는 소비 대상에 `Row`·`Item` 을 적었으나 코드는
`from .daydata import DayReport, Location` 만 한다. Task 5 Interfaces 는
`report.config.Config` 를 적었으나 자체 검토에서 `render()` 의 미사용 인자를
없애며 evidence.py 의 Config import 도 사라졌다.

결정: 코드 블록이 구속력을 가진다. 산문은 서술이다.

틀렸을 때 비용: 없음 — 실행되는 것은 코드다. 리뷰어가 이 불일치를 지적하면
리뷰 루프에서 판정한다(리뷰어에게 미리 무시하라고 지시하지 않는다).

---

## 진행

Task 1: dispatched (sonnet, BASE c8abfa6) — config.yaml 로딩·검증 + pytest 기반.
  Ruling 1 (세그먼트 경계 접두사 매칭)을 디스패치에 실어 보냈다.
Task 1: implementer DONE (commit d9500e8, 15 passed). 리뷰 패키지
  review-c8abfa6..d9500e8.diff 생성, 태스크 리뷰어 디스패치(sonnet).
  구현자 관찰 2건 (수정 대상 아님, 관찰이라 리뷰로 진행):
    - category_for_repo 가 접두사 매칭으로 O(n) 스캔 (n=9). 현 규모에선 무해.
    - 아직 호출자가 없다 → T5(collect_evidence)·T6 이 호출자를 추가할 때
      정확 일치 전제로 쓰지 말 것. 두 디스패치에 이 포인터를 싣는다.
Task 1: 리뷰 결과 Spec ✅ / Task quality Approved. Critical·Important 0건.
Task 1: minor (deferred): tests/test_config.py:153-157 `test_가장_긴_프리픽스가_이긴다`
  가 두 접두사를 같은 구분에 매핑해, 짧은 쪽이 이겨도 단정이 통과한다(판별력 없음).
  구현은 수동 트레이스로 정확함 확인. 최종 전체 리뷰에서 트리아지 대상.
Task 1: ⚠️ 해소 — "뒤 태스크가 category_for_repo 를 정확 일치 전제로 쓰는가".
  계획 전수 확인 결과 호출자는 Task 5 collect_evidence.py 한 곳뿐이고(계획 1681행)
  거기서 접두사 매칭이 의도된 동작이다. Task 6 은 config.category(이름)·
  order_index 만, Task 7 은 label 만 쓴다. 실제 갭 아님.
Task 1: complete (commits c8abfa6..d9500e8, review clean, 1 minor deferred)
Task 2: dispatched (haiku, BASE d9500e8) — sessions.py, 이벤트별 cwd 집계.
  계획에 코드·테스트가 완비돼 전사 작업이라 최저 티어.
Task 2: implementer DONE (commit 11f086a, 9 passed). 실데이터 검증에서
  qmeet-dev-ssh 3,126 이벤트로 1위 — cwd 소실 버그 해소 확인. 우려 0건.
  리뷰 패키지 review-d9500e8..11f086a.diff, 태스크 리뷰어 디스패치(sonnet).
Task 2: 리뷰 결과 Spec ✅ / Task quality Approved. Critical·Important 0건.
Task 2: minor (deferred): _extract_prompt 가 멀티블록 content 를 공백으로 이어
  붙인 뒤 startswith("<") 검사를 하므로, 선행 <system-reminder> 블록 + 진짜
  프롬프트 조합이면 진짜 프롬프트까지 버려진다. **실측으로 영향 0건 확인**:
  2026-09-07·08 사용자 턴 3,541건 중 단일블록 3,077 / 문자열 content 463 /
  멀티블록 1건(해당 패턴 아님), 해당 조합 0건. 이벤트·cwd 집계에는 무영향.
  수정 없이 이월 — 최종 리뷰 트리아지 대상.
Task 2: minor (deferred): _local_tz() 가 주입 불가라 시간대를 고정한 테스트를
  쓰려면 mock 이 필요하다. 폴리시.
Task 2: complete (commits d9500e8..11f086a, review clean, 2 minor deferred)
Task 3: dispatched (sonnet, BASE 11f086a) — repos.py, 저장소 발견 + git 수집.
  Ruling 2(커밋터 날짜 필터 유지)를 디스패치에 실어 보냈다.
Task 3: implementer NEEDS_CONTEXT — 계획 결함 2건을 근본 원인까지 규명해 보고했다.
  전사는 완료(report/repos.py, tests/test_repos.py), 커밋 없음, 3 failed / 12 passed.

**Ruling 4: commits() 를 `--since-as-filter` 로 바꾼다. 픽스처는 그대로 둔다.**
발견: `git log --since` 는 순수 필터가 아니라 이력 순회 중단 최적화다. 범위보다
오래된 커밋을 만나면 그 자리에서 순회를 멈춘다. 브리프 픽스처는 마지막에 생성한
"어제 커밋이다"(하루 전 날짜)가 HEAD 라서, 09-08 질의가 HEAD 에서 즉시 멈추고
아래 깔린 09-08 커밋 3건에 도달하지 못한다.
측정: 실제 저장소 6곳에서 `--since` 와 `--since-as-filter` 결과가 완전히 동일
  (backend2 5/5 · front 12/12 · qmeet_ai 5/5 · qmeet-dev-ssh 11/11 ·
   e2etest/qmeet 8/8 · playwright_base 2/2). 실제 이력은 시간순이라 차이가 없다.
결정: `--since-as-filter` 채택. git 2.49.0 확인. 픽스처는 수정하지 않는다.
이유: ① 측정상 실제 결과가 동일해 검증된 기준선에 위험이 없다 ② 리베이스·
체리픽으로 날짜 순서가 뒤집힌 이력에서 커밋이 조용히 사라지는 실패 모드를
제거한다 — 조용한 누락은 이 프로젝트가 막으려는 실패 그 자체다(cwd 소실,
미커밋 누락과 같은 부류) ③ 픽스처를 그대로 두면 "범위 밖 HEAD 뒤에 숨은 커밋을
찾아내는가"를 검증하는 회귀 테스트가 된다. 시간순으로 재배열하면 그 검증력을 잃는다.
틀렸을 때 비용: git < 2.34 는 플래그를 거부 → `_git` 이 None → 조용한 0건.
완화로 `_git` 이 "unknown option" 을 구분해 시끄럽게 실패하도록 한다.

**Ruling 5: `_git()` 에 `-c core.quotepath=false` 를 넣는다.**
발견: `git status --porcelain` 이 비ASCII 파일명을 8진수로 이스케이프한다
  (`?? "\355\225\234\352\270\200\355\214\214\354\235\274.txt"`). core.quotepath
  기본값이 true 라서다.
측정: 임시 저장소에서 재현·확인. 플래그를 주면 한글로 나온다. 이 세션에서도
  실제로 `git status -s` 가 일일보고 파일명을 8진수로 뱉는 것을 봤다.
결정: 픽스처가 아니라 코드에서 고친다.
이유: 근거 파일의 실제 출력도 읽을 수 있게 된다. 픽스처만 고치면 실제 출력은
계속 깨진 채 남는다.
틀렸을 때 비용: 사실상 없음. quotepath=false 는 출력 표기만 바꾼다.

**Ruling 6: Task 3 테스트 수는 15가 맞다.** 계획의 16은 오기.
  전체 합계 81 → 80.

관찰(판정 아님): e2etest/qmeet 의 2026-09-08 본인 커밋이 2건 → 8건으로 늘었다.
  세션 중 누군가 미커밋 작업을 커밋한 것으로 보인다. Task 8 회귀 테스트는
  손으로 쓴 행 수(17·20)를 비교하므로 영향 없다.
Task 3: implementer DONE (commit 412fed5, 16 passed, 전체 40 passed).
  Ruling 4·5·6 반영. Step 5 실검증 `본인 5 / 타인 제외 5 / feature/orchestrator`
  — 기대 4와 다르나 세션 중 추가된 실제 커밋(19:45 c9622d9)으로 확인, 코드 영향 아님.
  구현자 forward 노트: `--since` 구 기준선이 조용히 커밋을 떨어뜨렸을 가능성이
  있으니 Task 8 회귀 기준선 검증 때 재확인할 것. → Task 8 디스패치에 싣는다.
  리뷰 패키지 review-11f086a..412fed5.diff, 태스크 리뷰어 디스패치(sonnet).
Task 3: 리뷰 결과 Spec ✅ / Task quality Approved. Critical·Important 0건.
  리뷰어가 세 판정을 코드 인스펙션 + 실제 git 실행으로 독립 검증했다
  (unknown-option 은 raise / not-a-git-repository 는 조용히 None — discover 경로 안전).
Task 3: minor (deferred): repos.py:44-45 RuntimeError 메시지가 내부 스캐폴딩
  (`-c core.quotepath=false`, `-C <repo>`)까지 담는다. 디버깅엔 오히려 유용, 무해.
Task 3: ⚠️ 해소 — c9622d9 실재·시각 독립 확인: 작성·커밋 모두 2026-09-08 19:45,
  klyhja@l-walk.com. 이 세션 시작(18:31) 이후다. 구현자 판단 맞음, 코드 영향 아님.
  관찰: 세션 중에도 qmeet_ai 에 커밋이 들어온다. data/*.yaml 은 19:00 무렵 수집한
  근거 기준 스냅샷이며 그대로 유효하다.
Task 3: complete (commits 11f086a..412fed5, review clean, 1 minor deferred)
Task 4: dispatched (haiku, BASE 412fed5) — handoff.py, 인계 문서 헤딩 발췌.
  순수 문자열 처리 + 계획에 코드·테스트 완비 → 최저 티어.
Task 4: implementer DONE (commit bcabba5, 9 passed). 실검증 backend2 2416→18줄,
  e2etest/qmeet 224→70줄. **컨트롤러가 18줄을 의심해 발췌 내용을 직접 확인, 결함 발견.**

**Ruling 7: select_headings 를 "섹션 + 하위 섹션" 의미로 고친다.**
발견(실측): backend2 발췌에서 `## 한 일 — 세 덩이` 가 **내용 0줄의 빈 헤딩**으로만
남았다. select_headings 가 모든 헤딩 줄에서 keeping 을 재판정하기 때문에,
`## 한 일`(WANTED)이 켜도 바로 아래 `### ① …` `### ② …` `### ③ …` 의 제목이
WANTED 에 없어 즉시 꺼진다. 최신 섹션 126줄 중 발췌가 18줄뿐인 이유가 이것이다.
스펙은 `한 일`/`What Was Done` 을 반드시 싣도록 요구하며(작업 항목·완료 여부),
오늘 보고서 행을 쓸 때 실제로 읽은 자료다. 핵심 산출물이 훼손된다.
계획 테스트가 못 잡은 이유: 테스트 DOC 과 e2etest/qmeet 은 헤딩 깊이가 모두
같아서 하위 섹션 케이스를 건드리지 않는다.
결정: keeping 을 켠 헤딩의 깊이를 기억한다. keeping 중에 ① 더 깊은 헤딩은
하위 섹션이므로 그대로 싣고 ② 같거나 얕은 헤딩에서만 WANTED 재판정한다.
아울러 ``` 코드펜스 안에서는 헤딩 판정을 하지 않는다 — 펜스 안의 `# 주석` 이
헤딩으로 오인돼 섹션이 조용히 잘리는 것을 막는다(기존 코드도 같은 결함).
이유: 조용한 내용 누락은 이 프로젝트가 막으려는 실패 자체다(cwd 소실, 미커밋
누락, 커밋 walk 절단과 같은 부류). 네 번째 사례다.
틀렸을 때 비용: 깊이 규칙이 너무 관대해 WANTED 섹션 아래 불필요한 하위 섹션까지
실릴 수 있다 — 근거 파일이 길어질 뿐 내용이 틀리지는 않는다. 되돌리기 쉽다.
Task 4: fix round 1/5 dispatched (원 구현자 재개) — Ruling 7 적용.
Task 4: fix round 1/5 완료 (commit 7c9c1dc, 11 passed). 컨트롤러 독립 검증:
  backend2 발췌 18→60줄, ### ①②③ 가 내용과 함께 살아남. e2etest/qmeet 70→81,
  front(최신 212줄) → 115줄로 ### 1~4 하위 섹션 전부 실림. Ruling 7 해소 확인.
  리뷰 패키지 review-412fed5..7c9c1dc.diff (2 commits), 태스크 리뷰어 디스패치(sonnet).
  리뷰어에게 신규 테스트 2개의 "판별력"(수정을 되돌리면 실제로 실패하는지)을
  판정하도록 요구했다.
Task 4: 리뷰 결과 Spec ✅ / Task quality Approved, 그러나 **Important 1건** —
  Approved 판정과 무관하게 수정 루프를 트리거한다(스킬 규칙).
  리뷰어가 신규 테스트 2개의 판별력을 수동 트레이스로 검증해 "둘 다 판별력 있음"
  판정. Task 1 의 판별력 없는 테스트 문제를 반복하지 않았다.

**Ruling 8: 닫히지 않은 펜스는 "마지막 짝 없는 여는 표시를 무시"로 처리한다.**
발견(컨트롤러 재현): kept 섹션 안에서 펜스가 열리고 닫히지 않으면 in_fence 가
끝까지 True 로 남아 헤딩 검출이 죽고, 뒤따르는 제외 대상 섹션이 그대로 실린다.
  입력  "## What Was Done\n\n```\ncode\n\n## Verification Commands\n\npytest -q\n"
  출력  '## What Was Done\n\n```\ncode\n\n## Verification Commands\n\npytest -q'
  → 'Verification Commands' 유출 True / 'pytest -q' 유출 True. 모듈의 핵심 보증
  (검증 명령·함정은 반드시 버린다)이 깨진다.
리뷰어 제안(깊이 1 헤딩에서 펜스 강제 종료)은 **채택하지 않는다**: latest_section
이 이미 두 번째 `# HANDOFF` 에서 자르므로 한 섹션 안의 깊이 1 `# ` 줄은 사실상
bash 주석이다. 그 제안은 펜스를 거짓 종료시켜 Ruling 7 의 수정 2가 막으려던
버그를 되살린다.
결정: 본 루프 전에 펜스 표시 줄을 미리 스캔한다. 개수가 홀수면 **마지막 표시를
토글 대상에서 제외**한다. 닫히지 않은 펜스는 오타이고, 짝 없는 여는 표시를
무시하면 섹션 경계가 보존되며 거짓 종료 위험이 0이다.
이유: 조용한 누출도 조용한 누락과 같은 등급의 실패다. 다섯 번째 사례.
틀렸을 때 비용: 짝 없는 ``` 한 줄이 kept 섹션 안에 리터럴 텍스트로 남는다 —
근거 파일에 백틱 세 개가 보일 뿐 내용이 틀리지 않는다.
아울러 리뷰어 minor #2(제외 섹션 펜스 안의 WANTED 처럼 보이는 헤딩) 테스트를
같이 넣는다 — 같은 코드 경로를 지키는 테스트라 이 라운드 범위로 정당하다.
컨트롤러 재현으로 현 동작은 이미 정상 확인(빈 출력).
Task 4: minor (deferred): handoff.py 의 `if keeping: out.append(line)` 4회 반복.
  각 지점의 술어가 달라 실제 DRY 위반은 아니며 순수 미관. 최종 리뷰 트리아지 대상.
Task 4: fix round 2/5 dispatched (원 구현자 재개) — Ruling 8 적용.
Task 4: fix round 2/5 완료 (commit d307bd3, 13 passed). 컨트롤러 독립 검증 3케이스
  전부 통과: ① 닫히지 않은 펜스 → Verification Commands·pytest -q 유출 없음, code 보존
  ② dropped 섹션 펜스 안 WANTED 유사 헤딩 → 빈 출력 ③ 균형 펜스 안 가짜 헤딩 →
  수정1 회귀 없음(still inside 보존, bad 제외). 실문서 60/81/115 그대로.
  구현자 revert 체크로 테스트 판별력 확인 보고.
  범위 한정 재리뷰 디스패치(haiku, review-7c9c1dc..d307bd3.diff).
  재리뷰어에게 특정 리스크 지목: 사전 스캔과 본 루프가 "펜스 표시" 판정 술어를
  다르게 쓰면 인덱스가 어긋나 잘못된 줄에서 토글된다.
Task 4: fix round 2/5 재리뷰 결과 — 3 findings 전부 ADDRESSED, 신규 breakage 없음.
  지목 리스크 해소 확인: 사전 스캔과 본 루프가 동일 술어
  `line.strip().startswith("```")` 사용 → 인덱스 어긋남 없음.
  거부된 깊이-1 가드는 구현되지 않았음(확인). Out-of-scope 관찰 0건.
Task 4: complete (commits 412fed5..d307bd3, 3 commits, review clean, 1 minor deferred)
Task 5: dispatched (sonnet, BASE d307bd3) — evidence.py + collect_evidence.py CLI.
  멀티파일 통합 태스크라 표준 티어. Ruling 1(접두사 매칭)의 유일한 호출자이며,
  Ruling 3(산문보다 코드 블록이 구속력)을 디스패치에 실었다.
Task 5: implementer DONE (commit 0e3ca70, 13 passed / 전체 66 passed).
  근거 파일 878줄, 저장소 14곳 발견. 접두사 매칭 실측 검증:
    - 교육생 5곳 → `교육` 구분으로 정확히 분류 (Ruling 1 목적 달성)
    - `qmeet/front/cypress-example-kitchensink` → `프론트 공수산정` 으로 흡수
    - `qmeet/front_design_prototype` → `시안` (경계 규칙 덕에 `qmeet/front` 에
      흡수되지 않음 — a/b vs a/bc 테스트가 실제로 값을 했다)
  `진행률` 1회 등장은 실제 커밋 제목 안(bcabba5) — 생성된 진행률 칸이 아니다. 정상.

**★ 자동화가 컨트롤러의 수작업 보고서 누락을 첫 실행에서 잡아냈다.**
`qmeet/front_design_prototype`(시안)에 2026-09-08 커밋 b1a909a 12:46
`feat(design): 결과 화면 02 테스트 플랫폼 — 체크박스 제거, 12항목 전부 개수 스테퍼`
(HTML 2파일, 192+/137-)가 있는데 손으로 만든 9/08 엑셀에 시안 행이 없다.
근본 원인: 첫 커밋 조사에서 경로를 `dev/front_design_prototype` 으로 찍어
"git 아님" 을 받고 재확인하지 않았다. 실제 위치는 `dev/qmeet/front_design_prototype`.
9/07 보고서에 시안이 있는 이유는 두 번째 조사에서 찾았기 때문이다.

**Ruling 9: `daily-report/blank-app` 은 config 에 등록하지 않는다.**
발견: 도구 자체 저장소가 dev_root 아래 있어 자동 발견된다(9 커밋 · 미커밋 4 ·
2,144 이벤트). 커버리지 표에 "구분 미지정" 으로 뜬다.
결정: 그대로 둔다. Task 8 의 기대를 "경고 없음" → "daily-report/blank-app 1건만"
으로 바꾼다. 그 경고는 안전망이 작동하는 증거다.
이유: `repos` 는 화이트리스트가 아니라 매핑이며, 미등록 저장소가 구분 미지정으로
드러나는 것이 설계된 안전 동작이다. 구분 이름을 새로 만들면 사용자 조직 분류에
없는 이름을 제가 정하는 셈이다(기존 시트에 해당 구분 없음). `ignore_repos` 설정을
새로 만드는 것은 오늘만의 조건에 영구 기계장치를 붙이는 YAGNI 위반 — 도구 개발이
끝나면 blank-app 에 매일 커밋할 일이 없다.
틀렸을 때 비용: 도구를 손대는 날마다 예상된 경고 1줄. 나중에 config 한 줄로 해결.

**Ruling 10: `data/2026-09-08.yaml` 에 시안 행을 넣는다. 회귀 기준선 20 → 21행.**
결정: 시안 | 결과 화면 테스트 플랫폼 시안 수정 | 100% |
      비고 "체크박스 제거 → 12항목 개수 스테퍼" · 위치 qmeet/front_design_prototype [main]
미커밋 18건은 세지 않는다 — 전부 미추적 이미지이고, front/HANDOFF.md 가
"시안 저장소엔 미추적 이미지가 여러 개 있으니 git add -A 금지" 라고 경고한 그 파일들이다.
9/08 작업이 아니다.
이유: 손으로 만든 기준선이 틀렸고 자동화가 그것을 증명했다. 틀린 기준선을 테스트
보호를 위해 동결하는 것은 거꾸로다. 회귀 테스트의 목적은 렌더링 파이프라인 보호이며
21행 기준선이 그 목적을 똑같이 수행한다.
틀렸을 때 비용: 행 문구가 커밋 1건에서 뽑은 제 판단이다. 사용자가 다르게 보면
YAML 한 항목만 고치면 된다.
Task 5: 리뷰 결과 Spec ✅ / Task quality Approved. Critical·Important 0건.
  리뷰어가 지목 리스크 전부(활동 판정·cwd 접기·과거 날짜 표기·사이드카 인코딩·
  모듈 경계·금지 파일·행 초안 불변식) 독립 확인.
Task 5: minor (deferred): collect_evidence.py:52-55 가 discover() 가 이미 한
  git_root 해석을 distinct cwd 당 한 번 더 한다. 규모상 무해, repos.py 를
  건드리지 않으려면 불가피.
Task 5: minor (deferred): collect_evidence.py:98 의 unknown 경고 활동 판정이
  `r.uncommitted` 를 빼서 evidence._has_activity 와 정의가 다르다. 현 발견
  메커니즘에서는 무해(미분류 저장소는 세션 cwd 로만 진입)하나 잠재 불일치.
Task 5: complete (commits d307bd3..0e3ca70, review clean, 2 minor deferred)

**Ruling 11: 경로 세그먼트 경계 술어를 config.py 모듈 최상위로 뽑는다.**
발견: 경계 규칙 `q == p or q.startswith(p + "/")` 이 config.py 의
category_for_repo 안에 인라인으로만 있다. Task 6 의 coverage_warnings 가 같은
규칙을 필요로 하므로 그대로 두면 사본이 둘이 된다.
결정: `is_under(parent, child) -> bool` 을 config.py 모듈 최상위에 추가하고
category_for_repo 가 그것을 쓰게 한다. Task 6 은 그것을 import 한다.
이유: 이 경계 규칙이 Ruling 1 의 load-bearing 불변식이다. 두 사본이 어긋나면
`qmeet/front_design_prototype` 이 `qmeet/front` 로 잘못 흡수되는 바로 그 경로가
열린다. 정의 하나, 테스트 표면 하나로 둔다. 리뷰 루브릭이 "논리 블록의 그대로
복제"를 Important 로 보는 것과도 맞는다.
틀렸을 때 비용: 사적 세부의 한 줄 리팩터. config.py 기존 테스트 15개가 그대로
통과해야 하며, 통과하지 않으면 잘못한 것이다.
Task 6: dispatched (sonnet, BASE 0e3ca70) — daydata.py + Ruling 1 후반(커버리지
  접두사 흡수) + Ruling 11(is_under 추출).
Task 6: implementer DONE (commit efaec1a). test_daydata 19 / test_config 19
  (원본 15개 무수정 + is_under 신규 4) / 전체 89 passed.
  컨트롤러 끝단 독립 검증:
    is_under 경계 7케이스 전부 통과 (a/b↔a/b·a/b/c·a/bc·a, qmeet/front↔
    front_design_prototype=False·front/cypress-example-kitchensink=True, 백슬래시 정규화)
    실제 사이드카(활동 14곳) + 부모 경로 8곳 참조 → **경고 정확히 1건**
    (daily-report/blank-app). Ruling 9 예측대로이고 헛경고 6건 소멸. Ruling 1 완결.
  구현자 forward 노트: 커버리지 흡수는 day YAML 이 부모 경로를 참조할 때만
  작동한다 — 형제 저장소를 낱개로 열거하면 6건 노이즈가 돌아온다. → Task 8 에 싣는다.
  리뷰 패키지 review-0e3ca70..efaec1a.diff, 태스크 리뷰어 디스패치(sonnet).
  리뷰어에게 지목: category_for_repo 의 longest-match-wins 보존 여부, 원본 15개
  테스트가 리팩터에 맞춰 조용히 수정되지 않았는지, 커버리지 테스트 4개의 판별력.
Task 6: 리뷰 결과 Spec ✅ / Task quality Approved. Critical·Important 0건.
  리뷰어가 지목 3건 전부 독립 확인: ① category_for_repo 의 longest-match-wins 보존
  (_by_repo 키가 이미 정규화돼 is_under 의 재정규화가 무해함을 추적) ② 원본 15개
  테스트 무수정(import 한 줄 추가 + 신규 테스트 말미 추가뿐) ③ 커버리지 테스트
  판별력 있음 — 형제 경로 테스트가 plain membership 되돌림과 경계 없는 startswith
  양쪽에서 실패한다.
Task 6: ⚠️ 해소 — "locations 도 default_location 도 없는" 분기 무테스트.
  컨트롤러 실행 확인: DayDataError 로 파일·구분·작업명을 담아 정상 예외 발생
  ("2026-09-08.yaml / 자동화 / 위치가 아예 없는 항목: locations 도 default_location
  도 없다"), default 폴백도 정상. 결함이 아니라 커버리지 공백. 실제 갭 아님.
Task 6: minor (deferred): config.py:78 이 루프마다 이미 정규화된 p 를 재정규화한다. 무해.
Task 6: minor (deferred): daydata.py:193-196 위치 부재 분기에 테스트가 없다
  (브리프에도 없던 선재 공백). 동작은 위에서 확인됨.
Task 6: complete (commits 0e3ca70..efaec1a, review clean, 2 minor deferred)
Task 7: dispatched (sonnet, BASE efaec1a) — excel.py 이관 + build_report.py 전면 교체.
Task 7: implementer DONE (commit 3bcfd47, 9 passed / 전체 98 passed).
  구현자가 B열 라벨 형식 변화를 스스로 신고했다 — 좋은 판단.

**Ruling 12: 구분에 선택 필드 `display` 를 추가해 두 줄 표기를 보존한다.**
발견: config.label() 이 `'백엔드 공수산정(85%)'` (한 줄)를 낸다. 검증된 엑셀과
사용자 원본 시트는 `'백엔드\n공수산정(85%)'` (두 줄 — 구분 칸에 "백엔드" 아래
"공수산정(85%)")이다. 사용자가 스크린샷을 주며 "해당 스샷참고 후 작성"이라고
명시했으므로 양식 충실도가 요구사항이다.
줄바꿈 위치는 name 에서 유도할 수 없다(의미적 구분: 담당 영역 / 모듈). 그래서
`name` 은 매칭용, `display` 는 표기용으로 분리한다.
결정: Category 에 선택 필드 `display` 추가. `label()` 은 `display or name` 을 쓰고
progress 가 있으면 `(NN%)` 를 붙인다. config.yaml 의 공수산정 3개 구분에
`display: "백엔드\n공수산정"` 식으로 넣는다. 나머지 구분은 display 없음 → name 그대로.
**부수 필수 사항**: flatten() 이 TSV 용으로 모든 필드의 개행을 공백으로 눌러야 한다.
현재는 F열만 누른다. 두 줄 라벨이 들어가면 TSV 의 "한 행 = 한 줄" 불변식이 깨지고
기존 테스트 `test_TSV_를_탭으로_쓴다` 의 `"\n" not in lines[0]` 단정도 깨진다.
이유: 사용자 조직의 확립된 시트 양식이고, 명시적 요구였다. wrap_text 가 어딘가에서
접어주긴 하지만 접히는 위치가 사용자 양식(담당 영역 / 모듈)과 다르다.
틀렸을 때 비용: config.yaml 에 선택 필드 하나가 늘어난다. display 를 지우면
한 줄로 돌아간다. Task 1 의 테스트 19개는 display 를 안 쓰므로 전부 그대로 통과해야
하며, 통과하지 않으면 잘못한 것이다.
Task 7: fix round 1/5 dispatched (원 구현자 재개) — Ruling 12 적용.
Task 7: fix round 1/5 완료 (commit e93a493). test_excel 11 / test_config 20
  (원본 19 무수정 + 신규 1) / 전체 101 passed.
  컨트롤러 독립 검증: label() 9개 구분 전부 검증된 엑셀 문자열과 정확히 일치
  ('백엔드\n공수산정(85%)' · '프론트\n공수산정(20%)' · 'AI 서버\n공수산정' ·
   시안·인프라·GA4·CRM·자동화·교육은 이름 그대로). Ruling 12 해소 확인.
  구현자가 TSV 붕괴 테스트의 판별력을 revert 체크로 확인 보고.
  리뷰 패키지 review-efaec1a..e93a493.diff (2 commits), 태스크 리뷰어 디스패치(sonnet).
  리뷰어에게 지목: 렌더 시점 git 조회 없음 · PermissionError 폴백 생존 ·
  행 높이 규칙이 F열 개행만 세는지(B열 두 줄 라벨이 들어온 뒤 다른 필드까지 세면
  높이가 잘못 부풀어 오른다) · B열 병합이 항목 2개 이상일 때만.
Task 7: 리뷰 결과 Spec ✅ / Task quality Approved. Critical·Important 0건.
  리뷰어가 렌더링 상수 8개를 하나씩 대조 확인. 지목한 새 위험도 해소 확인:
  행 높이가 `ws.cell(i, 6)` 로 F열만 세므로 B열 두 줄 라벨이 높이에 영향 없음.
  **리뷰어가 구현자 보고서의 허위 진술을 잡았다** — "여섯 필드 전부에 _flatten_line
  적용" 이라 했으나 실제는 5/6(date 누락). "보고서를 신뢰하지 말라" 지시가 값을 했다.
Task 7: minor (deferred): excel.py:60 flatten() 의 date 필드가 _flatten_line 을
  거치지 않는다(5/6). DayReport.date 는 "2026.9.08" 형태라 개행이 들어갈 일이 없어
  실질 위험 없음. 다만 "모든 필드" 요구에 대한 문자적 미달 + 보고서 과장.
Task 7: ⚠️ 해소 — daydata.py:142 가 config.order_index 로 정렬, :54 가 YAML 의
  branch 를 읽는다. daydata.py·excel.py 모두 subprocess/git import 0건 →
  나중에 재렌더해도 그날의 브랜치가 찍힌다. 실제 갭 아님.
Task 7: complete (commits efaec1a..e93a493, 2 commits, review clean, 1 minor deferred)
Task 8: dispatched (sonnet, BASE e93a493) — data/*.yaml 이관 + 회귀 테스트.
  Ruling 9·10 + Task 6·3 forward 노트를 디스패치에 실었다.
Task 8: implementer NEEDS_CONTEXT — 브리프 test_regression.py 212행의 stale 단정을
  파일 원시 바이트까지 확인해 신고했다(마크다운 렌더 artifact 아님을 배제). 정확한 지적.

**Ruling 13: 브리프의 label 단정을 두 줄 형태로 정정한다.**
발견: 브리프는 `config.label("백엔드 공수산정") == "백엔드 공수산정(85%)"` (공백, 한 줄)
을 단정하지만 실제 값은 `'백엔드\n공수산정(85%)'` 이다.
원인: **내 Ruling 12 가 만든 모순이다.** 계획의 Task 8 테스트는 Ruling 12(구분에
display 필드 추가) 이전에 쓰였다. config.yaml 은 수정 금지 목록에 있으므로 테스트를
고치는 것이 유일하게 옳은 방향이다.
결정: 단정을 `"백엔드\n공수산정(85%)"` 로 고친다.
이유: 두 줄 형태가 검증된 기준선이자 사용자 원본 시트의 형태다. 이 단정은 이제
Ruling 12 의 회귀 감시 역할까지 한다. 테스트를 구현에 맞춰 굽히는 것이 아니라,
계획의 기대가 나중에 내린 판정에 대해 stale 해진 것을 정정하는 것이다.
전수 확인: stale 단정은 212행 하나뿐. 나머지(자동화 / TC 입력 양식 제정)는 day YAML
데이터 값이라 무영향. len(categories) == 9 도 유효.
틀렸을 때 비용: 없음 — 두 줄 형태가 검증된 값이다.
Task 8: implementer 재차 정지 — 지시대로 9/07 경고 2건을 보고했다. 정확한 판단이며
  그 뒤에 진짜 설계 결함이 있었다.

**Ruling 14: active_repos 의 활동 판정을 좁히고 is_past 를 받게 한다.**
발견(실측):
  9/07 `qmeet/qmeet-dev-ssh` — 커밋 0 · 세션 이벤트 0 · 미커밋 9(전부 미추적 이미지
    + .playwright-mcp/). 9/07 증거가 전무한데 **현재 시점** 미추적 파일 때문에만
    active_repos 에 든다. git status 는 과거 날짜를 말할 수 없다.
  9/07 `golfzone/admin` — 커밋 0 · 미커밋 0 · 이벤트 14, 살아남은 프롬프트 0
    (유일한 프롬프트가 /compact 로 ignore_prompts 에 걸린다). 미등록 저장소.
방치하면 과거 날짜 보고서마다 흩어진 미추적 파일로 영구 헛경고가 난다 — Ruling 1·9
에서 반대한 경고 피로 그 자체다.
결정: `active_repos(rows, is_past)` 로 바꾸고, 저장소가 활동했다고 보는 조건을
  ① 커밋이 있다  ② 살아남은 프롬프트가 있다(그날 사람이 뭔가 요청했다)
  ③ 미커밋이 있고 is_past 가 아니다
로 한다. **원시 이벤트 수 단독은 제외한다** — 세션이 지나간 흔적(resume·/compact)일
뿐 사람의 요청이 없으면 보고할 것이 없다.
렌더링용 `_has_activity`(섹션을 낼지 여부)는 그대로 둔다. 목적이 둘이므로 술어도
둘이며, 차이를 의도적으로 명시한다 — Task 5 리뷰어가 지적한 "두 활동 정의 불일치"
minor 도 이로써 해소된다.
검증(적용 후 기대): 9/07 경고 0건, 9/08 경고 1건(daily-report/blank-app).
이 수정은 report/evidence.py 와 collect_evidence.py 를 건드린다 — 완료된 태스크의
파일이지만 컨트롤러 권한으로 금지 목록을 이 건에 한해 해제한다.
틀렸을 때 비용: 커밋도 프롬프트도 없이 미커밋만 남긴 당일 작업은 여전히 잡히고,
과거 날짜에서만 빠진다. 프롬프트 없이 이벤트만 남은 저장소가 실제 작업이었다면
경고를 놓친다 — 다만 그런 저장소는 근거 커버리지 표에 여전히 표시된다.

**Ruling 15: `_` 접두사 폴백은 정상 동작이다. 열린 파일을 강제하지 않는다.**
발견: output/ 에 `~$일일보고-2026-09-07.xlsx`·`~$일일보고-2026-09-08.xlsx` 엑셀 잠금
파일이 있다 — 사용자가 두 워크북을 열어둔 상태다.
결정: 폴백이 설계대로 작동한 것이다. 삭제·강제 덮어쓰기 하지 않는다. 검증은 실제로
쓰인 `_` 접두사 파일을 대상으로 한다. 19:11 자 손으로 만든 xlsx 도 남긴다 —
사용자가 지금 그걸 보고 있다.
틀렸을 때 비용: 없음. 사용자가 엑셀을 닫고 다시 돌리면 정상 파일명으로 쓰인다.
Task 8: fix round 1/5 dispatched (원 구현자 재개) — Ruling 14·15.
Task 8: implementer 3차 정지 — **내 Ruling 14 의 사실 주장 오류를 잡았다.** 정확하다.
  내가 "/compact 는 ignore_prompts 에 걸린다"고 썼으나 config.yaml 의 ignore_prompts
  에는 보안 리뷰·세션 이어받기 두 패턴뿐이고 /compact 는 걸러지지 않는다. 확인함.
  9/07 golfzone/admin 의 프롬프트 "09:45 · /compact" 는 실제로 살아남는다.

**Ruling 16: golfzone/admin 경고를 그대로 둔다. 슬래시 명령 일괄 제외는 하지 않는다.**
발견: 구현자가 제시한 대안 ①(active_repos 안에서 bare /-명령을 작업 요청으로 보지
않는다)을 검토했으나 **채택하지 않는다.** 오늘 세션 기록의 슬래시 명령 분포를
실측하니 `/code-review` 2건 — 명백한 작업 요청이다. `/handoff`·`/humanize-korean`
등도 실제 산출물을 만든다. 슬래시 명령 일괄 제외는 진짜 작업 요청을 억제해
**조용한 누락**을 만든다. 이 프로젝트가 막으려는 실패 그 자체다.
결정: 경고를 그대로 둔다. 기대치를 정정한다 —
  9/07: 경고 1건 (golfzone/admin) · 9/08: 경고 1건 (daily-report/blank-app).
이유: 사람이 9/07 에 golfzone/admin 에서 /compact 를 실제로 쳤다. "활동이 있는데
표에 없다"는 문자적으로 참이다. 사람이 경고를 보고 근거를 열면 커밋 0·프롬프트
/compact 뿐임이 바로 보이고 2초 만에 기각한다. 억제하는 쪽의 비용(진짜 작업을
조용히 놓침)이 남기는 쪽의 비용(기각 가능한 경고 1줄)보다 훨씬 크다.
Ruling 14 는 유효하다 — qmeet-dev-ssh(미커밋 only, 과거 날짜) 경고는 정확히
사라졌다. 잘못된 것은 내가 덧붙인 golfzone 기대치의 전제뿐이다.
틀렸을 때 비용: 과거 날짜 보고서에 기각 가능한 경고가 1줄 남는다.
Task 8: implementer DONE (commit 9a01e62). test_regression 7 / test_evidence 17
  (원본 13 + 신규 4) / 전체 112 passed.
  컨트롤러 끝단 독립 검증:
    data/2026-09-07.yaml · data/2026-09-08.yaml 추적됨(커밋)
    9/07 → 17행 · 경고 1건(golfzone/admin)
    9/08 → 21행 · 경고 1건(daily-report/blank-app)  ← Ruling 10 반영
    B1 = '백엔드\n공수산정(85%)' (실제 개행) — 검증된 양식 그대로
    구분 순서 양쪽 모두 config.yaml 순서 준수. 9/08 에 시안 포함 확인.
  리뷰 패키지 review-e93a493..9a01e62.diff, 태스크 리뷰어 디스패치(sonnet).
  리뷰어에게 지목: YAML 이 부모 경로를 쓰는지 · active_repos 새 술어가 Ruling A 와
  정확히 일치하는지(event_count 단독 불가) · 기존 test_evidence 호출부가 시그니처에
  맞춰 갱신되며 단정은 안 바뀌었는지 · 신규 과거날짜 테스트의 판별력.
Task 8: 리뷰 결과 Spec ✅ / Task quality Approved. Critical·Important 0건, ⚠️ 0건.
  리뷰어가 구현자 주장을 실제 git 이력·파일시스템·소스로 전수 독립 검증했다
  (b1a909a 커밋 stat 192+/137-, 미커밋 18건, repo 경로 10개 실재, 행 수 산술 21=2+5+4+1+1+7+1).
  기존 test_evidence 호출부는 is_past=False 만 추가되고 단정은 byte-for-byte 불변 확인.
  신규 테스트 4개 전부 판별력 있음 판정.
Task 8: minor (deferred): tests/test_evidence.py:120 이 실제로 논의된 golfzone/admin
  이름을 prompts=() 인 합성 픽스처에 재사용해, 실제 동작(프롬프트 1건으로 경고 발생)과
  반대인 상황을 단정한다. 선재 패턴의 연장이며 논리는 맞다. 이름만 혼동 소지.
Task 8: complete (commits e93a493..9a01e62, review clean, 1 minor deferred)

=== 8개 태스크 전부 완료. 전체 브랜치 리뷰로 진행. ===
전체 스위트 112 passed. 이월 minor 총 11건 (아래 목록을 최종 리뷰어에게 전달).

=== 전체 브랜치 리뷰 (opus, a73ef33..9a01e62, 15 commits) ===
결과: Ready to merge = With fixes. Critical 0 / Important 6(I1~I6) / Minor 다수.
이월 minor 11건 트리아지: fix 5건(#1·#6·#9·#10·#11) · leave 6건.
**판정 16건 전부 지지. 5건은 원안보다 낫다는 평가(1/11·4·5·7/8·10).**
Ruling 8 이 리뷰어 제안(깊이1 펜스 강제 종료)을 거부한 것도 맞다고 확인.

**Ruling 17: `errors="replace"` 누락 3곳을 그대로 둔다.**
발견: 계획 Global Constraint 는 "파일 읽을 때 encoding='utf-8', errors='replace'"
를 요구하지만 config.py:104 · daydata.py:60 · build_report.py:40 은 errors 를 안 준다.
결정: 그대로 둔다. 리뷰어도 "오히려 옳은 선택"이라 평가했다.
이유: 이 세 곳은 **사람이 손으로 쓴 설정·데이터 파일**을 읽는다. 깨진 바이트를
조용히 대체 문자로 바꾸면 잘못된 값이 대표님께 가는 문서에 실린다. 터지는 게 맞다.
errors="replace" 가 옳은 곳은 세션 로그·인계 문서처럼 남이 쓴 대용량 입력이다.
계획의 제약이 그 구분을 안 했다 — 계획의 결함이며 코드가 옳다.
틀렸을 때 비용: 설정 파일이 깨졌을 때 친절한 메시지 대신 UnicodeDecodeError.

**Ruling 18: git worktree 이중 계수는 고치지 않고 「한계」에 기록한다.**
발견: 살아 있는 worktree 를 별도 저장소로 잡으면 `git -C <worktree> log --all` 이
본체와 같은 커밋 집합을 돌려줘 "본인 커밋 N건" 이 이중 계수된다. 9/07 근거에 실제로
worktree 경로 한 줄이 잡혔다(당시 폴더가 이미 없어 무해).
결정: 지금 고치지 않는다. 스펙 「한계」 절에 기록한다.
이유: `git_root` 를 worktree 인식으로 바꾸는 것은 `--git-common-dir` 이 .git 디렉터리를
돌려주는 것이라 저장소 루트 유도가 단순하지 않다. 마감 직전에 발견 로직의 핵심
함수를 손대는 위험이 이득보다 크다. 실측 발생 1건이고 그마저 무해했다.
틀렸을 때 비용: worktree 를 쓰는 날 커밋 수가 부풀어 보인다. 근거 커버리지 표에
worktree 경로가 별도 줄로 찍혀 사람이 알아볼 수 있다.

**Ruling 19: 리뷰어의 Recommendations 1·2(단일 진입점 · --scaffold · 사이드카를
data/ 로) 는 구현하지 않고 사용자에게 올린다.**
이유: --scaffold 는 스펙 「설계 결정 4」(행 초안 금지)를 건드리고, 사이드카 위치
변경은 산출물/소스 경계를 바꾼다. 둘 다 스펙 수정이며 사용자 승인 사항이다.
리뷰어 자신도 "사용자 승인 사항으로 올리십시오"라고 적었다.

=== 최종 수정 웨이브 (opus, commit 97edd2e) — 127 passed (112 → +15) ===
컨트롤러 독립 검증: 파이프라인 회귀 없음(날짜별 경고 1건씩 유지), 워크북 17/21행,
  B1='백엔드\n공수산정(85%)', I2 헤딩이 "총 47건 중 8건" 형태로 은닉량 노출.

**Ruling 20: 구현자의 I6b 편차를 수용한다 — 내 지시가 틀렸다.**
발견: 내가 "stderr 에 'not a git repository' 가 없는 비정상 종료는 시끄럽게" 라고
지시했으나, 구현자가 커밋 없는 새 `git init` 저장소는 `rev-parse --abbrev-ref HEAD`
가 `fatal: ambiguous argument 'HEAD'` 로 실패하며 그 문구가 없다고 보고했다.
**컨트롤러가 직접 재현해 확인.** 문자 그대로 따랐으면 dev_root 아래 새 폴더 하나로
수집 전체가 크래시했다 — 내가 회귀를 지시한 셈이다.
결정: `ambiguous argument` 를 두 번째 조용한 패턴으로 유지한 구현을 수용한다.
구현자가 실제 저장소 17곳 × git 명령 3종을 사전 스윕해 non-"not a git repository"
실패가 0건임을 확인하고, 라이브 수집 2회로 재확인했다. I6b 의 의도(dubious
ownership·손상 인덱스·권한 오류 노출)는 온전히 보존된다.

**Ruling 21: test_regression 의 label 단정 완화를 수용한다.**
구현자가 지시 범위를 넘어 `== "백엔드\n공수산정(85%)"` 를
`startswith("백엔드\n공수산정(") + endswith("%)")` 로 완화했다.
근거: `progress` 는 스펙이 "사람이 관리하며 자동 갱신 안 됨" 이라 명시한 값이라
85%→90% 로 바꾸면 스위트가 깨진다 — I5 가 지적한 `len(categories)==9` 와 동일
취약 부류다. Ruling 12 의 load-bearing 부분(display 개행)은 그대로 지킨다.
결정: 수용. I5 의 의도(정당한 변경에 저항하지 않는 테스트)와 일치한다.
검증: B1 은 여전히 정확히 '백엔드\n공수산정(85%)' 임을 컨트롤러가 확인.

**Ruling 22: daydata 최상위 isinstance 가드 추가를 수용한다.**
C3 이 rows/items 범위만 지시했으나 구현자가 "파일 전체가 문자열" 케이스도 막았다.
같은 `.get` → AttributeError 실패 부류이며 한 줄. 매일 손으로 쓰는 입력이다.

관찰(판정 아님): I2 의 새 규칙(커밋 0 저장소는 캡 해제)은 **오늘 출력에는 무영향**
이다 — 9/08 의 커밋 0 저장소는 전부 프롬프트 ≤6건. 구현자가 이를 정직하게 보고하고
동일 20프롬프트 입력을 커밋 유무로 갈라 규칙을 증명하는 테스트를 넣었다.

=== 최종 수정 웨이브 범위 한정 재리뷰 (sonnet, 9a01e62..97edd2e) ===
결과: All findings addressed, no new Critical/Important breakage. **Safe to merge.**
  I1~I6 · B1~B5 · Part C 전부 ADDRESSED, file:line 근거 제시.
  수용한 편차 4건 전부 보고대로 구현됐음 확인. 범위 밖 항목 유입 없음
  (daily.py 없음 · --scaffold 없음 · 사이드카 여전히 비추적 · streamlit_app.py 무수정).
  Minor 1건(비차단): 구현자 보고서의 "손을 댄 테스트" 표가 5개로 적었으나 실제 8개.
  누락된 것은 tests/test_evidence.py 의 B5 리네임 1건. 변경 자체는 정당·무해.
  → 이월. 기록으로 남긴다(보고서 정확성 문제이며 코드 문제 아님).

=== 종료 ===
8개 태스크 + 최종 수정 웨이브 완료. 127 passed. 판정 22건.
