# [요건정의서] SignalForge Twitter/X 기반 36개사 인텔리전스 연동

**문서 버전**: v1.0.0

**작성일**: 2026-10-11

**대상 시스템**: `b_0917_10_QK_EARNING`

**참조 시스템**: `c_1006_subject_outline` (SignalForge)

**대상 도메인**: Contracts, Fab/Capacity, Milestones

**문서 상태**: 구현 전 요구사항 기준선

## 0. 참조 자료

- `../c_1006_subject_outline/src/collectors/twitter_fetcher.py`
- `../c_1006_subject_outline/src/collectors/db_manager.py`
- `../c_1006_subject_outline/src/collectors/catalog_manager.py`
- `../c_1006_subject_outline/src/collectors/link_scraper.py`
- `../c_1006_subject_outline/docs/twitter_fetching_and_time_filtering_logic_20261006.md`
- `../c_1006_subject_outline/config/influencers.yaml`
- `docs/2026-10-10_contracts_fab_milestones_ingestion_requirements.md`
- `docs/2026-10-10_contracts_capacity_milestones_acquisition_requirements.md`
- `docs/2026-10-10_36개기업_계약_생산능력_전략이정표_월별수집_요건정의서.md`

---

## 1. 목적

SignalForge가 Twitter/X에서 수집한 반도체·AI 산업 신호를 36개 기업의 다음 세 가지 인텔리전스 도메인에 안전하게 연결한다.

1. 공급·투자 계약(`CONTRACT`)
2. 생산능력 및 물리 인프라(`CAPACITY`)
3. 전략적 이정표(`MILESTONE`)

Twitter/X는 공식 데이터베이스에 사실을 직접 입력하는 원천이 아니라 **후보 사건 발견 계층**으로 사용한다. 후보에서 공식 공시·기업 IR·정부 자료를 찾아 검증한 뒤에만 운영 데이터로 승격한다.

### 1.1 핵심 목표

- 공식 발표 전후에 발생하는 실시간 공급망 신호를 조기에 포착한다.
- 36개 기업과 제품·시설·거래 상대방을 자동 식별한다.
- 금액, 용량, 물량, 날짜 및 계약 기간을 구조화한다.
- 트윗과 첨부 링크를 원문 공식 자료로 연결한다.
- 출처 없는 C4, 허위 금액 및 잘못된 사건 날짜의 운영 DB 유입을 방지한다.
- 검증된 사건을 월별 기업 매트릭스에 자동 반영한다.

### 1.2 비목표

- Twitter/X 게시물만으로 계약·캐파·이정표를 확정하지 않는다.
- 좋아요·리트윗·조회수가 높은 게시물을 사실로 간주하지 않는다.
- 익명 주장이나 단일 분석가 추정을 자동으로 C3/C4로 승격하지 않는다.
- SignalForge의 기존 DB에 10_QK_EARNING이 직접 쓰지 않는다.

---

## 2. 현행 SignalForge 자산

### 2.1 재사용 가능한 기능

| 기능 | 현행 구현 | 재사용 방안 |
|---|---|---|
| 계정별 수집 | `twscrape.API.user_tweets` | 기존 수집기를 그대로 사용 |
| 계정 카탈로그 | P0·P1·P2 Markdown/YAML | 36개사 관련 계정 태그 확장 |
| 시간 필터 | UTC cutoff, `since_hours` | 증분 동기화 보조 기준으로 사용 |
| 시간대 표시 | KST ISO 8601 | UTC 원본을 추가 보존 |
| 외부 링크 추출 | 정규식 URL 탐지 | canonical URL 정규화 추가 |
| 링크 본문 보강 | `StealthLinkScraper` | 후보 탐색용으로 사용 |
| 중복 방지 | 트윗 URL UNIQUE, `INSERT OR IGNORE` | tweet ID·content hash 보조키 추가 |
| 인게이지먼트 | likes, reposts, replies, views | 후보 우선순위에만 반영 |
| 저장소 | SQLite WAL `timeline.db` | 읽기 전용 증분 조회 |

### 2.2 현행 한계

