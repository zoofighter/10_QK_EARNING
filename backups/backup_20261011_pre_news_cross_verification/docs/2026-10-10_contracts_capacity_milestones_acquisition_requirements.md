# [요건정의서] 대규모 공급·투자 계약, 생산능력, 전략적 이정표 데이터 수집 체계

**문서 버전**: v1.1.0  ****
**작성일**: 2026-10-10  
**프로젝트 기준 시점**: 2026-09-10  
**적용 범위**: 36개 기업, 8대 밸류체인 레이어  
**대상 데이터**: `contracts`, `fab_capacity`·`datacenter_capacity`, `milestones`  
**문서 상태**: 구현 전 요건 기준선(Baseline)

**연관 문서**:[[2026-10-10_contracts_fab_milestones_ingestion_requirements]]******
- [AGENTS.md](file:///Users/boon/Dropbox/03_code/b_0910_memory_claude/AGENTS.md)
- [requirements_spec.md](file:///Users/boon/Dropbox/03_code/b_0910_memory_claude/docs/requirements_spec.md)
- [db_architecture.md](file:///Users/boon/Dropbox/03_code/b_0910_memory_claude/docs/db_architecture.md)
- [2026-09-10_fab_capacity_spec.md](file:///Users/boon/Dropbox/03_code/b_0910_memory_claude/docs/2026-09-10_fab_capacity_spec.md)
- [2026-09-11_data_source_reliability.md](file:///Users/boon/Dropbox/03_code/b_0910_memory_claude/docs/2026-09-11_data_source_reliability.md)
- [2026-09-16_raw_layer_architecture_and_rag_comparison.md](file:///Users/boon/Dropbox/03_code/b_0910_memory_claude/docs/2026-09-16_raw_layer_architecture_and_rag_comparison.md)
- [SignalForge Twitter 수집 로직](file:///Users/boon/Dropbox/03_code/c_1006_subject_outline/docs/twitter_fetching_and_time_filtering_logic_20261006.md)
- [SignalForge Twitter Fetcher](file:///Users/boon/Dropbox/03_code/c_1006_subject_outline/src/collectors/twitter_fetcher.py)

**변경 이력**:
- v1.1.0 (2026-10-10): `c_1006_subject_outline`를 참조한 Twitter/X 후보 시그널 수집 요건 추가
- v1.0.0 (2026-10-10): 최초 작성

---

## 1. 목적과 결론

이 요건의 목적은 개별 뉴스 링크를 쌓는 것이 아니라 다음 연결고리를 재현 가능한 데이터로 만드는 것이다.

```text
수요 주체의 투자·구매 약정
        ↓ 계약 기간·금액·물량
공급자의 팹·패키징·데이터센터·전력 Capacity 증설
        ↓ 준공·가동·수율·고객 인증
제품 출시·양산·납품이라는 전략적 Milestone
        ↓
2026~2028년 매출 인식, 병목, 공급과잉/부족 시나리오
```

수집 체계의 핵심 결론은 다음과 같다.

1. **공식 원문을 우선 수집**하고, 보도·리서치는 공식 문서에 없는 금액·물량·고객·일정을 보완하는 데 사용한다.
2. 계약 발표, 계약 이행, 캐파 증설, 제품 양산은 서로 다른 사건이므로 **별도 레코드로 저장하고 관계 키로 연결**한다.
3. `2026-Q3` 이후의 미래 수치와 사건은 출처가 공식 로드맵이어도 반드시 `is_forecast=1`로 관리한다.
4. 금액·WSPM·MW·출하량이 공개되지 않으면 억지로 하나의 숫자를 만들지 않고, **범위·상한·하한·비공개 상태와 산식**을 보존한다.
5. 현재 DB는 요약값을 담을 수 있으나 다중 출처, 변경 이력, 범위값, 계약-캐파-마일스톤 연결이 부족하므로 단계적으로 보강한다.

---

## 2. 현재 상태와 보완 필요사항

2026-10-10 현재 DB에는 `contracts` 15건, `fab_capacity` 12건, `milestones` 25건이 존재한다. 기존 구조는 분석의 뼈대는 갖추었으나 운영형 수집 시스템으로 사용하려면 아래 결함을 해소해야 한다.

| 구분 | 현재 관찰 | 요구되는 보완 |
| :--- | :--- | :--- |
| 원천 연결 | `raw_source`가 비어 있거나 포괄적 출처명만 존재 | 레코드마다 원문 파일, 원문 URL, 발행자, 게시일, 접근일, 근거 문구 위치 저장 |
| 계약 금액 | 단일 `value_b`만 존재 | 확정액/최대액/추정액, 현금/클라우드 크레딧/현물, 총액/연간액 구분 |
| 계약 상대방 | buyer-seller 2자 구조 | 복수 투자자·공급사·고객·정부기관을 지원하는 참여자 구조 |
| 계약 상태 | 신뢰도만 있고 이행상태가 약함 | 발표/서명/조건부/진행/증액/완료/취소/만료 상태 이력 |
| Capacity | 현재값과 목표값만 존재 | 측정 기준일, 단위, 명목/유효 캐파, 증설 단계, 제품별 할당, 산식 필요 |
| Milestone | 날짜 하나로 확정/전망 저장 | 발표일, 목표일, 실제 달성일, 날짜 정밀도 및 지연 여부 분리 |
| 미래 판정 | 일부 2026-09 사건의 확정·전망 의미가 혼재 | 프로젝트 기준시점과 사건 성격을 함께 적용하는 판정 규칙 |
| 변경 이력 | 최신값으로 덮어쓸 위험 | 원천 불변 + 버전/관측치 이력 + 정정 사유 기록 |
| 엔티티 연결 | 텍스트 고객명 포함 | 36개 마스터는 관계 테이블로 연결하고 외부 기업만 텍스트 보조값 사용 |

> 현행 데이터에는 `공식 발표`, `업계 추정`처럼 상세 인용이 없는 행과 `bookmarks_index.json` 하나만 가리키는 행이 섞여 있다. 기존 값은 삭제하지 않고 `LEGACY_UNVERIFIED` 검증 대기열로 분류한 뒤 공식 원문부터 역검증한다.

---

## 3. 수집 대상의 정의와 포함 기준

### 3.1 Contracts: 대규모 공급·투자 계약

다음 중 하나 이상을 충족하면 수집한다.

- 공개 계약·투자액이 **USD 1B 이상**
- 금액이 비공개라도 GPU 10,000개 이상, 데이터센터 100MW 이상, 웨이퍼 10,000 WSPM 이상 등 산업 공급에 유의미한 물량
- HBM, GPU/ASIC, 선단 파운드리, 첨단 패키징, EUV 장비처럼 병목 품목의 장기·우선·독점 공급 약정
- 지분 투자, 합작법인, 클라우드 크레딧, 오프테이크, PPA 등 2026~2028년 수요 또는 공급능력을 구속하는 약정
- 금액·물량이 비공개라도 36개 기업 중 2개 이상을 직접 연결하고 전략 방향을 바꾸는 파트너십

단순 MOU는 `binding_level=NON_BINDING`으로 저장하며 확정 계약액 합계에서는 제외한다. 같은 거래의 최초 발표, 증액, 수정, 종료는 새 계약으로 중복 생성하지 않고 하나의 `contract_id` 아래 버전 또는 상태 이력으로 기록한다.

**표준 계약 유형**:

`SUPPLY`, `CAPACITY_RESERVATION`, `CLOUD_COMPUTE`, `INVESTMENT_EQUITY`, `INVESTMENT_CONVERTIBLE`, `JOINT_VENTURE`, `PPA_ENERGY`, `FOUNDRY`, `PACKAGING`, `LICENSE`, `SERVICE`, `PARTNERSHIP_MOU`

### 3.2 Capacity: 물리적 공급능력

Capacity는 공장만 뜻하지 않는다. 수요가 매출로 전환되는 과정의 물리적 병목을 추적한다.

| 자산 유형 | 핵심 단위 | 대표 대상 |
| :--- | :--- | :--- |
| 웨이퍼 팹 | WSPM | DRAM, NAND, 로직 N2/N3/N4 |
| 첨단 패키징 | wafers/month, packages/month | CoWoS, HBM 적층·패키징, 2.5D |
| 장비 공급 | systems/year, backlog | EUV/High-NA, 식각·증착 장비 |
| 데이터센터 | MW/GW, IT load MW | 하이퍼스케일러·네오클라우드 캠퍼스 |
| 가속기 클러스터 | GPU/ASIC 수량 | GB200/NVL72, TPU, Trainium |
| 전력 인프라 | MW/GW, MWh | PPA, 원전, 가스터빈, 변압기·UPS |
| 네트워크 | Tbps, ports, units | 800G/1.6T 스위치·광모듈 |

포함 기준은 36개 기업이 소유·운영·예약하거나 해당 기업의 매출에 중대한 영향을 주는 자산이다. 동일 팹 안의 서로 다른 공정·제품 라인은 캐파를 합산할 수 없으면 별도 `capacity_asset_id`로 관리한다.

### 3.3 Milestones: 전략적 이정표

전략적 이정표는 실적 발표 자체가 아니라 **공급능력, 기술 경쟁력, 매출 인식 또는 산업 구조가 바뀌는 검증 가능한 사건**이다.

**포함 카테고리**:

- `PRODUCT_ANNOUNCEMENT`, `SAMPLE`, `CUSTOMER_QUALIFICATION`, `MASS_PRODUCTION`, `FIRST_SHIPMENT`
- `FAB_GROUNDBREAKING`, `TOOL_MOVE_IN`, `RISK_PRODUCTION`, `CAPACITY_RAMP`, `CAPACITY_TARGET_REACHED`
- `CONTRACT_ANNOUNCEMENT`, `CONTRACT_START`, `CONTRACT_EXPANSION`, `CONTRACT_END`
- `REGULATORY_APPROVAL`, `SUBSIDY_AWARD`, `PARTNERSHIP`, `STANDARD_RELEASE`
- `DELAY`, `CANCELLATION`, `RESTRUCTURING`, `SCENARIO_SIGNAL`

제품 발표와 양산, 고객 인증과 첫 출하는 각각 별도 레코드다. “로드맵상 출시 예정”은 전망이고, 실제 출하를 공식 확인한 시점부터 확정 사건으로 승격한다.

---

## 4. 원천과 수집 채널 우선순위

### 4.1 출처 등급

| 등급 | 출처 | 용도 | 데이터 판정 |
| :---: | :--- | :--- | :--- |
| S1 | 규제 공시, 정부 계약·보조금 문서, 회사 IR·보도자료·실적자료·공식 블로그 | 계약 존재, 금액, 일정, 공식 목표 확정 | 단독으로 확정 가능 |
| S2 | 컨퍼런스 발표자료, 공식 연설·영상·컨콜 전문, 고객사·공급사 상대 확인 | 세부 물량·로드맵·상호 검증 | 공식 자료로 취급하되 문맥 확인 |
| S3 | Reuters/Bloomberg 등 원취재 매체, 신뢰도 높은 산업 전문지 | 비공개 조건, 일정 변경, 익명 소싱 | 독립 2개 출처 또는 후속 공식 확인 권장 |
| S4 | 증권사 리서치, TrendForce 등 시장조사, 공급망 채널체크 | 물량·ASP·수율·캐파 추정 | 추정치로만 저장 |
| S5 | 블로그, X, 커뮤니티, 2차 재가공 기사 | 후보 발견과 탐색 키워드 확보 | 단독 DB 확정 금지 |

`confidence`는 출처 인지도만이 아니라 **주장별 근거 강도**에 따라 부여한다.

- `C4`: S1/S2 원문이 주장과 수치를 직접 확인
- `C3`: S1/S2 일부 확인 + S3 교차검증, 또는 독립 S3 두 곳 일치
- `C2`: S4 추정이나 단일 S3 보도
- `C1`: S5·루머·내부 시나리오, 정식 집계 제외

### 4.2 기업별 상시 모니터링 채널

1. **미국 상장사**: SEC 8-K, 10-Q, 10-K, DEF 14A, 회사 IR 뉴스·실적자료
2. **한국 기업**: DART 주요사항보고서·사업보고서, 회사 IR, 산업통상자원부·지자체 인허가/보조금 발표
3. **대만 기업**: MOPS 공시, 월매출, 회사 IR, 과학단지·환경영향평가 자료
4. **일본 기업**: TDnet/EDINET, 회사 IR, 경제산업성 보조금 자료
5. **유럽 기업**: 회사 규제공시·IR, EU/회원국 보조금·경쟁당국 문서
6. **비상장 AI 기업**: 공식 블로그·파트너 발표·정부 조달 문서, 투자자 또는 거래 상대방 공시
7. **캐파 보완**: 환경영향평가, 건축 허가, 전력계통 접속, 장비 발주, 채용, 위성·현장 자료

### 4.3 발견용 검색 질의 팩

수집기는 회사명·별칭과 아래 키워드를 결합한다. 발견용 검색 결과는 원문이 아니므로 반드시 원출처로 이동한다.

```text
계약: agreement, contract, purchase commitment, supply, offtake,
      capacity reservation, strategic investment, funding, PPA,
      cloud credits, minimum purchase, take-or-pay

캐파: capacity, WSPM, wafer starts, ramp, expansion, cleanroom,
      tool move-in, utilization, yield, MW, GW, IT load,
      GPUs, accelerators, CoWoS, packaging capacity

마일스톤: roadmap, sample, qualification, tape-out, risk production,
          mass production, shipment, launch, delayed, postponed,
          groundbreaking, operational, commissioning
```

### 4.4 Twitter/X 기반 후보 시그널 수집

#### 4.4.1 도입 결론

`c_1006_subject_outline`(SignalForge)의 수집기를 참조하여 Twitter/X에서 Contracts, Capacity, Milestones 후보를 가져오는 것은 **가능하다**. 실제 참조 프로젝트에는 다음 자산이 구현되어 있다.

- `twscrape` 기반 계정별 타임라인 수집
- 계정 핸들→user ID 캐시로 불필요한 조회 감소
- UTC 작성 시각 컷오프와 KST ISO 8601 정규화
- P0/P1/P2 인플루언서 카탈로그 및 활성/비활성 관리
- 트윗 URL UNIQUE 인덱스와 `INSERT OR IGNORE` 멱등 적재
- 좋아요·리트윗·답글·조회수 메트릭 보존
- 트윗의 외부 링크 탐지와 연결 문서 제목·요약 보강

2026-10-10 점검 시점에 SignalForge 카탈로그에는 96개 계정(P0 43, P1 38, P2 15), `timeline_events`에는 Twitter 이벤트 987건이 존재했다. 따라서 새 수집기를 처음부터 만들기보다 **SignalForge를 발견 계층으로 재사용하고 Memory Claude에 검증 후보만 전달하는 어댑터 방식**을 우선한다.

다만 Twitter/X 게시물은 삭제·수정될 수 있고 원출처를 재인용하는 경우가 많으므로, 원칙적으로 S5 후보 신호다. 회사 공식 계정이 자사 발표를 직접 게시한 경우라도 링크된 공식 IR·공시·보도자료를 S1/S2 근거로 수집해야 한다. X 게시물 단독으로 운영 DB의 `contracts`, `fab_capacity`, `milestones`를 `VERIFIED` 상태로 만들 수 없다.

#### 4.4.2 권장 연동 구조

```text
[SignalForge 인플루언서 카탈로그]
              ↓
[Twitter/X 수집기: official API 우선, twscrape 대체]
              ↓
[SignalForge timeline.db / timeline_events]
              ↓ 읽기 전용 증분 어댑터
[Memory Claude twitter_signal_candidates]
              ↓ 엔티티·주장·외부 링크 추출
[공식 원문 탐색 및 99.raw 신규 보존]
              ↓ 검토·교차검증
[contracts / capacity / milestones]
```

두 프로젝트가 동일 Dropbox 경로에 있더라도 Memory Claude가 SignalForge DB에 직접 쓰지 않는다. SQLite WAL 파일 충돌과 프로젝트 간 결합을 피하기 위해 다음 우선순위를 적용한다.

1. SignalForge가 JSONL/SQLite export를 원자적으로 생성하고 Memory Claude가 가져오는 방식
2. SignalForge `timeline.db`를 read-only URI로 조회하는 증분 어댑터 방식
3. 향후 내부 HTTP API가 생기면 cursor 기반 API 방식

실시간 결합보다 **느슨한 결합(loose coupling)**을 유지하며, SignalForge 장애가 Memory Claude 운영 DB를 중단시키지 않아야 한다.

#### 4.4.3 수집 대상 계정 체계

기존 P0/P1/P2는 “수집 우선순위”이고 C1~C4는 “주장 신뢰도”이므로 혼용하지 않는다.

| 계정군 | 예시 | 수집 주기 | 기본 증거 등급 | 처리 원칙 |
| :--- | :--- | :---: | :---: | :--- |
| O0 공식 | 기업 IR, 정부기관, 규제기관, 거래소 | 15~60분 | S2 후보 | 링크된 공식 문서를 찾아 S1/S2로 승격 |
| P0 핵심 | 산업 전문 매체·핵심 애널리스트 | 1시간 | S4~S5 | 모든 계약·캐파 숫자를 검토 큐로 전송 |
| P1 분석 | 공급망·기업 전문 분석가 | 4~12시간 | S4~S5 | 독립 교차 출처가 있을 때 우선 검토 |
| P2 신호 | 매크로·루머·큐레이션 | 1일 | S5 | 급증·반복 신호만 검토 큐로 전송 |

Memory Claude용 카탈로그 뷰에는 다음 태그를 추가한다.

- `entity_ids`: 계정이 주로 다루는 36개 기업
- `signal_domains`: `CONTRACT`, `FAB_CAPACITY`, `DATACENTER`, `POWER`, `MILESTONE`
- `source_role`: `OFFICIAL`, `JOURNALIST`, `ANALYST`, `RESEARCH_FIRM`, `AGGREGATOR`, `ANONYMOUS`
- `languages`: `ko`, `en`, `zh`, `ja` 등
- `enabled_for_memory_claude`: 프로젝트별 수집 여부
- `false_positive_rate`, `verified_hit_rate`: 과거 후보의 실제 검증 성과

#### 4.4.4 Twitter 후보 이벤트 스키마

Twitter 원문을 바로 핵심 테이블에 넣지 않고 별도 staging 테이블에 저장한다.

```sql
CREATE TABLE twitter_signal_candidates (
    signal_id              TEXT PRIMARY KEY,
    tweet_id               TEXT NOT NULL UNIQUE,
    author_handle          TEXT NOT NULL,
    author_tier            TEXT,
    source_role            TEXT,
    tweet_url              TEXT NOT NULL,
    content                TEXT NOT NULL,
    published_at_utc       TEXT NOT NULL,
    collected_at_utc       TEXT NOT NULL,
    conversation_id        TEXT,
    referenced_tweet_id    TEXT,
    tweet_type             TEXT, -- ORIGINAL, REPLY, QUOTE, REPOST
    external_urls_json     TEXT,
    metrics_json           TEXT,
    entity_ids_json        TEXT,
    signal_types_json      TEXT,
    extracted_claims_json  TEXT,
    signal_score           REAL,
    source_project         TEXT DEFAULT 'c_1006_subject_outline',
    source_row_id          INTEGER,
    content_sha256         TEXT,
    availability_status    TEXT DEFAULT 'AVAILABLE',
    review_status          TEXT DEFAULT 'NEW',
    promoted_record_type   TEXT,
    promoted_record_id     TEXT,
    rejection_reason       TEXT,
    created_at             TEXT DEFAULT (datetime('now')),
    updated_at             TEXT DEFAULT (datetime('now'))
);
```

`extracted_claims_json`의 각 주장은 다음 구조를 갖는다.

```json
{
  "claim_type": "CAPACITY_TARGET",
  "subject_entity_id": "TSMC",
  "counterparty_entity_id": "NVIDIA",
  "value_low": 100000,
  "value_high": 120000,
  "unit": "WSPM",
  "target_period": "2026-Q4",
  "evidence_text": "트윗 안에서 해당 주장을 뒷받침하는 문장",
  "linked_url": "외부 원문 URL",
  "needs_official_source": true
}
```

#### 4.4.5 수집 및 증분 동기화 규칙

- 기본 폴링 주기: O0/P0 1시간, P1 6시간, P2 24시간
- 최초 소급: 최근 7일. 이후에는 `tweet_id`/`published_at` cursor 기반 증분 수집
- 장애 복구: 마지막 성공 cursor부터 재개하되 최근 6시간을 겹쳐 조회
- 중복 키: `tweet_id`가 1순위, canonical tweet URL과 content hash가 보조키
- 시간 저장: UTC 원본을 기준으로 저장하고 화면에서만 Asia/Tokyo/KST로 변환
- 수집량 제한: 계정별·주기별 상한과 지수 백오프 적용
- 스레드: 동일 `conversation_id`를 묶어 주장 문맥 보존
- 인용 트윗: 인용자와 원작성자를 모두 보존하고 같은 주장으로 중복 집계하지 않음
- 리포스트: 신규 증거가 아니므로 기본적으로 점수만 보강하고 별도 주장으로 승격하지 않음
- 삭제 게시물: DB에서 삭제하지 않고 `availability_status=DELETED_OR_UNAVAILABLE`로 표시
- 메트릭: 수집 시점 스냅샷이며 사실 신뢰도를 직접 높이지 않음

참조 프로젝트는 현재 시간 윈도우 내 게시물을 가져오지만, 장기 운영에서는 lookback만으로 누락을 완전히 막을 수 없다. Memory Claude 연동에는 계정별 `last_seen_tweet_id`, `last_published_at`, `last_success_at`을 가진 cursor 테이블이 필수다.

#### 4.4.6 후보 필터와 시그널 점수

후보는 다음 순서로 필터링한다.

1. 36개 기업명·티커·별칭 또는 핵심 제품/시설명 탐지
2. 계약·투자·캐파·마일스톤 동사와 수치·기간 표현 탐지
3. 외부 링크 도메인과 공식 원문 여부 판정
4. 기존 계약 family, capacity asset, milestone과 유사도 매칭
5. 점수 기준으로 자동 기각·보류·우선 검토 분류

권장 점수는 100점 만점이다.

| 요소 | 배점 | 설명 |
| :--- | :---: | :--- |
| 계정 역할·티어 | 20 | 공식/O0 및 검증 적중률이 높은 P0 우대 |
| 명명된 기업·자산 | 15 | entity/fab/product 명시 여부 |
| 정량성 | 20 | 금액, WSPM, MW, 물량, 일정 범위 포함 |
| 원문 링크 품질 | 20 | 공시·IR·정부 문서 링크 우대 |
| 독립 교차 신호 | 15 | 서로 다른 원출처 계정의 일치 |
| 최신성 | 10 | 신규 계약·상태 변경 우대 |

- 75점 이상: P0 검토 큐 및 공식 원문 자동 탐색
- 50~74점: 일반 검토 큐
- 30~49점: 관찰 상태, 반복 신호 발생 시 재평가
- 30점 미만: 보관하되 핵심 테이블 승격 대상에서 제외

인게이지먼트는 확산 정도를 나타낼 뿐 사실성을 보장하지 않으므로 별도 `attention_score`로 관리하고 `evidence_score`와 분리한다.

#### 4.4.7 공식 근거로의 승격 규칙

Twitter 후보가 운영 DB로 승격되려면 다음 단계를 통과해야 한다.

1. 트윗의 외부 링크를 canonical URL로 해소
2. 공식 IR·공시·정부자료·거래 상대방 발표 탐색
3. 원문을 `99.raw/`에 신규 저장하고 source manifest 생성
4. 숫자·날짜·당사자별 `evidence_locator` 확보
5. 기존 레코드와 중복·증액·정정 관계 판정
6. 검토자가 `VERIFIED` 또는 `REJECTED` 결정
7. 승격 시 `promoted_record_type/id`를 기록하여 역추적 가능하게 연결

예외적으로 공식 회사 계정이 링크 없이 제품 출시나 양산 시작을 직접 발표한 경우 게시물 자체를 S2 근거로 보존할 수 있다. 그러나 대규모 계약액, 캐파, 수율 등 투자 판단에 직접 쓰이는 정량값은 가능한 한 공시·IR·정부 원문 또는 거래 상대방의 독립 확인을 추가한다.

#### 4.4.8 접근 방식과 준수 요건

- 가능한 경우 Twitter/X 공식 API 또는 승인된 데이터 제공 방식을 우선한다.
- `twscrape`는 가용성과 정책 변화에 민감한 대체 백엔드로 격리한다.
- 접근제어·CAPTCHA·유료벽을 우회하는 구현을 Memory Claude의 필수 기능으로 두지 않는다.
- 플랫폼 이용약관, 로봇 정책, 저작권, 개인정보 및 계정 보안 요구를 준수한다.
- 봇 계정 비밀번호·세션·토큰은 저장소, 문서, 로그, 대시보드 응답에 평문으로 남기지 않는다.
- 게시물 전문 재배포를 최소화하고 분석에 필요한 메타데이터·근거 문장·원문 링크 중심으로 보존한다.
- 백엔드가 중단되면 알림을 남기고 재시도하되 차단을 회피하기 위한 공격적 계정 회전은 하지 않는다.

#### 4.4.9 Twitter 연동 인수 기준

- 동일 tweet를 반복 수집해도 후보 행이 중복되지 않음
- 수집 게시물의 100%에 `tweet_id`, 작성자, UTC 게시시각, 원문 URL 존재
- 후보 주장의 100%에 원문 게시물과 근거 문장 역추적 가능
- Twitter 단독 후보가 자동으로 `VERIFIED` 핵심 레코드가 되는 사례 0건
- 공식 원문으로 승격된 레코드의 100%에 `source_id`와 `evidence_locator` 존재
- 계정별 cursor로 중단 후 재개 시 테스트 구간 누락률 1% 미만
- P0 후보의 수집 후 검토 큐 도착시간 90분 이내
- 접근 토큰·비밀번호·세션이 로그나 산출물에 노출되는 사례 0건

---

## 5. 원천 보존 및 파일 규칙

`99.raw/`는 원본 금고이며 기존 파일을 수정·삭제하지 않는다. 신규 원문만 아래 규칙으로 추가한다.

```text
99.raw/
├── contracts/YYYY/ENTITY_A__ENTITY_B/
├── fab_capacity/YYYY/ENTITY/ASSET/
├── milestones/YYYY/ENTITY/
└── manifests/
```

권장 파일명:

```text
YYYY-MM-DD__publisher__entity__topic__document-type.ext
```

각 파일과 함께 manifest에 다음 메타데이터를 기록한다.

| 필드 | 필수 | 설명 |
| :--- | :---: | :--- |
| `source_id` | Y | 원문 고유 ID, 예: `SRC-20260910-NVDA-001` |
| `publisher` | Y | 발행 기관 또는 회사 |
| `title` | Y | 원문 제목 |
| `published_at` | Y | 원문 게시 시각/일자 |
| `accessed_at` | Y | 수집 시각 |
| `canonical_url` | Y | 원문 URL |
| `local_path` | Y | `99.raw/` 상대 경로 |
| `content_sha256` | Y | 중복·변조 확인용 해시 |
| `document_type` | Y | filing, IR, press_release, transcript, article 등 |
| `language` | Y | 원문 언어 |
| `retrieval_method` | Y | manual, RSS, API, crawler |
| `supersedes_source_id` | N | 정정·개정 문서 관계 |

유료 기사 전문이나 라이선스 제한 자료는 무단 복제하지 않고 허용 범위의 메타데이터·짧은 근거 메모·링크만 저장한다.

---

## 6. 데이터 모델 요건

### 6.1 공통 필드

세 데이터셋 모두 다음 공통 의미를 가져야 한다.

| 필드 | 규칙 |
| :--- | :--- |
| `as_of_date` | 해당 값이 유효하다고 관측된 기준일 |
| `announced_date` | 외부에 발표된 날짜 |
| `event_date`/`period` | 실제 발생일 또는 적용 기간 |
| `is_forecast` | 0=2026-Q2까지 확인된 실제 사건, 1=2026-Q3 이후 목표·가이던스·추정 |
| `confidence` | C1~C4, 주장별 신뢰도 |
| `source_id` | source manifest FK |
| `evidence_locator` | 페이지, 표, 문단, 타임코드 또는 HTML 앵커 |
| `extraction_method` | MANUAL, RULE, LLM_ASSISTED |
| `review_status` | NEW, REVIEWED, VERIFIED, REJECTED, SUPERSEDED |
| `created_at`, `updated_at` | 감사 추적 시각 |

**중요**: 판정 기준은 문서 게시일이 아니라 사건·수치의 대상 기간이다. 2026-Q2 이전 사건을 2026-Q3 이후 문서에서 재확인해도 `is_forecast=0`을 유지한다. 반대로 프로젝트 기준시점 규칙에 따라 대상 기간이 2026-Q3 이후인 사건·수치는 현재 달성 여부와 관계없이 `is_forecast=1`로 저장하고, 실제 달성 여부는 별도의 `status`와 `actual_date`로 표현한다.

### 6.2 Contracts 필수 요건

| 필드 | 필수 | 규칙 |
| :--- | :---: | :--- |
| `contract_id` | Y | 거래 단위의 안정적 ID |
| `contract_family_id` | Y | 최초 계약·증액·수정 계약 연결 |
| `buyer_id`, `seller_id` | Y | 36개 기업 마스터 FK; 방향이 불명확하면 역할 테이블 사용 |
| `contract_type` | Y | 표준 enum |
| `binding_level` | Y | BINDING, CONDITIONAL, NON_BINDING, REPORTED |
| `status` | Y | ANNOUNCED, SIGNED, ACTIVE, COMPLETED, CANCELLED, EXPIRED |
| `value_low_b`, `value_high_b` | N | USD Billion 범위. 단일 확정액은 두 값을 동일하게 저장 |
| `value_basis` | Y | DISCLOSED, MAXIMUM, ESTIMATED, DERIVED, UNDISCLOSED |
| `consideration_type` | Y | CASH, EQUITY, CREDITS, IN_KIND, MIXED |
| `quantity`, `quantity_unit` | N | GPU, wafer, HBM stack, MW 등 |
| `start_date`, `end_date` | N | 계약 효력·공급 기간 |
| `product_type`, `technology` | Y | GPU/HBM/FOUNDRY/CLOUD 등과 세대 정보 |
| `geography` | N | 적용 지역 |
| `source_id` | Y | 근거 원문 |

파생 필드인 `annualized_value_b`는 계약 총액을 단순 기간으로 나눈 값임을 명시하고, 실제 연도별 매출 인식액으로 사용하지 않는다.

### 6.3 Capacity 필수 요건

기존 `fab_capacity`와 `datacenter_capacity`를 유지하되 장기적으로 공통 `capacity_observations` 이력 테이블을 추가한다.

| 필드 | 필수 | 규칙 |
| :--- | :---: | :--- |
| `capacity_asset_id` | Y | 팹·라인·캠퍼스·장비군 고유 ID |
| `entity_id` | Y | 소유/운영 주체 |
| `asset_type` | Y | FAB, PACKAGING, DATACENTER, POWER, EQUIPMENT, NETWORK |
| `asset_name`, `location` | Y | 식별 가능한 시설명·지역 |
| `technology` | N | 공정 노드, 패키징 방식, 칩 세대 |
| `observation_date` | Y | 값의 기준일 |
| `capacity_value_low`, `capacity_value_high` | Y | 단일값이면 동일값 |
| `capacity_unit` | Y | WSPM, PACKAGES_MONTH, MW_IT, MW_GRID, GPU_COUNT 등 |
| `capacity_kind` | Y | NAMEPLATE, INSTALLED, QUALIFIED, EFFECTIVE, ALLOCATED |
| `utilization_pct`, `yield_pct` | N | 기준일과 출처가 있는 경우만 |
| `status` | Y | PLANNED, PERMITTED, CONSTRUCTION, TOOL_MOVE_IN, RAMPING, OPERATING, PAUSED, CANCELLED |
| `start_date`, `target_date`, `actual_date` | N | 착공·목표 가동·실제 가동 구분 |
| `capex_low_b`, `capex_high_b` | N | 시설 투자 범위 |
| `allocation_entity_id`, `allocation_pct` | N | 고객별 예약 캐파가 확인된 경우 |
| `is_forecast`, `confidence`, `source_id` | Y | 공통 규칙 적용 |

WSPM과 패키지 수량, 데이터센터 총전력과 IT Load는 직접 합산하지 않는다. 캐파 변환이 필요하면 별도 `capacity_conversion_assumptions`에 수율, die size, dies/wafer, package 구성, PUE를 저장한다.

### 6.4 Milestones 필수 요건

| 필드 | 필수 | 규칙 |
| :--- | :---: | :--- |
| `event_id` | Y | 사건 단위 ID |
| `entity_id` | Y | 주된 기업 |
| `event_type` | Y | 표준 카테고리 |
| `title`, `description` | Y | 사실과 해석을 분리하여 작성 |
| `announced_date` | N | 로드맵 발표일 |
| `target_date_start`, `target_date_end` | N | 예정 기간 범위 |
| `actual_date` | N | 달성 확인일 |
| `date_precision` | Y | DAY, MONTH, QUARTER, HALF, YEAR |
| `status` | Y | PLANNED, ON_TRACK, ACHIEVED, DELAYED, CANCELLED, SUPERSEDED |
| `impact_level` | Y | LOW, MEDIUM, HIGH, CRITICAL |
| `linked_contract_id` | N | 관련 계약 FK |
| `linked_capacity_asset_id` | N | 관련 캐파 자산 FK |
| `is_forecast`, `confidence`, `source_id` | Y | 공통 규칙 적용 |

예정 사건이 달성되면 기존 전망 행을 삭제하지 않는다. 동일 `event_id`의 상태 이력을 남기고 `actual_date`를 추가하며, 달성 사실을 확인한 출처를 별도 연결한다.

### 6.5 다중 출처 및 관계 테이블

한 레코드에 `source` 문자열 하나만 두는 현재 구조를 보완하기 위해 다음 논리 테이블이 필요하다.

```text
sources
record_sources(record_type, record_id, source_id, claim_type, evidence_locator)
contract_participants(contract_id, entity_id, role, share_pct)
contract_status_history(contract_id, status, effective_date, source_id)
capacity_observations(capacity_asset_id, observation_date, value, unit, kind, ...)
milestone_status_history(event_id, status, observed_date, source_id)
record_links(from_type, from_id, relation_type, to_type, to_id)
```

`record_links.relation_type` 예시는 `FUNDS`, `RESERVES_CAPACITY`, `ENABLES`, `REQUIRES`, `TRIGGERS_REVENUE`, `DELAYS`, `SUPERSEDES`다.

---

## 7. 추출·정규화·검증 절차

### 7.1 수집 파이프라인

```text
1. 발견(Feed/Search)
2. 원문 확보 및 99.raw 신규 저장
3. source manifest 등록·해시 계산
4. 후보 주장 추출
5. 엔티티·날짜·통화·단위 정규화
6. 중복/기존 계약 family 매칭
7. 출처 교차검증 및 confidence 부여
8. 검토용 staging 적재
9. 사람 또는 규칙 기반 승인
10. 운영 DB upsert 및 품질검사
11. 계약→캐파→마일스톤 연결 생성
12. 보고서·대시보드 재생성
```

LLM은 후보 추출과 문장 요약에 사용할 수 있으나, 숫자·날짜·당사자·상태는 원문 근거 위치와 함께 규칙 검증을 통과해야 한다. LLM 출력만으로 `VERIFIED` 상태를 만들 수 없다.

### 7.2 날짜 규칙

- 일자 확인: `YYYY-MM-DD`
- 월만 확인: 해당 월을 임의의 1일로 만들지 않고 `YYYY-MM` + `date_precision=MONTH`
- 분기만 확인: `YYYY-QN` + `date_precision=QUARTER`
- “2027년 하반기”: 시작 `2027-07-01`, 종료 `2027-12-31`, `date_precision=HALF`
- 회계분기와 달력분기는 별도 필드로 보존하고 임의 혼용하지 않는다.

### 7.3 금액·환율 규칙

- DB 표준 단위는 USD Billion이다.
- 원문 금액과 원통화는 반드시 별도 보존한다.
- 계약 발표 시점의 금액 환산은 발표일 환율 또는 명시된 거래 환율을 사용한다.
- 다년 계약의 최대 지출 한도는 확정 구매액과 구분한다.
- 클라우드 크레딧, 지분, 현금이 섞인 계약은 구성요소별 금액을 분리한다.
- 금액 비공개는 `NULL`이며 0이 아니다.

### 7.4 중복 판정

아래 항목이 유사하면 동일 거래 또는 사건 후보로 본다.

- 당사자 조합
- 제품·기술
- 발표일 ±30일
- 금액 ±10% 또는 동일 최대 한도
- 동일 원문을 재인용한 기사

중복 후보는 자동 병합하지 않고 `possible_duplicate_of`로 검토 큐에 보낸다. 증액 계약은 원계약과 family로 연결하되 증액분과 누적액을 구분한다.

### 7.5 정합성 검사

- 모든 `entity_id`가 `entities` 또는 승인된 외부 엔티티에 존재
- `value_low_b <= value_high_b`
- `start_date <= end_date`
- `actual_date`가 있으면 milestone 상태가 `ACHIEVED` 또는 후속 상태
- `is_forecast=0`인 미래 목표치 금지
- 확정 계약 총액 집계에서 `NON_BINDING`, `REPORTED`, `C1`, `UNDISCLOSED` 제외
- Capacity 합계는 동일 단위·동일 기준·상호 배타 자산만 허용
- `yield_pct`, `utilization_pct`, `allocation_pct`는 0~100
- 모든 VERIFIED 레코드는 S1~S3 원문과 `evidence_locator` 보유
- `raw_source` 파일 존재 여부와 SHA-256 일치

---

## 8. 운영 주기와 갱신 정책

| 주기 | 작업 |
| :--- | :--- |
| 매일 | 공식 보도자료·규제공시·정부 발표·주요 원취재 매체 후보 수집 |
| 주 1회 | 후보 중복 제거, S3/S4 교차검증, 계약 상태 변경 확인 |
| 실적 발표일 | 컨콜에서 수요, 예약, 캐파, 수율, 양산 일정 추출 |
| 월 1회 | 팹·데이터센터·전력 프로젝트의 허가/착공/가동 상태 점검 |
| 분기 1회 | 캐파 관측치 스냅샷, 전망→실제 롤포워드, 지연 여부 판정 |
| 연 1회 | 계약 잔여기간, 누적 투자액, 취소·만료, 출처 링크 상태 감사 |

상태가 바뀌면 이전 값을 덮어쓰지 않고 이력을 추가한다. 잘못된 레코드는 물리 삭제보다 `REJECTED` 또는 `SUPERSEDED` 처리하고 정정 사유를 기록한다.

---

## 9. 우선순위 수집 백로그

### P0: 기존 데이터 역검증

1. `contracts` 15건의 공식 원문·금액 구성·계약 상태 확인
2. `raw_source`가 비어 있는 계약과 마일스톤에 source manifest 연결
3. `업계 추정`, `Industry Rumors` 등 C3/C4가 과도하게 부여된 행 재평가
4. 2026-Q3 이후 사건의 `is_forecast=1` 일괄 검증
5. 팹 12건의 WSPM 기준일, 명목/유효 캐파, 수율 출처 확인
6. SignalForge P0/O0 계정에서 기존 DB 52개 레코드와 관련된 게시물·외부 원문 링크 역탐색

### P1: 핵심 밸류체인 자동 수집

1. AI 랩 ↔ 하이퍼스케일러: 투자, 클라우드 컴퓨트, 전용 칩 계약
2. 하이퍼스케일러 ↔ GPU/ASIC: 가속기 구매·커스텀 ASIC 개발
3. GPU/ASIC ↔ 메모리/파운드리: HBM, 웨이퍼, CoWoS 예약
4. 데이터센터 ↔ 전력: PPA, 원전·가스터빈, 계통 접속
5. 메모리 3사·TSMC: HBM4, 1c/1d, N2/A16, 패키징 램프

### P2: 산업 병목 확장

- ASML·AMAT·Lam·KLA 장비 백로그와 출하 캐파
- ASE·Amkor 첨단 패키징 증설
- Arista·Marvell·Coherent의 800G/1.6T 공급능력
- Vertiv·Eaton·GE Vernova·Schneider의 전력·냉각 수주잔고와 생산 증설

---

## 10. 구현 산출물

요건을 충족하기 위한 최소 산출물은 다음과 같다.

| 구분 | 산출물 |
| :--- | :--- |
| DDL | `scripts/add_intelligence_lineage.sql` |
| 수집 설정 | `data/source_registry.yaml`, `data/query_packs.yaml` |
| 원천 manifest | `99.raw/manifests/sources.jsonl` 또는 별도 SQLite staging DB |
| 수집기 | `scripts/collect_intelligence_sources.py` |
| Twitter 어댑터 | `scripts/import_signalforge_twitter.py` |
| Twitter cursor | `data/twitter_ingestion_state.json` 또는 staging DB의 cursor 테이블 |
| 추출기 | `scripts/extract_contracts_capacity_milestones.py` |
| 검증기 | `scripts/validate_intelligence_data.py` |
| 검토 큐 | `data/intelligence_review_queue.json` |
| 운영 가이드 | `docs/*_intelligence_pipeline_runbook.md` |
| 품질 리포트 | 출처 완결성, 검증 대기, 중복 후보, 전망 만기 리포트 |

DB 스키마 변경 전에는 반드시 DDL 파일을 먼저 작성하고 백업·행 수 사전 확인·트랜잭션 검증을 수행한다. 이 문서는 구현을 승인하는 문서가 아니라 구현 범위와 합격 기준을 정의하는 문서다.

---

## 11. 인수 기준(Acceptance Criteria)

### 11.1 레코드 품질

- 신규 VERIFIED 레코드의 **100%**가 로컬 원문 또는 적법한 메타데이터와 연결
- 신규 레코드의 **100%**가 `as_of_date`, `confidence`, `review_status` 보유
- 금액·물량·캐파 수치의 **100%**가 원단위, 표준단위, 산식 또는 직접 인용 위치 보유
- 2026-Q3 이후 대상 데이터의 `is_forecast=1` 준수율 **100%**
- 확정 데이터와 전망 데이터가 동일 집계에서 무표시로 혼합되는 사례 **0건**

### 11.2 파이프라인 품질

- 동일 수집 배치를 재실행해도 중복 행이 생성되지 않는 멱등성 보장
- 원천 해시 불일치, FK 오류, 비정상 범위, 단위 혼합을 적재 전에 차단
- 기존 DB의 대규모 UPDATE/DELETE 전 영향 행 수 출력
- 실패 시 트랜잭션 롤백 및 원천 파일 무변경
- 계약 하나에서 관련 캐파와 마일스톤으로 추적 가능한 링크를 핵심 P0 거래의 **80% 이상** 구축

### 11.3 분석 가능성

최종적으로 다음 질문에 SQL로 답할 수 있어야 한다.

1. 2027년에 효력이 있는 확정 HBM 계약의 구매자·공급자·금액 범위는 무엇인가?
2. 해당 계약을 충족할 HBM/패키징 캐파는 언제 얼마나 늘어나는가?
3. 고객 인증, 양산, 첫 출하 중 어느 마일스톤이 아직 전망이며 지연되었는가?
4. 계약 총액 중 공식 확정액과 시장 추정액은 각각 얼마인가?
5. 특정 캐파 수치가 어떤 원문과 산식에서 왔으며 이후 어떻게 수정되었는가?

---

## 12. 구현 단계 제안

### Phase 1 — 출처와 기존값 정비

- source manifest와 다중 출처 연결 테이블 추가
- 기존 52개 레코드(계약 15 + 캐파 12 + 마일스톤 25) 전수 품질 감사
- C1~C4 재분류, `LEGACY_UNVERIFIED` 큐 생성

### Phase 2 — 이력형 모델 도입

- 계약 상태 이력, 캐파 관측치, 마일스톤 상태 이력 추가
- 날짜 범위·금액 범위·원통화 보존
- 계약-캐파-마일스톤 관계 링크 생성

### Phase 3 — 반자동 수집

- 공식 공시·IR·정부 발표의 RSS/API/검색 기반 발견 자동화
- SignalForge Twitter export/read-only adapter와 `twitter_signal_candidates` staging 도입
- 계정별 cursor, 스레드·인용 관계, 외부 원문 승격 흐름 구현
- 원문 저장, 해시, 메타데이터 생성 자동화
- 추출 결과는 staging과 검토 큐까지만 자동 진행

### Phase 4 — 분석·알림

- 신규 대형 계약, 계약 증액·취소, 캐파 지연, 양산 달성 알림
- 전망 만기 후 실제 달성 여부 자동 점검
- 2026~2028 공급부족/과잉 시나리오에 검증된 캐파 관측치만 투입

---

## 13. 데이터 신뢰도 고지

현재 DB의 계약·캐파·마일스톤에는 공식 원문이 직접 연결되지 않은 값과 업계 추정치가 포함되어 있다. 따라서 기존 합계와 미래 공급 전망은 방향성 탐색에는 사용할 수 있지만, 정밀 투자 판단이나 확정 계약 규모로 인용하기 전에 P0 역검증이 필요하다.

향후 모든 보고서는 최소한 다음을 함께 표시해야 한다.

- 데이터 기준일
- 확정/전망 구분
- 공식/추정 금액 구분
- 신뢰도(C1~C4)
- 원문 링크 또는 `99.raw/` 근거 경로
- 범위값과 핵심 산식

이 원칙을 지키면 Memory Claude는 단순 뉴스 아카이브가 아니라 **계약이 어떤 물리적 캐파를 예약하고, 어떤 전략적 마일스톤을 통해 매출로 전환되는지 추적하는 감사 가능한 인텔리전스 시스템**으로 발전할 수 있다.
