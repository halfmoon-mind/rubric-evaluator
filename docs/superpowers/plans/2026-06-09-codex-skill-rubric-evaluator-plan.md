# Codex Skill Rubric Evaluator 구현 계획

**작성일**: 2026-06-09
**상태**: 초안
**기준 설계**: `docs/superpowers/specs/2026-06-09-skill-rubric-evaluator-design.md`

## 1. 목표

Codex용 Skill을 평가하는 Codex Skill을 만든다.

이 평가기는 `SKILL.md` 기반 Skill 디렉토리를 입력받아 6섹션 30항목 Rubric으로 검사하고, 등급과 수정 가능한 리포트를 출력한다.

핵심 원칙은 다음 하나다.

> 결정적인 결함은 rule 검사로 고정하고, 의미 품질은 Codex 모델 검사로 판단한다.

## 2. 전제와 범위

### 전제

- 평가 대상은 폴더 안에 `SKILL.md`가 있는 Codex Skill이다.
- Skill 호출 여부는 frontmatter의 `description`이 크게 좌우하므로, trigger 관련 평가는 중요도가 높다.
- 평가기 자체도 Codex Skill로 만든다.
- 외부 Python 패키지 없이 Python 표준 라이브러리만 사용한다.
- 모델 검사는 별도 API 호출 CLI가 아니라, Skill을 호출한 Codex가 수행한다.

### 이번 범위

- `SKILL.md` 기반 Skill 평가
- rule 검사 17개 구현
- model 검사 13개 기준 문서화
- 등급 계산
- 사람이 바로 수정할 수 있는 리포트 포맷
- 합성 fixture 기반 검증
- 평가기 자기 자신에 대한 dogfood

### 제외

- slash command 평가
- GitHub Actions 자동 PR comment
- gitleaks 같은 외부 보안 도구 의존
- 독립 LLM API 호출 CLI
- 웹 UI

## 3. 산출물

```text
skill-rubric-evaluator/
├── SKILL.md
├── scripts/
│   ├── check_rules.py
│   └── render_report.py
├── references/
│   └── model-rubric.md
└── tests/
    ├── fixtures/
    │   ├── clean/
    │   ├── bad-kebab/
    │   ├── name-folder-mismatch/
    │   ├── missing-description/
    │   ├── arguments-without-hint/
    │   ├── long-body/
    │   ├── nested-references/
    │   ├── bad-script-syntax/
    │   ├── unmentioned-script/
    │   ├── todo-leftover/
    │   ├── secret-leak/
    │   └── destructive-tool/
    └── test_rules.py
```

`SKILL.md`는 오케스트레이션만 담당한다. 상세한 모델 판정 기준과 예시는 `references/model-rubric.md`에 둔다. 결정적 검사는 `scripts/check_rules.py`에 고정한다.

## 4. 평가 흐름

1. Codex가 사용자로부터 평가 대상 Skill 경로를 받는다.
2. 대상 폴더의 `SKILL.md`, `references/`, `scripts/` 존재 여부를 확인한다.
3. `python3 scripts/check_rules.py <target-skill-dir>`를 실행한다.
4. rule findings JSON을 읽는다.
5. Codex가 `references/model-rubric.md`를 열고 model 검사 13개를 수행한다.
6. rule findings와 model findings를 합친다.
7. 등급을 계산한다.
8. TL;DR, 차단 사유, 섹션별 상세, 수정 제안을 출력한다.

기본 동작은 full report다. rule BLOCKER가 있어도 model 검사는 계속 수행한다. 빠른 차단 모드는 나중에 옵션으로 추가할 수 있다.

## 5. Finding 스키마

모든 검사는 같은 스키마로 합친다.

```json
{
  "id": "3.4",
  "section": "trigger",
  "item": "body-only trigger 안티패턴 없음",
  "severity": "BLOCKER",
  "status": "fail",
  "checker": "model",
  "why": "description에는 호출 조건이 없고 본문에만 사용 시점이 있습니다.",
  "how_to_fix": "description에 무엇을 하는 Skill인지와 언제 사용해야 하는지를 함께 적으세요."
}
```