- 트윗 고유 ID가 전용 컬럼이 아니라 URL에 의존한다.
- KST 변환값만 저장되어 UTC 원본 시각이 분리되지 않는다.
- 리트윗·인용·답글 유형과 원본 게시물 관계가 부족하다.
- 외부 링크가 공식 원문인지 재가공 기사인지 구분하지 않는다.
- 계정 우선순위와 개별 주장의 신뢰도가 분리되지 않는다.
- `since_hours` 방식만으로 장기 장애 후 완전한 소급 수집을 보장하기 어렵다.
- 트윗에서 추출한 수치의 검증·승격 상태를 관리할 staging 계층이 없다.
- 삭제·수정된 트윗의 상태 변경 이력이 없다.

---

## 3. 목표 아키텍처

```text
[Twitter/X 계정]
       ↓
[SignalForge TwitterFetcher]
       ↓
[SignalForge timeline.db / timeline_events]
       ↓ 읽기 전용 증분 어댑터
[twitter_signal_candidates]
       ↓ 엔티티·도메인·주장·수치 추출
[공식 원문 탐색 큐]
       ↓ SEC·DART·IR·정부자료·거래상대방 확인
[검증 및 사용자 검토]
       ↓ 승격
[contracts / fab_capacity / datacenter_capacity / milestones]
       ↓
[36개사 월별 매트릭스와 전체 집계]
```

### 3.1 결합 원칙

- SignalForge는 수집과 발견을 담당한다.
- 10_QK_EARNING은 기업 매핑, 주장 추출, 검증, 승격 및 집계를 담당한다.
- 두 프로젝트는 SQLite DB 파일을 공유 쓰기하지 않는다.
- SignalForge 장애가 10_QK_EARNING 운영 DB를 중단시키지 않아야 한다.
- 동일 Dropbox 경로에 있어도 느슨한 결합을 유지한다.

### 3.2 권장 연동 우선순위

1. SignalForge export 파일(JSONL/SQLite snapshot)을 원자적으로 생성하여 가져오기
2. `timeline.db`를 SQLite read-only URI로 증분 조회
3. 향후 내부 cursor API가 제공되면 API 연동으로 전환

초기 MVP는 read-only SQLite 방식으로 구현한다.

```python
sqlite3.connect(
    "file:../c_1006_subject_outline/data/timeline.db?mode=ro",
    uri=True,
)
```

---

## 4. 수집 대상 계정

### 4.1 계정 등급

SignalForge의 P0/P1/P2는 수집 우선순위이며 사실 신뢰도가 아니다.

| 계정군 | 정의 | 권장 수집 주기 | 기본 처리 |
|---|---|---:|---|
| O0 | 기업 IR·정부·규제기관 공식 계정 | 15~60분 | 링크된 공식 문서를 우선 회수 |
| P0 | 핵심 산업 매체·분석가 | 1시간 | 정량 주장을 우선 검토 큐로 전송 |
| P1 | 공급망·기업 전문 분석가 | 4~12시간 | 복수 신호 또는 공식 링크가 있을 때 우선 검토 |
| P2 | 매크로·루머·큐레이션 계정 | 24시간 | 급증·반복 신호만 보류 큐로 전송 |

### 4.2 카탈로그 확장 필드

기존 인플루언서 카탈로그에 다음 속성을 추가한다.

```yaml
entity_ids:
  - NVIDIA
  - TSMC
signal_domains:
  - CONTRACT
  - FAB_CAPACITY
source_role: ANALYST
languages:
  - en
enabled_for_qk_earning: true
verified_hit_rate: 0.72
false_positive_rate: 0.18
```

### 4.3 역할과 신뢰도의 분리

- `priority`: 수집 순서
- `source_role`: 계정의 역할
- `signal_score`: 후보 검토 순서
- `confidence`: 개별 주장에 부여하는 C1~C4 신뢰도
- `verification_status`: 공식 원문 확인 상태

P0 계정이라고 해서 자동으로 C4가 되지 않는다.

---

## 5. 후보 데이터 스키마

### 5.1 `twitter_signal_candidates`

