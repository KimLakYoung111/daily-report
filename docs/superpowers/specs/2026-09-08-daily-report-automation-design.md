# 일일보고 엑셀 생성 자동화 — 설계

작성일: 2026-09-08
대상 저장소: `C:\Users\klyhj\dev\daily-report\blank-app`

## 배경

대표님께 제출하는 일일보고는 스프레드시트 한 장이고, 열 구성은
`날짜 | 구분(모듈 진행률) | 세부 작업 | 진행률 | 비고`다. 날짜별 블록을 위로
쌓아 올린다.

2026-09-08 이 보고서를 처음 기록 기반으로 만들면서 세 가지가 드러났다.

1. **`daily_report.py`는 세션 로그를 나열할 뿐 보고서가 아니다.** 출력이
   "몇 시에 어떤 세션이 몇 이벤트"라서, 대표님이 볼 "무엇을 끝냈는가"가 없다.
2. **판단이 자동화의 대상이 아니다.** 값이 컸던 작업은 커밋 메시지를 업무 문구로
   바꾼 것이었다. `fix(공수산정): 사전 스캔의 플랫폼 판정을 견적 경로까지 실어 준다`
   → `추천 환경 값 견적 경로 누락 수정`. 규칙으로 환원되지 않는다.
3. **누락이 실제로 발생했다.** 커밋 로그만 보고 표를 만들어 `e2etest/qmeet`의
   작업 6행을 놓쳤다. 그 저장소는 커밋이 2건뿐이었고 실제 작업 대부분이 미커밋
   상태였다. `git status`를 보지 않았기 때문이다.

`build_report.py`는 렌더링(셀 병합·테두리·열 너비)까지 완성했으나, 행 데이터를
담은 `REPORTS` 딕셔너리가 손으로 채운 값이다. 날짜마다 사람이 커밋 로그와
`git status`와 `HANDOFF.md`와 세션 기록을 조사해 넣어야 한다.

## 목표

- 날짜 하나를 지정하면, 그날 작업의 **근거를 전수로** 모아 한 파일에 담는다.
- 그 근거를 읽고 표 데이터를 만드는 일은 Claude가 한다.
- 표 데이터는 코드가 아닌 **날짜별 데이터 파일**로 남아, 과거 보고서를 고칠 때
  코드를 건드리지 않는다.
- 구분(카테고리)과 모듈 진행률은 **사람이 관리하는 설정**에 두어, 날짜별로
  흔들리지 않는다.

## 비목표

- 완전 무인 자동화. 스크립트 안에서 LLM API를 호출해 사람 개입 0으로 만드는
  방향은 채택하지 않는다. 근거 없는 숫자와 문구가 검토 없이 대표님께 가는 위험이
  자동화 이득보다 크다.
- 행 초안 생성. 아래 「설계 결정 4」 참조.
- 누적 진행률 추적표. 기존 시트는 날짜마다 항목 목록을 통째로 이어 붙이는
  방식이었으나(9/07 블록과 9/04 블록이 동일), 이 설계는 **당일 실작업만** 싣는다.
  사용자가 2026-09-08 명시적으로 정한 규칙이다.

## 설계 결정

### 1. 실행 방식 — Claude에게 한 줄 시킨다

스크립트는 근거 수집만 하고, 분류·문구·진행률 판단은 Claude가 한다.
`python daily.py` 한 번으로 끝나는 방식은 항목 문구가 커밋 메시지 그대로 나와
기술적이고, 진행률을 추정할 수 없다.

### 2. 구분은 고정 목록 + 예외 판단

구분 목록과 `저장소 → 구분` 기본 매핑을 `config.yaml`에 고정한다. `GA4`처럼
저장소로 갈라지지 않고 내용으로만 알 수 있는 구분은 `by_content: true`로 표시해
Claude가 판단한다.

날짜마다 자유롭게 구분을 만들면 진행률 추이 비교가 불가능해진다. 대표님이 날짜별로
같은 구분을 찾아 읽기 때문이다.

### 3. 진행률 — 항목은 Claude, 모듈은 사람

