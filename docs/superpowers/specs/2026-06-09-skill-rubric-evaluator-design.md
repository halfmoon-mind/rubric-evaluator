# skill-rubric-evaluator — 설계 문서

**작성일**: 2026-06-09
**상태**: 승인됨 (구현 계획 대기)
**출처 영감**: [토스 — Skill 품질 Rubric](https://toss.tech/article/skill-quality-rubric)

---

## 1. 목표

Claude Code skill의 품질을 **6섹션 30항목 럽릭**으로 평가해 등급(S/A/B/C/F)과
개선 리포트를 출력하는 **Claude Code skill**을 만든다.

핵심 명제(토스 글): **"결정적인 것은 규칙 기반으로, 의미적인 것은 모델 기반으로."**
- 결정적 검사 17개 → Python 스크립트 (정규식·카운트·AST·파일 존재)
- 의미적 검사 13개 → Claude (references의 기준을 적용)

핵심 가치는 "좋은 skill을 만드는 것"이 아니라 **"나쁜 skill을 차단하는 결정적 게이트"** 제공.

## 2. 스코프

- **포함**: `SKILL.md`을 가진 skill 디렉토리 평가.
- **제외(향후 확장)**: 슬래시 커맨드(`commands/*.md`)는 frontmatter 규약이 달라 이번 범위 밖.
- **의존성 0**: Python 표준 라이브러리만 사용. 외부 도구(gitleaks 등) 요구하지 않음.
  secret 검사도 자체 정규식으로 구현.

## 3. 접근법

**채택: 하이브리드 skill (Approach A)**
스크립트가 규칙검사, Claude가 모델검사, references가 모델검사 기준 보관.

기각:
- **B. 순수 프롬프트형** — 스크립트 없이 Claude가 정규식·카운트까지 전부 수행.
  토스 글이 직접 경고하는 안티패턴(모델은 결정적 검사에서 오작동). 기각.
- **C. 독립 Python CLI가 LLM API까지 호출** — API 키 필요, Claude가 이미 하는 일 중복. 기각.

## 4. 산출물 구조

평가기 자신도 럽릭을 통과(S등급)하도록 설계한다(dogfooding).

```
skill-rubric-evaluator/
├── SKILL.md                 # 오케스트레이션: 평가 흐름·등급 계산·리포트 포맷 (핵심만, 가볍게)
├── scripts/
│   └── check_rules.py       # 규칙검사 17개 → JSON findings 출력 (표준 라이브러리만)
├── references/
│   └── model-rubric.md      # 모델검사 13개 기준 + good/bad 예시 (필요할 때만 로드)
└── tests/
    └── fixtures/            # 합성 fixture(검증용) — 아래 8절 참고
```

`SKILL.md` 파일명은 Claude Code 규약대로 **대문자 `SKILL.md`** (토스 글의 `Skill.md` 아님).

## 5. 동작 흐름 (skill 호출 시)

1. 평가 대상 skill 디렉토리 확정 — 인자로 받거나 사용자에게 물어봄.
2. `python3 scripts/check_rules.py <대상_디렉토리>` 실행 → 규칙검사 17개 결과(JSON).
3. 대상의 `SKILL.md` · `references/*` · `scripts/*`를 Claude가 읽어 모델검사 13개 적용.
4. 30개 finding 통합 → 등급 계산 → 리포트 출력.

**검사 순서**: 규칙 먼저(결정적·테스트 가능) → 모델 나중.
(토스의 운영 방식과 동일: 빠르고 무료인 규칙검사를 통과해야 모델검사 진행. 단,
30항목 리포트를 항상 완전히 제공하기 위해 규칙 BLOCKER가 있어도 모델검사는 수행한다.
빠른 종료가 필요하면 BLOCKER 발견 시 조기 종료 옵션을 둘 수 있으나 기본은 전체 평가.)

## 6. 데이터 모델 — finding 1건

```json
{
  "id": "2.2",
  "section": "structure",
  "item": "name은 kebab-case (≤64자)",
  "severity": "BLOCKER",          // BLOCKER | MAJOR | MINOR
  "status": "fail",               // pass | fail | na
  "checker": "rule",              // rule | model
  "why": "name 'MySkill'이 kebab-case가 아님 (대문자 포함)",
  "how_to_fix": "name을 'my-skill'로 변경하고 폴더명도 일치시키세요"
}
```

`check_rules.py`는 17개 rule finding의 JSON 배열을 stdout으로 출력.
Claude는 13개 model finding을 동일 스키마로 생성해 합친다.

## 7. 등급 & 리포트

**등급 계산** (토스 글과 동일):
- BLOCKER ≥ 1 → **F** (배포 불가, 재작성)
- BLOCKER 0, MAJOR 0 → **S** (모범)
- BLOCKER 0, MAJOR 1–2 → **A**
- BLOCKER 0, MAJOR 3–4 → **B**
- BLOCKER 0, MAJOR 5+ → **C**
- MINOR는 등급에 영향 없음 (권고 사항으로만 표시)

**리포트 포맷** (토스의 "왜 문제인가 + 어떻게 고치는가" 한 묶음):
```
TL;DR: [<Skill 유형>] | 등급 <X> | 개선 포인트:
- <항목>: <왜 문제> → <어떻게 고침>
- ...

[섹션별 상세 표: 항목 | 심각도 | 상태 | 코멘트]
```

## 8. 30항목 럽릭 (전체 매핑)

표기: 심각도(BLOCKER/MAJOR/MINOR) · 검사방식(rule/model)

### 섹션 1. 타당성 (3항목 — 모두 model)
| id | 항목 | 심각도 | 검사 |
|----|------|--------|------|
| 1.1 | 반복되는 워크플로우인가? | MAJOR | model |
| 1.2 | 범용성이 있는가? (특정 프로젝트 한정 아님) | MAJOR | model |
| 1.3 | 에이전트 기본 능력으로 대체 불가능한가? | MAJOR | model |

### 섹션 2. 구조 (8항목 — 모두 rule)
| id | 항목 | 심각도 | 검사 |
|----|------|--------|------|
| 2.1 | YAML frontmatter 파싱 가능 | BLOCKER | rule |
| 2.2 | name은 kebab-case (≤64자) | BLOCKER | rule |
| 2.3 | name과 폴더명 일치 | BLOCKER | rule |
| 2.4 | description 1–1024자 | BLOCKER | rule |
| 2.5 | description에 XML/HTML 태그 없음 | BLOCKER | rule |
| 2.6 | 허용된 frontmatter 키만 사용 | MAJOR | rule |
| 2.7 | name/description에 claude·anthropic 예약어 없음 | MAJOR | rule |
| 2.8 | README.md 없음 (SKILL.md로 충분) | MINOR | rule |

**2.6 허용 키 화이트리스트** — Claude Code 공식 skill frontmatter 문서를 기준으로,
디스크의 설치된 skill에서 관측된 키로 교차검증해 도출한다. (글의 목록을 그대로 베끼지 않음)
- 필수: `name`, `description`
- 관측된 선택 키: `allowed-tools`, `argument-hint`, `user-invocable`,
  `license`, `homepage`, `author`, `repository`, `mcp_tool`, `mcp_args`
- 최종 화이트리스트는 구현 단계에서 공식 문서로 확정.

### 섹션 3. 트리거 (6항목)
| id | 항목 | 심각도 | 검사 |
|----|------|--------|------|
| 3.1 | description에 WHAT(기능)+WHEN(시점) 모두 포함 | MAJOR | model |
| 3.2 | 충분한 트리거 키워드 존재 | MAJOR | model |
| 3.3 | description과 본문의 의미 일치 | MAJOR | model |
| 3.4 | body-only trigger 안티패턴 없음 (호출 조건이 본문에만 있음) | **BLOCKER** | model |
| 3.5 | 트리거 범위가 과도하지 않음 (과잉 호출 방지) | MAJOR | model |
| 3.6 | $ARGUMENTS 사용 시 argument-hint 존재 | MINOR | rule |

### 섹션 4. 콘텐츠 (3항목)
| id | 항목 | 심각도 | 검사 |
|----|------|--------|------|
| 4.1 | 구체성 ≥1 (수치·코드·Why·시나리오 중 하나 이상) | MINOR | model |
| 4.2 | 코딩 에이전트 기본 지식만 나열한 것 아님 | MAJOR | model |
| 4.3 | 본문 500줄 이하 | MINOR | rule |

### 섹션 5. 리소스 (8항목)
| id | 항목 | 심각도 | 검사 |
|----|------|--------|------|
| 5.1 | 핵심은 SKILL.md, 상세는 references/로 분리 | MAJOR | model |
| 5.2 | references 링크에 "언제 읽는지" 조건 명시 | MINOR | model |
| 5.3 | references 중첩 금지 (A→B→C 체인) | MAJOR | rule |
| 5.4 | 100줄 이상 reference에 목차 존재 | MINOR | rule |
| 5.5 | 실수 가능한 고정 작업은 scripts/로 분리 | MAJOR | model |
| 5.6 | scripts syntax 유효 (AST 파싱) | MAJOR | rule |
| 5.7 | scripts 경로가 SKILL.md에서 언급됨 | MINOR | rule |
| 5.8 | placeholder/TODO 잔재 없음 | MINOR | rule |

### 섹션 6. 안전성 (2항목 — 모두 BLOCKER rule)
| id | 항목 | 심각도 | 검사 |
|----|------|--------|------|
| 6.1 | 평문 secret·credential 없음 | **BLOCKER** | rule |
| 6.2 | allowed-tools에 destructive 패턴 없음 | **BLOCKER** | rule |

**6.2 destructive 패턴** (자체 정규식, False Positive 감수·False Negative 0 지향):
`rm -rf`, `dd if=`, `mkfs`, `chmod -R 777`, `:(){ :|:& };:`(fork bomb), `> /dev/sda` 등.
**6.1 secret 패턴**: AWS 키, 일반 API 키/토큰, private key 블록, 하드코딩 비밀번호 등.

### 집계 검증
- 합계: 3 + 8 + 6 + 3 + 8 + 2 = **30** ✓
- 검사방식: rule **17** (2.1–2.8, 3.6, 4.3, 5.3·5.4·5.6·5.7·5.8, 6.1·6.2) / model **13** ✓
- BLOCKER **8개**: 2.1·2.2·2.3·2.4·2.5, 3.4, 6.1·6.2 ✓

## 9. 검증 전략 (핵심 산출물 — 추후가 아니라 1급 작업)

1. **합성 fixture** (`tests/fixtures/`): 특정 검사를 일부러 깨뜨린 미니 skill 폴더 +
   기대 결과. 이것이 테스트 스위트이며 CLAUDE.md "테스트 먼저, 그 다음 통과" 원칙을 충족.
   예시:
   - `bad-kebab/` → BLOCKER 2.2
   - `name-folder-mismatch/` → BLOCKER 2.3
   - `body-only-trigger/` → BLOCKER 3.4
   - `desc-too-long/` → BLOCKER 2.4
   - `secret-leak/` → BLOCKER 6.1
   - `destructive-tool/` → BLOCKER 6.2
   - `nested-references/` → MAJOR 5.3
   - `clean/` → 등급 S (모든 검사 통과)
   각 fixture에 기대 finding을 명시한 `expected.json` 동반.
2. **Dogfood**: 평가기가 자기 자신(`skill-rubric-evaluator/`)을 평가해 **S등급**.
3. **실제 skill 점검**: 디스크의 성숙한 skill(superpowers:* 등) 2–3개에 규칙검사를 돌려
   오탐(False Positive) 확인. 잘 만든 skill이 F면 검사기가 틀린 것.

## 10. 구현 시퀀스 (계획 단계 입력)

1. 규칙검사 17개 + 합성 fixture (TDD: fixture/expected 먼저 → check_rules.py 통과).
2. 등급 계산 + 리포트 포맷.
3. references/model-rubric.md (모델검사 13개 기준 + 예시).
4. SKILL.md 오케스트레이션.
5. Dogfood + 실제 skill 점검으로 검증.

## 11. 미해결/추후

- 2.6 허용 키 최종 화이트리스트는 Claude Code 공식 문서로 확정 (구현 단계).
- 슬래시 커맨드 평가는 향후 확장.
- GitHub Actions PR 자동화는 이번 범위 밖 (이번엔 Claude Code skill 형태).