허용 값:

- `severity`: `BLOCKER`, `MAJOR`, `MINOR`
- `status`: `pass`, `fail`, `na`
- `checker`: `rule`, `model`

## 6. Rule 검사 설계

Rule 검사는 실행할 때마다 같은 결과가 나와야 한다. 정규식, 파일 존재, 줄 수, 간단한 파싱, Python AST처럼 결정적 도구만 사용한다.

### 6.1 구조

| ID | 항목 | 심각도 | 검증 방식 |
| --- | --- | --- | --- |
| 2.1 | YAML frontmatter 파싱 가능 | BLOCKER | `---`로 둘러싼 frontmatter를 flat key/value parser로 파싱 |
| 2.2 | `name`은 kebab-case, 64자 이하 | BLOCKER | `^[a-z0-9]+(-[a-z0-9]+)*$`와 길이 검사 |
| 2.3 | `name`과 폴더명 일치 | BLOCKER | `Path(target).name`과 frontmatter `name` 비교 |
| 2.4 | `description` 1-1024자 | BLOCKER | 문자열 길이 검사 |
| 2.5 | `description`에 XML/HTML 태그 없음 | BLOCKER | `<[A-Za-z][^>]*>` 정규식 |
| 2.6 | 허용된 frontmatter 키만 사용 | MAJOR | whitelist 외 key 검출 |
| 2.7 | `name`/`description`에 예약어 없음 | MAJOR | `claude`, `anthropic` 등 벤더 종속 예약어 검사 |
| 2.8 | Skill 폴더 내 `README.md` 없음 | MINOR | 파일 존재 검사 |

초기 frontmatter whitelist:

- 필수: `name`, `description`
- 선택: `allowed-tools`, `argument-hint`, `user-invocable`, `license`, `homepage`, `author`, `repository`, `mcp_tool`, `mcp_args`, `metadata`

Python 표준 라이브러리에는 YAML 파서가 없으므로, MVP에서는 flat key/value와 간단한 list 값만 지원한다. 복잡한 YAML이 필요해지는 시점에 파서를 확장한다.

### 6.2 트리거

| ID | 항목 | 심각도 | 검증 방식 |
| --- | --- | --- | --- |
| 3.6 | `$ARGUMENTS` 사용 시 `argument-hint` 존재 | MINOR | body에 `$ARGUMENTS`가 있고 frontmatter에 `argument-hint`가 없으면 fail |

### 6.3 콘텐츠

| ID | 항목 | 심각도 | 검증 방식 |
| --- | --- | --- | --- |
| 4.3 | 본문 500줄 이하 | MINOR | frontmatter 제외 body line count |

### 6.4 리소스

| ID | 항목 | 심각도 | 검증 방식 |
| --- | --- | --- | --- |
| 5.3 | references 중첩 금지 | MAJOR | `references/*.md` 안에서 다른 `references/*.md` 링크 검출 |
| 5.4 | 100줄 이상 reference에 목차 존재 | MINOR | 100줄 이상이고 `목차`, `Table of Contents`, 또는 충분한 heading 구조가 없으면 fail |
| 5.6 | scripts syntax 유효 | MAJOR | `.py`는 `ast.parse`, `.sh`는 `bash -n` 가능 시 검사 |
| 5.7 | scripts 경로가 `SKILL.md`에서 언급됨 | MINOR | `scripts/<file>` 문자열 검색 |
| 5.8 | placeholder/TODO 잔재 없음 | MINOR | `TODO`, `FIXME`, `TBD`, `placeholder`, `lorem ipsum` 검색 |

### 6.5 안전성