- **항목 진행률**: Claude가 인계 문서·커밋 근거로 판단하고, 100%가 아니면 잠긴
  사유를 비고에 적는다. (예: `TC 명세 80%` ← 인계 문서의 `QM103 미작성`)
- **모듈 진행률**(구분 라벨의 `백엔드 공수산정(85%)`): `config.yaml`에 사람이
  관리한다. 전체 화면 목록 같은 외부 기준이 있어야 계산되는 값이라 Claude가
  추정하지 않는다. 2026-09-08 작업에서 이 칸을 두 번 채우지 못했다.

### 4. 행 초안을 만들지 않는다

스크립트가 `저장소 → 구분` 매핑으로 행을 전수 생성하고 Claude가 문구만 다듬는
방식은 채택하지 않는다. 2026-09-08 누락 사고가 정확히 그 구조였다 — 커밋 로그라는
그럴듯한 초안을 믿고 근거 전체를 다시 읽지 않았다. 초안이 있으면 검토가 얕아진다.
그리고 초안 문구는 어차피 거의 전부 다시 쓴다.

## 구성

```
blank-app/
├── config.yaml                 사람이 관리 (구분·매핑·모듈 진행률·본인 식별)
├── collect_evidence.py         신규. 근거 전수 수집
├── build_report.py             개편. 렌더링만
├── data/
│   ├── 2026-09-07.yaml         Claude가 판단해서 쓰는 파일
│   └── 2026-09-08.yaml
├── output/                     .gitignore 처리됨
│   ├── evidence/2026-09-08.md
│   ├── 일일보고-2026-09-08.xlsx
│   └── 일일보고-2026-09-08.tsv
├── daily_report.py             그대로 둠 (범용 세션 조회용)
└── requirements.txt            openpyxl, PyYAML 추가
```

`daily_report.py`는 남긴다. cwd 집계 버그가 있으나 "전체 프로젝트 세션 훑기"라는
다른 용도가 있고, 새 수집기는 보고서용으로 범위가 좁다.

### `config.yaml`

```yaml
# 본인 식별 — 이 목록에 없는 작성자의 커밋은 보고서에서 제외한다
me:
  - klyhja@l-walk.com
  - 61999720+KimLakYoung111@users.noreply.github.com   # PR 병합 시 찍히는 주소

# 구분 목록 — 엑셀에 나타날 순서. 여기 없는 구분은 쓰지 않는다
categories:
  - name: 백엔드 공수산정
    progress: 85%          # 모듈 전체 진행률. 사람이 직접 관리
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
    by_content: true       # 저장소로 안 갈라짐 — 내용으로 판단
  - name: CRM
    by_content: true
  - name: 자동화
    repos: [e2etest/qmeet, e2etest/playwright_base]
  - name: 교육
    repos: [leadwalk_study/2026/second-half-automation-training]

# 수집 대상 루트. 여기 아래 git 저장소를 자동 발견한다
dev_root: C:\Users\klyhj\dev

# 근거에서 걸러낼 자동 생성 세션 (사람이 시킨 작업이 아님)
ignore_prompts:
  - "Review this change for security vulnerabilities"
  - "This session is being continued from a previous conversation"
```

`repos`는 화이트리스트가 아니라 매핑이다. 목록에 없는 저장소에서 작업이 나오면
버리지 않고 `구분 미지정`으로 근거에 올린다. 2026-09-08 목록 기반 조사로
`qmeet-dev-ssh`(세션 이벤트 3,034건, 그날 최다)를 하마터면 놓쳤다.

`me`가 두 개인 이유: 같은 사람이 두 주소를 쓴다. `qmeet_ai`에서 다른 사람 커밋
5건을 걸러내야 했고, 반대로 `playwright_base`에서는 GitHub noreply 주소로 찍힌
본인 커밋 3건이 있었다.

`progress`는 있는 구분에만 붙인다. 기존 시트에서 `%`가 붙은 건 백엔드·프론트뿐이다.

### `collect_evidence.py`

`python collect_evidence.py [YYYY.M.D]` (생략 시 오늘) →
`output/evidence/YYYY-MM-DD.md`

다섯 소스에서 모은다.