```sql
CREATE TABLE twitter_signal_candidates (
    signal_id               TEXT PRIMARY KEY,
    tweet_id                TEXT NOT NULL UNIQUE,
    author_handle           TEXT NOT NULL,
    author_name             TEXT,
    author_tier             TEXT,
    source_role             TEXT,
    tweet_url               TEXT NOT NULL,
    content                 TEXT NOT NULL,
    published_at_utc        TEXT NOT NULL,
    published_at_local      TEXT NOT NULL,
    collected_at_utc        TEXT NOT NULL,
    conversation_id         TEXT,
    referenced_tweet_id     TEXT,
    tweet_type              TEXT,
    external_urls_json      TEXT,
    canonical_urls_json     TEXT,
    metrics_json            TEXT,
    entity_ids_json         TEXT,
    signal_domains_json     TEXT,
    extracted_claims_json   TEXT,
    signal_score            REAL,
    source_project          TEXT DEFAULT 'c_1006_subject_outline',
    source_row_id           INTEGER,
    content_sha256          TEXT,
    availability_status     TEXT DEFAULT 'AVAILABLE',
    review_status           TEXT DEFAULT 'NEW',
    official_source_url     TEXT,
    promoted_record_type    TEXT,
    promoted_record_id      TEXT,
    rejection_reason        TEXT,
    created_at              TEXT DEFAULT (datetime('now')),
    updated_at              TEXT DEFAULT (datetime('now'))
);

CREATE INDEX idx_twitter_signal_published
    ON twitter_signal_candidates(published_at_utc);

CREATE INDEX idx_twitter_signal_review
    ON twitter_signal_candidates(review_status, signal_score DESC);

CREATE INDEX idx_twitter_signal_source_row
    ON twitter_signal_candidates(source_project, source_row_id);
```

### 5.2 트윗 유형

- `ORIGINAL`
- `REPLY`
- `QUOTE`
- `REPOST`

리포스트는 기본적으로 새로운 증거로 집계하지 않는다. 인용 게시물은 인용자 의견과 원문 주장을 분리한다.

### 5.3 후보 상태

- `NEW`: 신규 후보
- `CLASSIFIED`: 기업·도메인 분류 완료
- `SOURCE_SEARCH`: 공식 원문 탐색 중
- `REVIEW_REQUIRED`: 검토 필요
- `VERIFIED`: 공식 원문 확인 완료
- `PROMOTED`: 운영 데이터로 승격 완료
- `REJECTED`: 허위·중복·범위 외로 기각
- `ARCHIVED`: 관찰만 유지

---

## 6. 주장 추출 구조

`extracted_claims_json`은 트윗 전체가 아니라 주장 단위 배열로 저장한다.

```json
[
  {
    "claim_id": "CLM-TW-12345-01",
    "claim_type": "CAPACITY_TARGET",
    "subject_entity_id": "TSMC",
    "counterparty_entity_id": "NVIDIA",
    "asset_name": "CoWoS packaging",
    "value_low": 100000,
    "value_high": 120000,
    "unit": "WAFERS_PER_MONTH",
    "currency": null,
    "announced_date": null,
    "target_period": "2026-Q4",
    "evidence_text": "트윗 내 해당 주장을 담은 문장",
    "linked_url": "https://example.com/source",
    "is_forecast": true,
    "needs_official_source": true,
    "claim_confidence": "C1"
  }
]
```

### 6.1 주장 유형

#### Contracts

- `CONTRACT_ANNOUNCEMENT`
- `SUPPLY_AGREEMENT`
- `CAPACITY_RESERVATION`
- `INVESTMENT`
- `PPA_ENERGY`
- `PARTNERSHIP_MOU`
- `CONTRACT_EXPANSION`
- `CONTRACT_END`

#### Capacity

- `CAPACITY_CURRENT`
- `CAPACITY_TARGET`
- `CAPACITY_EXPANSION`
- `FAB_GROUNDBREAKING`
- `TOOL_MOVE_IN`
- `RAMP_UP`
- `OPERATING`
- `DELAYED`
- `SUSPENDED`
- `CANCELLED`

#### Milestones

- `PRODUCT_ANNOUNCEMENT`
- `SAMPLE`
- `CUSTOMER_QUALIFICATION`
- `MASS_PRODUCTION`
- `FIRST_SHIPMENT`
- `REGULATORY_APPROVAL`
- `SUBSIDY_AWARD`
- `STANDARD_RELEASE`
- `SCENARIO_SIGNAL`

### 6.2 추출 필드

- 주체 기업
- 상대 기업 또는 기관
- 계약·자산·제품 유형
- 금액과 원통화
- 물량과 원단위
- 발표일, 실제 발생일, 목표일
- 지역과 시설명
- 확정·계획·추정 여부
- 근거 문장과 외부 링크
- 원문 추가 확인 필요 여부

---

## 7. 기업 매핑

### 7.1 대상