| ID | 항목 | 심각도 | 검증 방식 |
| --- | --- | --- | --- |
| 6.1 | 평문 secret, credential 없음 | BLOCKER | private key, AWS key, generic token/password 정규식 |
| 6.2 | `allowed-tools`에 destructive 패턴 없음 | BLOCKER | `rm -rf`, `dd if=`, `mkfs`, `chmod -R 777`, fork bomb 등 검사 |

안전성 검사는 false positive를 일부 감수한다. secret이나 destructive command가 배포되는 비용이 더 크기 때문이다.

## 7. Model 검사 설계

Model 검사는 의미 판단이 필요한 항목만 맡긴다. Codex는 `description`, body, file tree, references 요약, scripts 목록, rule findings를 함께 보고 판정한다.

`references/model-rubric.md`에는 각 항목마다 다음을 적는다.

- 판정 질문
- pass 기준
- fail 기준
- 흔한 오탐 주의점
- 좋은 예시
- 나쁜 예시
- `why`와 `how_to_fix` 작성 방식

### 7.1 타당성

| ID | 항목 | 심각도 | 모델 판정 기준 |
| --- | --- | --- | --- |
| 1.1 | 반복되는 워크플로우인가? | MAJOR | 여러 번 재사용될 업무인지 본다. 일회성 작업이면 fail |
| 1.2 | 범용성이 있는가? | MAJOR | 특정 개인, 임시 repo, 한 번의 migration에만 묶이면 fail |
| 1.3 | 에이전트 기본 능력으로 대체 불가능한가? | MAJOR | 일반적인 코딩 조언만 담고 있으면 fail |

### 7.2 트리거

| ID | 항목 | 심각도 | 모델 판정 기준 |
| --- | --- | --- | --- |
| 3.1 | description에 WHAT과 WHEN 모두 포함 | MAJOR | description만 보고 기능과 호출 시점을 알 수 있어야 pass |
| 3.2 | 충분한 트리거 키워드가 있는가 | MAJOR | 사용자가 실제로 말할 법한 표현이 부족하면 fail |
| 3.3 | description과 body의 의미가 일치하는가 | MAJOR | description은 A인데 body는 B를 설명하면 fail |
| 3.4 | body-only trigger 안티패턴 없음 | BLOCKER | 호출 조건이 body에만 있고 description에 없으면 fail |
| 3.5 | 트리거 범위가 과도하지 않음 | MAJOR | 너무 넓어 관련 없는 요청에서도 호출될 것 같으면 fail |

`3.4`는 모델 검사지만 BLOCKER다. Skill body는 Skill이 호출된 뒤에야 읽히므로, 호출 조건이 body에만 있으면 Codex가 Skill을 발견하기 어렵다.

### 7.3 콘텐츠

| ID | 항목 | 심각도 | 모델 판정 기준 |
| --- | --- | --- | --- |
| 4.1 | 구체성 1개 이상 | MINOR | 수치, 코드, why, 시나리오 중 하나도 없으면 fail |
| 4.2 | 기본 지식만 나열하지 않음 | MAJOR | Codex가 이미 아는 일반론이 대부분이면 fail |

### 7.4 리소스

| ID | 항목 | 심각도 | 모델 판정 기준 |
| --- | --- | --- | --- |
| 5.1 | 핵심은 `SKILL.md`, 상세는 `references/`로 분리 | MAJOR | 본문이 무겁거나 reference로 빠져야 할 상세가 많으면 fail |
| 5.2 | references 링크에 읽는 조건 명시 | MINOR | reference를 언제 읽을지 지시가 없으면 fail |
| 5.5 | 실수 가능한 고정 작업은 `scripts/`로 분리 | MAJOR | 반복적이고 실수 가능성이 큰 절차를 매번 자연어로 재현하게 하면 fail |

## 8. 등급 계산

등급은 finding 집계로 계산한다. `na`는 집계에서 제외한다.