| 소스 | 얻는 것 | 없으면 생기는 문제 |
|---|---|---|
| `git log --all` (작성자 필터) | 커밋 목록 | — |
| `git status --porcelain` | 미커밋 작업 | `e2etest/qmeet` 6행 누락 |
| `HANDOFF.md` 최신 섹션 | 진행률 근거·안 한 것 | `TC 명세 80%` 근거 없음 |
| 세션 `~/.claude/projects/**/*.jsonl` | 커밋 없는 작업·시간대 | `qmeet_ai` 정책 검토 2건 (커밋 0) |
| `git rev-parse --abbrev-ref HEAD` | 브랜치 | 폴더 위치 열 |

#### 저장소 자동 발견 — 두 소스의 합집합

```
세션 기록의 cwd 전체  →  git rev-parse --show-toplevel 로 접어 올림
        ∪
config.yaml 의 categories[].repos
```

한쪽만 쓰면 구멍이 난다. 세션만 쓰면 config에 등록됐는데 그날 세션이 없던
저장소를 놓치고, config만 쓰면 새로 등장한 저장소가 조용히 사라진다. 합집합에서
config에 없는 저장소는 `구분 미지정`으로 표시한다.

#### cwd 집계 버그를 여기서 고친다

`daily_report.py`는 세션 파일의 **첫 cwd**로 전체를 집계한다(`s["cwd"] or
o.get("cwd")`). 세션 중간에 디렉터리를 옮기면 그쪽 작업이 통째로 다른 저장소에
붙는다. 2026-09-08 이벤트 최다였던 `qmeet-dev-ssh`가 보고서에 아예 안 나온
원인이다. 새 수집기는 **이벤트마다 cwd를 보고** git 루트로 정규화한다.

#### 미커밋 정보의 시간 한계를 표기한다

`git status`는 실행 시점 상태만 안다. 9/07 보고서를 9/08에 만들면 그 미커밋
목록은 9/07 것이 아니다. 근거 파일 머리에 경고를 박고, 과거 날짜를 넘기면 미커밋
섹션에 `[신뢰 불가 — 과거 날짜]`를 붙인다. 2026-09-07 보고서가 커밋만으로
채워진 것도 이 한계 때문이다.

#### 인계 문서는 헤딩으로 골라 싣는다

`backend2/HANDOFF.md`는 1,500줄이 넘고 최신 섹션만 110줄, `front`는 212줄이다.
저장소 8곳 전문이면 수천 줄이 된다. `HANDOFF.md`는 최신 섹션이 맨 위에 쌓이는
방식이므로 두 번째 `# HANDOFF` 헤딩 전까지만 본 다음, 그 안에서 아래 헤딩만
싣는다.

- `한 일` / `What Was Done` / `Current Status` → 작업 항목·완료 여부
- `안 한 것` / `다음 단계` / `Remaining Work` → 진행률과 비고
- `Uncommitted Changes` → 미커밋 교차 확인

`함정·주의`, `Verification Commands`, `Key File Paths`는 제외한다. 필요하면
근거에 적힌 경로로 직접 읽는다.

#### 출력 형태

아래는 **형태 예시**다. 저장소·구분 조합은 2026-09-08 실측이고, 이벤트 수는
자릿수 감각을 위한 근사치다(git 루트 정규화 후 값은 구현 시 확정된다).

````markdown
# 근거 묶음 — 2026-09-08 (화)
> 수집 2026-09-08 19:30 · 저장소 8곳 · 본인 커밋 36건 (타인 5건 제외)
> ⚠️ 미커밋 정보는 수집 시점 상태입니다.

## 커버리지 점검
| 저장소 | 구분(config) | 커밋 | 미커밋 | 세션 이벤트 | 인계 |
|---|---|---|---|---|---|
| qmeet/backend2          | 백엔드 공수산정  |  5 |  0 | 2,164 | ✓ |
| qmeet/front             | 프론트 공수산정  | 12 |  1 | 2,775 | ✓ |
| qmeet/qmeet_ai          | AI 서버 공수산정 |  4 |  0 |   461 | ✓ |
| qmeet/qmeet-dev-ssh     | 인프라        | 11 |  0 | 3,034 | — |
| e2etest/qmeet           | 자동화        |  2 | 21 | 1,693 | ✓ |
| e2etest/playwright_base | 자동화        |  2 |  0 |   491 | ✓ |
| leadwalk_study/...      | 교육         | (git 아님) | — | 730 | — |
| golfzone/admin          | 구분 미지정     |  0 |  0 |    14 | — |