36개 기업의 표준 `entity_id`를 사용한다. 트윗에서 발견되는 ticker, 브랜드, 자회사, 경영진, 제품 및 시설 별칭을 매핑한다.

예시:

```text
NVIDIA, Nvidia, NVDA, 엔비디아 → NVIDIA
Google, Alphabet, GCP, Google Cloud, TPU → GOOGLE
AWS, Amazon Web Services, Annapurna Labs → AMAZON
Hynix, SK hynix, 하이닉스, M15X → SK_HYNIX
Samsung, Samsung DS, 삼성 반도체, P4 → SAMSUNG
SpaceX, xAI, Colossus → SPACEX_XAI
```

### 7.2 매핑 상태

- `EXACT`: 표준명·ticker 직접 일치
- `ALIAS`: 등록 별칭 일치
- `CONTEXTUAL`: 제품·시설 문맥으로 추론
- `AMBIGUOUS`: 복수 기업 가능
- `UNMAPPED`: 신규 외부 기업

`CONTEXTUAL`과 `AMBIGUOUS`는 자동 승격하지 않는다.

---

## 8. 후보 필터링과 점수

### 8.1 1차 필터

1. 36개 기업명·ticker·별칭·제품·시설 탐지
2. 계약·투자·증설·착공·양산·출하·지연 동사 탐지
3. 금액·용량·물량·기간 표현 탐지
4. 공식 공시·IR·정부·거래상대방 링크 여부 확인
5. 기존 사건 및 event family와 유사도 비교

### 8.2 점수표

| 항목 | 배점 | 설명 |
|---|---:|---|
| 공식 계정·검증된 계정 | 20 | O0 및 과거 적중률이 높은 P0 우대 |
| 공식 원문 링크 | 25 | 공시·IR·정부 문서 링크 |
| 기업·자산 명시 | 15 | 주체, 상대방, 시설 또는 제품이 명확함 |
| 정량성 | 15 | 금액, MW, WSPM, GPU 수, 날짜 포함 |
| 독립 교차 신호 | 15 | 서로 다른 원출처에서 같은 주장 확인 |
| 최신성과 상태 변경 | 10 | 신규 계약·가동·지연·취소 우대 |

### 8.3 처리 기준

- 80점 이상: P0 검토 큐 및 공식 원문 자동 탐색
- 60~79점: 일반 검토 큐
- 40~59점: 보류 큐
- 40점 미만: 자동 기각 후보

인게이지먼트는 후보 발견 우선순위에만 사용하며 사실 신뢰도를 직접 높이지 않는다.

---

## 9. 출처와 신뢰도

### 9.1 출처 등급

| 등급 | 출처 | 운영 원칙 |
|---:|---|---|
| S1 | SEC·DART·MOPS·정부 문서·기업 IR | 단독 확정 가능 |
| S2 | 공식 계정·공식 컨퍼런스·상대 기업 발표 | 연결 원문 확인 후 공식 근거 사용 |
| S3 | Reuters·Bloomberg·원취재 전문매체 | 공식 확인 또는 독립 출처 추가 권장 |
| S4 | 시장조사·증권사·공급망 분석 | 추정치로만 저장 |
| S5 | 일반 X 계정·블로그·커뮤니티 | 후보 발견 전용 |

### 9.2 C1~C4 승격 규칙

| 후보 상태 | 허용 신뢰도 |
|---|---:|
| 일반 트윗 단독 | C1 |
| 검증된 전문계정 단일 주장 | C1~C2 |
| 공식 기업계정 게시물만 확인 | C2 |
| 독립 S3 두 곳 일치 | C3 |
| S1/S2 원문이 주장·수치 직접 확인 | C4 |

### 9.3 금지 규칙

- P0 계정이라는 이유로 C4를 부여하지 않는다.
- 게시물의 조회수·좋아요 수로 C3/C4를 부여하지 않는다.
- 첨부 기사 요약만으로 C4를 부여하지 않는다.
- 익명 소식통 기반 금액을 확정 계약금액으로 집계하지 않는다.
- 공식 원문이 연결되지 않은 Twitter 후보를 월별 공식 매트릭스에 포함하지 않는다.

---

## 10. 공식 원문 탐색

### 10.1 탐색 순서