| 등급 | 조건 | 의미 | 처리 |
| --- | --- | --- | --- |
| S | BLOCKER 0, MAJOR 0 | 모범 Skill | 통과 |
| A | BLOCKER 0, MAJOR 1-2 | 사용 가능, 소폭 개선 | 통과 |
| B | BLOCKER 0, MAJOR 3-4 | 개선 필요 | 조건부 통과 |
| C | BLOCKER 0, MAJOR 5개 이상 | 대폭 개선 필요 | 통과 가능하지만 수정 강력 권장 |
| F | BLOCKER 1개 이상 | 배포 불가 | 차단 |

MINOR는 등급에 반영하지 않는다. 리포트에는 권고 사항으로 표시한다.

자동화 gate는 단순하게 둔다.

- `F`: fail
- `S`, `A`, `B`, `C`: pass

사람이 운영할 때는 `C`를 조직 정책상 차단으로 올릴 수 있지만, MVP 기본값은 Toss식으로 BLOCKER만 hard gate로 둔다.

## 9. 리포트 포맷

리포트는 작성자가 바로 수정할 수 있어야 한다.

```text
TL;DR: [Workflow Skill] 등급 F | BLOCKER 1, MAJOR 2, MINOR 3

차단 사유:
- 3.4 body-only trigger 안티패턴
  왜 문제인가: description에는 호출 조건이 없고 body에만 사용 시점이 있습니다.
  어떻게 고치는가: description에 WHAT과 WHEN을 함께 적으세요.

우선 수정할 항목:
- 4.2 기본 지식만 나열하지 않음
  왜 문제인가: 본문 대부분이 Codex가 이미 아는 일반론입니다.
  어떻게 고치는가: 이 조직/도구/워크플로우에서만 유효한 규칙, 수치, 예시를 추가하세요.

섹션별 요약:
- Validity: 1 MAJOR
- Structure: PASS
- Trigger: 1 BLOCKER
- Content: 1 MAJOR
- Resources: 3 MINOR
- Safety: PASS
```

리포트 원칙:

- fail 항목은 항상 `왜 문제인가`와 `어떻게 고치는가`를 같이 쓴다.
- BLOCKER를 가장 위에 둔다.
- MAJOR는 수정 우선순위로 묶는다.
- MINOR는 마지막에 권고로 둔다.
- pass 항목은 기본 리포트에서 접거나 요약만 한다.

## 10. 구현 순서

### 1단계: rule 검사 TDD

성공 기준:

- fixture별 `expected.json`을 먼저 만든다.
- `python3 -m unittest discover tests`가 통과한다.
- rule finding 17개가 모두 최소 1개 fixture에서 검증된다.

작업:

1. fixture 구조 작성
2. `tests/test_rules.py` 작성
3. `scripts/check_rules.py` 작성
4. JSON schema 안정화

### 2단계: 등급 계산과 리포트

성공 기준:

- sample findings를 넣으면 S/A/B/C/F가 정확히 계산된다.
- BLOCKER가 하나라도 있으면 F가 된다.
- MINOR만 있는 경우 S가 유지된다.

작업:

1. `scripts/render_report.py` 작성
2. grade 계산 함수 작성
3. markdown report 출력 작성
4. unit test 추가

### 3단계: model rubric 작성

성공 기준:

- Codex가 13개 model finding을 같은 schema로 작성할 수 있다.
- 각 model 항목에 pass/fail 기준과 예시가 있다.
- body-only trigger 판단 기준이 명확하다.

작업:

1. `references/model-rubric.md` 작성
2. model finding 작성 지침 추가
3. 항목별 good/bad 예시 추가

### 4단계: `SKILL.md` 작성

성공 기준:

- description만 보고 평가 Skill의 기능과 호출 시점을 알 수 있다.
- body는 오케스트레이션 중심으로 짧다.
- 상세 판정 기준은 reference로 연결된다.
- scripts 사용 시점이 명확하다.

작업:

1. frontmatter 작성
2. 평가 절차 작성
3. scripts 실행 지침 작성
4. model rubric 로딩 조건 작성
5. 리포트 출력 형식 작성

### 5단계: dogfood와 실제 Skill 점검

성공 기준:

- 평가기가 자기 자신을 평가했을 때 BLOCKER가 없다.
- 잘 만들어진 기존 Skill 2-3개가 rule 검사에서 F로 떨어지지 않는다.
- 일부 나쁜 fixture는 의도한 항목으로 떨어진다.

작업:

1. `skill-rubric-evaluator/` 자기 평가
2. 설치된 local Skill 일부 rule 검사
3. 오탐 발견 시 rule 조정

## 11. 테스트 전략

### Unit test

- frontmatter parser
- kebab-case
- description length
- allowed keys
- argument hint
- body line count
- reference link detection
- script syntax
- secret regex
- destructive allowed-tools
- grade calculation

### Fixture test

각 fixture는 최소한 다음 파일을 가진다.

```text
fixture-name/
├── SKILL.md
└── expected.json
```

필요하면 `references/`와 `scripts/`를 추가한다.

테스트는 `check_rules.py` 출력에서 `expected.json`의 fail finding이 모두 존재하는지 확인한다. 전체 findings를 완전히 고정하면 메시지 개선 때 테스트가 쉽게 깨지므로, `id`, `severity`, `status`, `checker` 중심으로 검증한다.

### Manual model test

모델 검사는 완전 자동 unit test가 어렵다. 대신 대표 Skill 3개를 수동 평가하고 결과를 `docs/superpowers/evals/`에 기록한다.

## 12. 예상 리스크와 대응

### 리스크: frontmatter parser가 실제 YAML을 충분히 못 읽음

대응:

- MVP에서는 flat key/value만 지원한다고 명시한다.
- list 값은 `allowed-tools: [a, b]`와 multi-line `- item`까지만 지원한다.
- parser 한계를 발견하면 dependency 추가 여부를 별도 결정한다.

### 리스크: secret regex 오탐

대응:

- 안전성은 false positive를 감수한다.
- test fixture에 예외 케이스를 추가하며 조정한다.
- fail 메시지에는 "의심" 표현을 써서 사용자가 확인할 수 있게 한다.

### 리스크: model 검사 결과가 흔들림

대응:

- `references/model-rubric.md`에 pass/fail 기준과 예시를 충분히 둔다.
- 모델에게 모든 항목을 같은 schema로 출력하게 한다.
- rule 결과를 함께 제공해 모델이 결정적 결함을 다시 추측하지 않게 한다.

### 리스크: Skill 본문이 너무 길어짐

대응:

- `SKILL.md`에는 절차만 둔다.
- 13개 model 기준과 예시는 reference로 분리한다.
- scripts 내부 구현 설명은 본문에 복제하지 않는다.

## 13. MVP 완료 기준

MVP는 다음을 모두 만족하면 완료다.

- `skill-rubric-evaluator/SKILL.md`가 존재한다.
- `scripts/check_rules.py`가 17개 rule 검사를 JSON으로 출력한다.
- `scripts/render_report.py`가 등급과 markdown report를 출력한다.
- `references/model-rubric.md`가 13개 model 검사 기준을 제공한다.
- fixture 기반 unit test가 통과한다.
- 평가기 자기 자신에 BLOCKER가 없다.
- 사용자가 "이 Skill 평가해줘"라고 했을 때 Codex가 이 평가 Skill을 호출할 수 있는 description을 가진다.

## 14. 다음 작업

이 계획에 문제가 없으면 다음 순서로 구현한다.

1. `skill-rubric-evaluator/` 디렉토리와 fixture skeleton 생성
2. rule 검사 fixture와 `expected.json` 작성
3. `scripts/check_rules.py` 구현
4. rule test 통과
5. report/grade 구현
6. `references/model-rubric.md` 작성
7. `SKILL.md` 작성
8. dogfood