---
## qmeet/backend2  `[feature/ai_effortEstimate_20260901]`  →  백엔드 공수산정

### 커밋 5건
- 09:29 `66fe6f12` feat(effort-estimate): AI가 고른 테스트 플랫폼을 RCMD_PLTF_CD에 저장한다
- 14:15 `853733e0` docs: 진행 화면 칩이 뒤로 가던 것을 잡고, execMd가 5종 기준임을 확정했다

### 미커밋 — 없음

### 인계 문서 (HANDOFF.md 최신 섹션 · 발췌)
#### 한 일
...
#### 안 한 것 / 다음 단계
1. ★ ③을 고친 뒤로 한 번도 안 돌려 봤다 — 이게 최우선이다.

### 세션 프롬프트 (자동 세션 제외 · 최대 8건)
- 09:08 · qmeet_ai 에 handoff후 커밋 가능한가
````

### `data/YYYY-MM-DD.yaml`

Claude가 근거를 읽고 판단 결과만 적는다. 폴더 경로는 `config.yaml`의 `dev_root`와
`repo` 이름으로 조립되므로 반복해 쓰지 않는다.

```yaml
date: 2026.9.08
rows:
  - category: 백엔드 공수산정
    default_location: { repo: qmeet/backend2, branch: feature/ai_effortEstimate_20260901 }
    items:
      - task: AI 추천 테스트 환경(RCMD_PLTF_CD) 저장
        progress: 100%
      - task: API 문서 공수 기준 정정(환경 1종)
        progress: 100%

  - category: 자동화
    default_location: { repo: e2etest/qmeet, branch: main }
    items:
      - task: 프로젝트 등록 TC 명세 작성(QM101~106)
        progress: 80%
        note: QM103 검증 대상 확정 대기
      - task: TC 입력 양식 제정
        progress: 100%
        note: 양식 2종(문서·엑셀)
        locations:                                    # 저장소 2곳인 항목만 재정의
          - { repo: e2etest/playwright_base, branch: main }
          - { repo: e2etest/qmeet,           branch: main }

  - category: 교육
    default_location:
      repo: leadwalk_study/2026/second-half-automation-training/repos
      branch: git 아님 · 교육생 5명 폴더                  # 브랜치 칸은 자유 문자열
    items:
      - task: 하반기 자동화 교육 4주차 과제 피드백
        progress: 100%
        note: 5명 전원 전달 완료
```

필드 규칙:

- `category` — `config.yaml`의 `categories[].name`과 정확히 일치해야 한다.
- `default_location` — 그 구분의 기본 저장소·브랜치. 항목이 `locations`를
  지정하지 않으면 이 값을 쓴다.
- `items[].locations` — 저장소가 둘 이상인 항목만 적는다. 있으면
  `default_location`을 무시한다.
- `items[].note` — 생략 가능. 비고 열.
- `branch` — 자유 문자열. 브랜치가 아닌 경우(비git 경로) 무엇인지 적는다.

**브랜치를 데이터에 박는 이유**: 렌더링 시점에 git에서 읽으면 과거 보고서를 다시
뽑을 때 그때가 아닌 지금 브랜치가 찍힌다. 보고서는 그날의 스냅샷이어야 한다.

### `build_report.py` 개편

| 항목 | 변경 |
|---|---|
| `REPORTS` 딕셔너리 | 제거 — `data/*.yaml`을 읽는다 |
| 구분 순서 | `config.yaml`의 `categories` 순서로 정렬. **날짜 파일의 순서는 무시.** 날짜별로 구분이 뒤바뀌면 추이를 못 본다 |
| 구분 라벨의 `%` | `config.yaml`의 `progress`에서 붙인다 (`백엔드 공수산정(85%)`) |
| 폴더 위치 열 | `dev_root` + `repo` + `[branch]` 로 조립 |
| 렌더링 (셀 병합·테두리·열 너비·`_` 접두사 폴백) | 그대로. 2026-09-08 검증된 코드 |