1. 트윗에 포함된 공식 링크
2. 주장 주체 기업의 IR·뉴스룸
3. 거래 상대방의 IR·뉴스룸
4. SEC·DART·MOPS·EDINET·정부 계약·보조금 문서
5. Reuters·Bloomberg 등 원취재 기사
6. 전문 리서치 및 복수 분석가 교차검증

### 10.2 검색 키 생성

```text
기업명 + 상대방 + contract/agreement/investment
기업명 + 시설명 + capacity/ramp/tool move-in
기업명 + 제품명 + sample/qualification/mass production
기업명 + 금액/용량 + 공식 발표 월
```

### 10.3 원문 저장

검증에 사용한 자료마다 다음을 저장한다.

- 원문 URL과 canonical URL
- 발행자와 문서 유형
- 게시일과 접근일
- 로컬 원문 경로
- 콘텐츠 SHA-256
- 근거 문구와 문서 내 위치
- 주장별 일치·불일치 판정

---

## 11. 증분 동기화

### 11.1 cursor 테이블

```sql
CREATE TABLE external_sync_cursors (
    source_project       TEXT PRIMARY KEY,
    last_source_row_id   INTEGER,
    last_published_at    TEXT,
    last_success_at      TEXT,
    last_error           TEXT,
    updated_at           TEXT DEFAULT (datetime('now'))
);
```

### 11.2 증분 조회

```sql
SELECT *
FROM timeline_events
WHERE source = 'twitter'
  AND id > ?
ORDER BY id ASC;
```

### 11.3 동기화 규칙

- 성공적으로 후보 DB에 커밋한 뒤 cursor를 갱신한다.
- 장애 복구 시 마지막 cursor부터 다시 읽는다.
- 최근 6시간을 겹쳐 조회해 경계 누락을 보완한다.
- `tweet_id`가 1차 중복키다.
- canonical tweet URL과 content hash를 보조키로 사용한다.
- SignalForge DB가 잠겼거나 없으면 본 시스템은 정상 동작을 계속하고 오류를 기록한다.

---

## 12. 중복과 사건 family

### 12.1 중복키

1. tweet ID
2. canonical tweet URL
3. content hash
4. 동일 외부 공식 원문 URL
5. 동일 기업·상대방·날짜·금액·자산의 주장 유사도

### 12.2 관계 처리

- 리포스트는 새 주장으로 집계하지 않는다.
- 같은 공식 발표를 인용한 여러 트윗은 하나의 후보 family로 묶는다.
- 계약 발표, 증액, 이행, 종료는 별도 사건이지만 동일 `event_family_id`로 연결한다.
- buyer와 seller 양쪽 기업에 표시하되 전체 계약 수와 금액은 한 번만 집계한다.
- Twitter 후보와 뉴스 후보가 같은 원문을 가리키면 하나의 검증 작업으로 합친다.

---

## 13. 운영 DB 승격

### 13.1 자동 승격 금지

Twitter 후보는 검증 완료 전 `contracts`, `fab_capacity`, `datacenter_capacity`, `milestones`에 직접 INSERT하지 않는다.

### 13.2 승격 조건

다음 조건을 모두 충족해야 한다.

1. 36개사 표준 entity mapping 완료
2. 도메인과 사건 유형 확정
3. 실제 발생일과 발표일 구분
4. 공식 원문 또는 C3 교차검증 근거 확보
5. 금액·용량·단위·통화의 원문 값 보존
6. 실제와 전망 구분
7. 기존 사건과 중복 및 family 검사 완료
8. 검토 상태 `VERIFIED`

### 13.3 승격 결과

- `promoted_record_type`: CONTRACT, CAPACITY, MILESTONE
- `promoted_record_id`: 운영 테이블 PK
- `review_status`: PROMOTED
- 운영 레코드에 `source_signal_id` 역참조 저장
- 원문과 트윗을 모두 provenance chain으로 연결

### 13.4 기각 사유

- `NO_OFFICIAL_SOURCE`
- `FALSE_OR_MISLEADING`
- `DUPLICATE`
- `OUT_OF_SCOPE`
- `WRONG_DATE`
- `WRONG_ENTITY`
- `UNSUPPORTED_NUMBER`
- `RUMOR_ONLY`
- `STALE_REPOST`

---

## 14. 월별 매트릭스 반영

### 14.1 반영 대상

- 기본 화면: C3/C4로 승격된 사건
- 후보 보기: C1/C2 Twitter 신호
- Twitter 후보와 공식 사건은 서로 다른 색상과 배지로 표시

### 14.2 날짜 귀속

- 공식 사건은 실제 발생일 기준 월에 배치한다.
- 실제 발생일을 모르면 공식 발표일 기준으로 배치한다.
- 트윗 게시일은 탐지 시각이지 사건 발생일이므로 월 배치 기준으로 사용하지 않는다.
- 미래 목표는 발표 월과 목표 월을 별도 레코드로 관리한다.

### 14.3 집계 제외

다음 항목은 공식 전체 집계에서 제외한다.

- 미검증 Twitter 후보
- 리포스트 수
- 좋아요·조회수
- 익명 루머 금액
- 중복된 buyer·seller 참여 금액
- 공식 원문에서 확인되지 않은 추정 캐파

---

## 15. 검토 화면

후보 검토 화면은 다음 정보를 한 번에 제공한다.

- 트윗 원문과 작성자
- 작성 시각 및 수집 시각
- P0/P1/P2, source role, 과거 적중률
- 좋아요·리트윗·답글·조회수
- 추출된 기업과 도메인
- 주장별 금액·물량·날짜
- 첨부 링크와 스크랩 요약
- 공식 원문 후보
- 기존 운영 사건과 유사도
- 승인·수정·기각 버튼
- 기각 사유와 검토 메모

---

## 16. 기능 요구사항

| ID | 요구사항 | 우선순위 |
|---|---|---:|
| FR-01 | SignalForge timeline DB를 읽기 전용으로 증분 조회한다. | Must |
| FR-02 | 트윗을 별도 후보 테이블에 멱등 적재한다. | Must |
| FR-03 | 36개 기업과 제품·시설 별칭을 자동 매핑한다. | Must |
| FR-04 | Contracts·Capacity·Milestones 후보를 주장 단위로 추출한다. | Must |
| FR-05 | 금액·용량·물량·날짜·상대방을 구조화한다. | Must |
| FR-06 | 공식 원문을 자동 탐색하고 후보에 연결한다. | Must |
| FR-07 | 계정 우선순위와 주장 신뢰도를 분리한다. | Must |
| FR-08 | 공식 원문이 없는 후보의 C4 승격을 금지한다. | Must |
| FR-09 | 중복 게시물과 같은 사건 family를 병합한다. | Must |
| FR-10 | 검증된 사건만 운영 테이블로 승격한다. | Must |
| FR-11 | 승격·기각 이력과 검토자를 기록한다. | Must |
| FR-12 | C1/C2 후보와 C3/C4 공식 사건을 UI에서 분리한다. | Must |
| FR-13 | 월별 매트릭스에 검증 사건을 자동 반영한다. | Should |
| FR-14 | 삭제·수정된 트윗의 상태 이력을 보존한다. | Should |
| FR-15 | 계정별 검증 적중률과 오탐률을 계산한다. | Should |

---

## 17. 비기능 요구사항

- **읽기 전용성**: 연동 시스템은 SignalForge DB를 수정하지 않는다.
- **멱등성**: 반복 동기화해도 동일 후보가 중복 생성되지 않는다.
- **감사 가능성**: 후보→원문→검증→승격의 전 과정을 추적한다.
- **장애 격리**: Twitter 또는 SignalForge 장애가 웹앱과 운영 DB를 중단시키지 않는다.
- **보안**: Twitter 계정 자격증명과 세션 쿠키를 가져오거나 로그에 기록하지 않는다.
- **시간 정확성**: UTC 원본과 Asia/Tokyo 표시 시간을 모두 유지한다.
- **성능**: 후보 10만 건에서 신규 1,000건 증분 동기화를 60초 이내 목표로 한다.
- **보존성**: 삭제된 게시물도 원문 해시와 가용성 상태를 유지한다.
- **DB 안전성**: 모든 쿼리는 파라미터화하고 트랜잭션 실패 시 rollback한다.

---

## 18. 테스트 요구사항

### 18.1 단위 테스트

- Twitter URL에서 tweet ID 추출
- UTC/KST 변환과 날짜 경계
- entity alias mapping
- 금액·통화·MW/GW·WSPM 파싱
- 트윗 유형 분류
- content hash 및 중복 판정
- 점수 계산
- C1~C4 승격 제한

### 18.2 통합 테스트