CLI는 현재와 같다.

```
python build_report.py            # data/ 아래 전체 날짜
python build_report.py 2026.9.08  # 특정 날짜
```

엑셀 열 구성(현행 유지):

| 열 | 내용 | 너비 |
|---|---|---|
| A | 날짜 (전체 행 병합) | 12 |
| B | 구분 (그룹별 병합) | 17 |
| C | 세부 작업 | 42 |
| D | 진행률 | 9 |
| E | 비고 | 36 |
| F | 폴더 위치 + `[브랜치]` (Consolas 8pt 회색) | 50 |

F열은 제출 전에 숨기거나 삭제할 수 있도록 맨 오른쪽에 둔다.

## 검증

렌더링 전에 확인하고, 어긋나면 처리한다.

| 검사 | 조치 | 막는 실패 |
|---|---|---|
| `category`가 `config.yaml` 목록에 없다 | **에러로 중단** | 오타로 새 구분이 생김 |
| `progress`가 `숫자%` 형식이 아니다 | **에러로 중단** | 빈 칸·`미정` 같은 값이 대표님께 감 |
| `locations`의 `repo` 폴더가 없다 | 경고 | 비git 경로·삭제된 저장소는 허용 |
| 근거 커버리지 표의 저장소가 날짜 파일에 하나도 없다 | 경고 (저장소 이름 지적) | **2026-09-08 `e2etest/qmeet` 누락** |

마지막 검사가 이 설계의 핵심 안전장치다. 근거는 모았는데 표에 옮기지 않은 저장소를
이름으로 지적한다.

## 사고 3건과 방지책 매핑

| 2026-09-08 실제 사고 | 방지책 |
|---|---|
| `e2etest/qmeet` 미커밋 작업 6행 누락 | `git status` 수집 + 커버리지 미반영 경고 |
| `qmeet-dev-ssh`(이벤트 3,034건)가 보고서에 안 나옴 | 이벤트별 cwd 집계 + 저장소 자동 발견 |
| 다른 사람 커밋 5건을 본인 것으로 셀 뻔함 | `config.yaml`의 `me` 목록으로 작성자 필터 |

## 한계

- **과거 날짜의 미커밋 작업은 복원할 수 없다.** `git status`는 현재만 안다.
  당일 실행이 전제이고, 과거 날짜는 커밋·세션·인계 문서까지만 근거가 된다.
- **`by_content` 구분은 Claude 판단에 의존한다.** `GA4`·`CRM`처럼 저장소로
  갈라지지 않는 구분은 근거를 읽고 판단해야 하며, 규칙으로 환원되지 않는다.
- **모듈 진행률은 자동으로 갱신되지 않는다.** 설계 결정 3에 따라 사람이
  `config.yaml`을 고쳐야 한다.
- **기존 시트와 집계 규칙이 다르다.** 기존 9/07 블록은 9/04와 내용이 동일한
  누적 목록이었다. 이 설계는 당일 실작업만 싣는다. 과거 블록을 이 방식으로
  다시 뽑으면 행 구성이 달라진다(9/07의 경우 9행 → 17행).
- **커밋 날짜를 자르는 기준과 보여주는 기준이 다르다.** `--since-as-filter`·
  `--until`은 committer date로 범위를 자르는데, 표시에 쓰는 `%ad`는 author
  date다. 그래서 리베이스·체리픽된 커밋은 옆 날짜 보고서에 들어갈 수 있고,
  그때 찍히는 시각도 그 범위와 안 맞는다. 커밋 시각이 이상하면 `git log
  --pretty=%ad/%cd`로 두 날짜를 직접 비교한다.
- **살아 있는 git worktree는 별도 저장소로 발견된다.** worktree 폴더가
  `dev_root` 아래 있으면 자동 발견에 걸리고, 그 worktree는 부모와 히스토리를
  공유하므로 같은 커밋이 두 저장소에 각각 집계된다(2026-09-08 수집에서 1건
  관측 — 폴더가 이미 삭제돼 있어 실제 중복은 없었다). 커밋 수가 두 배로
  보이면 발견된 저장소 목록에서 worktree를 먼저 확인한다.