- 임시 SignalForge SQLite DB에서 read-only 증분 수집
- cursor 장애 복구와 재실행 멱등성
- 같은 공식 원문을 가리키는 여러 트윗 병합
- 사용자 승인 후 운영 테이블 승격
- 기각 후보가 공식 매트릭스에서 제외되는지 확인
- source signal에서 운영 레코드까지 역추적

### 18.3 회귀 테스트 사례

다음 오류가 재발하지 않아야 한다.

- 2024년 제품 출시를 2026년 사건으로 저장
- 장기간 서비스 의무액을 특정일의 자본유치로 저장
- 공식 원문이 없는 공급계약 금액에 C4 부여
- 같은 계약을 buyer와 seller에서 이중 금액 집계
- 트윗 게시일을 실제 계약일로 오인

---

## 19. 모니터링

### 19.1 운영 지표

- 신규 Twitter 후보 수
- 기업 매핑 성공률
- 공식 원문 발견률
- 후보→검증 전환율
- 후보→운영 DB 승격률
- 계정별 검증 적중률·오탐률
- 평균 검증 소요시간
- 중복 병합률
- 잘못된 날짜·금액 탐지 건수
- cursor 지연 시간

### 19.2 경보

- SignalForge DB 접근 실패
- cursor가 6시간 이상 갱신되지 않음
- 특정 계정 수집량 급감 또는 폭증
- 공식 원문 없이 C4 승격 시도
- 동일 tweet ID 또는 운영 record 중복
- 미래 날짜가 실제 사건으로 저장됨

---

## 20. 구현 단계

### Phase 1 — 읽기 전용 후보 수집

1. `twitter_signal_candidates` 및 cursor 테이블 생성
2. SignalForge read-only adapter 구현
3. tweet ID·URL·hash 기반 멱등 수집
4. UTC 원본 시각 보존

### Phase 2 — 분류 및 추출

1. 36개사 alias 사전 구성
2. 도메인·주장 유형 분류
3. 금액·용량·날짜 추출
4. 점수와 검토 큐 생성

### Phase 3 — 공식 원문 검증

1. 첨부 링크 canonicalization
2. 기업 IR·공시·정부 원문 탐색
3. 근거 문구·해시·로컬 파일 저장
4. 주장별 C1~C4 판정

### Phase 4 — 운영 DB 승격

1. 승인·수정·기각 UI
2. event family와 중복 검사
3. 도메인 테이블 승격
4. 월별 매트릭스 및 전체 집계 반영

### Phase 5 — 품질 피드백

1. 계정별 적중률·오탐률 산출
2. 후보 점수 가중치 보정
3. 반복 오탐 키워드·계정 억제
4. 누락 감사 및 회귀 테스트 자동화

---

## 21. 수용 기준

다음 조건을 모두 만족하면 1차 구현을 완료한 것으로 판단한다.

1. SignalForge DB를 수정하지 않고 신규 Twitter 이벤트를 가져올 수 있다.
2. 반복 실행 시 동일 트윗이 중복 적재되지 않는다.
3. 트윗의 UTC 작성 시각과 로컬 표시 시각이 모두 보존된다.
4. 36개 기업 alias mapping 결과와 불확실 상태가 구분된다.
5. Contracts·Capacity·Milestones 주장이 구조화된다.
6. 공식 원문이 없는 트윗은 운영 DB로 자동 승격되지 않는다.
7. C4는 S1/S2 원문에서 주장과 수치가 확인된 경우에만 허용된다.
8. 같은 사건을 다룬 여러 트윗은 하나의 family로 병합된다.
9. 승인·기각·수정 이력과 근거가 보존된다.
10. 승격 사건이 올바른 사건 발생월의 기업 매트릭스에 반영된다.
11. Twitter 후보의 금액은 검증 전 공식 전체 집계에 포함되지 않는다.
12. 잘못된 연도·금액·기업 매핑 회귀 테스트를 통과한다.

---

## 22. 최종 결론

`c_1006_subject_outline`의 Twitter 수집 자산은 36개 기업 인텔리전스의 실시간 후보 발견에 재사용할 수 있다. 그러나 Twitter는 빠른 대신 수정·삭제·재인용·루머 위험이 있으므로 운영 DB의 직접 입력원으로 사용해서는 안 된다.

최종 원칙은 다음과 같다.

```text
Twitter는 발견한다.
공식 원문이 검증한다.
사용자 또는 검증 규칙이 승인한다.
운영 DB는 검증된 사실만 집계한다.
```
