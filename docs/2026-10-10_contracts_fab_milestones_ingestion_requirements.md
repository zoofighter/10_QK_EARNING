# [요건정의서] 대규모 계약·팹 캐파·전략적 이정표 수집 및 통합 파이프라인
**문서 버전**: v1.0.0  
**작성 일자**: 2026-10-10  
**프로젝트 기준 시점**: 2026-09-10  
**프로젝트 코드명**: `b_0910_memory_claude`  
**대상 도메인**: 
1. 대규모 공급·투자 계약 (`contracts`)
2. 팹 증설 및 생산 능력 (`fab_capacity`)
3. 전략적 기술·공급망 이정표 (`milestones`)

---

## 1. 추진 배경 및 요건 정의 목적

### 1.1 현상 진단 (AS-IS)
`Memory Claude` 프로젝트는 현재 8대 레이어(L1~L8) 36개 기업 마스터 체계와 657건의 분기별 정량 실적(`earnings_reports`)을 확보하여 탄탄한 재무 시계열을 구축했습니다.  
그러나 **거시 자본 흐름(Sankey) 및 2026~2028년 업황 슈퍼사이클 예측의 핵심 동력**이 되는 비정형·준정형 이벤트 데이터는 심각한 불균형 상태에 놓여 있습니다.

| 도메인 | DB 테이블 | 현재 건수 | 현행 상태 및 한계점 |
| :--- | :--- | :---: | :--- |
| **대규모 계약** | `contracts` | 15건 ($877B) | 단편적 메가딜 위주 적재, 중기 공급계약 결측, 자동 수집 부재 |
| **팹 캐파** | `fab_capacity` | 12건 | TSMC, SK하이닉스, 삼성, 마이크론 위주(파운드리/메모리 편중), 장비/패키징 거점 누락 |
| **전략 이정표** | `milestones` | 25건 | 과거 제품 출시(2022~2024) 위주, 2026~2028 미래 변곡점 파이프라인 미흡 |

### 1.2 추진 목적 (TO-BE)
1. **재무 실적과 물리적 인프라의 인과 고리 완성**:
   $$\text{Capex 집행} \longrightarrow \text{공급·투자 계약 체결} \longrightarrow \text{Fab 증설 및 캐파 가동} \longrightarrow \text{제품 출하 및 매출 인식}$$
2. **선제적 데이터 수집 파이프라인 확립**:
   SEC 8-K/10-K, 관세청 통관, 글로벌 반도체 전문지, IR 컨퍼런스콜에서 발생하는 정성·정량 정보를 체계적인 절차(수집 $\to$ 파싱/정규화 $\to$ 검증/적재 $\to$ 시뮬레이터 연동)로 파이프라인화.
3. **자매 프로젝트(`b_0917_10_QK_EARNING`)와의 유기적 통합 기반 마련**:
   10_QK_EARNING의 FTS5 전문 검색 및 수집 파이프라인과 연계하여 실시간성 및 신뢰도 확보.

---

## 2. 3대 핵심 도메인별 수집 요건 정의

```
┌────────────────────────────────────────────────────────────────────────┐
│                        3대 도메인 수집 아키텍처                          │
└───────┬────────────────────────┬───────────────────────────────┬───────┘
        │                        │                               │
 ┌──────▼──────┐          ┌──────▼──────┐                 ┌──────▼──────┐
 │  CONTRACTS  │          │ FAB CAPACITY│                 │  MILESTONES │
 │ 대규모 계약 │          │  팹 증설    │                 │ 전략적 변곡점│
 └──────┬──────┘          └──────┬──────┘                 └──────┬──────┘
        │                        │                               │
        ├─ SEC Form 8-K / 10-Q   ├─ IR 프레젠테이션/Fact Sheet    ├─ GTC / Computex 키노트
        ├─ 하이퍼스케일러 PPA    ├─ CHIPS Act 공시 보고서        ├─ 어닝콜 질의응답 (Q&A)
        ├─ 전문지 (The Info 등)  ├─ SemiAnalysis, TrendForce     ├─ 로드맵 공식 발표
        └─ 파트너십 프레스릴리즈 └─ 각 사 이사회 투자 의결        └─ 규제·독점 심사 동향
```

### 2.1 도메인 1: 대규모 공급·투자 계약 (`contracts`)

#### (1) 수집 대상 및 범위
- **계약 규모**: 최소 추정액 **$1.0B (10억 달러) 이상** 메가 계약 원칙 (단, HBM4 독점 공급 및 차세대 패키징 파일럿 계약은 $500M 이상도 포함)
- **계약 유형 (Contract Types)**:
  - `SUPPLY`: 가속기(GPU/ASIC), 메모리(HBM3E/HBM4/서버DRAM), 파운드리 웨이퍼, 광트랜시버 공급
  - `INVESTMENT`: 빅테크 $\to$ AI 랩 지분 투자, 전환사채, 공동 펀딩
  - `INFRA_COMPUTE`: 장기 클라우드 인프라 용량 확약 (Cloud Capacity Commitment, Compute PPA)
  - `PARTNERSHIP`: 차세대 아키텍처 공동 개발 (예: OpenAI-Broadcom 커스텀 ASIC, Apple-TSMC 선단공정 협력)
  - `POWER_PPA`: 데이터센터 전력 장기 공급계약 (원전 PPA, SMR 장기구매계약 등)

#### (2) 데이터 소스 채널
1. **공식 1차 공시 (C4 등급)**:
   - **SEC Form 8-K** (Item 1.01: Entry into a Material Definitive Agreement)
   - **SEC Form 10-Q / 10-K** 내 "Commitments and Contingencies" 및 "Subsequent Events" 주석
2. **기업 공식 IR (C4 등급)**:
   - 각 사 IR Press Release (예: Amazon의 Anthropic 투자, Microsoft의 OpenAI 파트너십)
3. **전문 언론 및 탐사 리서치 (C3 등급)**:
   - The Information, Bloomberg Tech, Reuters, SemiAnalysis, Edgewater Research
4. **사용자 수기 메모 및 북마크**:
   - `99.raw/manual.md`, `99.raw/contracts/bookmarks_index.json`

#### (3) 수집 추출 필드 요건
| 필드명 | 데이터 타입 | 필수 여부 | 수집 및 정규화 규칙 |
| :--- | :--- | :---: | :--- |
| `contract_id` | TEXT | 필수 | 규칙: `CON-{YEAR}-{BUYER_ID}-{SELLER_ID}-{TYPE}` |
| `buyer_id` | TEXT | 필수 | `entities.entity_id` 외래키 참조 (대문자 스네이크) |
| `seller_id` | TEXT | 필수 | `entities.entity_id` 외래키 참조 |
| `contract_type` | TEXT | 필수 | `SUPPLY`, `INVESTMENT`, `INFRA_COMPUTE`, `PARTNERSHIP`, `POWER_PPA` |
| `value_b` | REAL | 선택 | **USD Billion 고정**. 미공개 시 NULL 유지하되 비고에 추정치 기록 |
| `product_type` | TEXT | 필수 | `HBM`, `GPU`, `CUSTOM_ASIC`, `FOUNDRY`, `CLOUD_COMPUTE`, `POWER` |
| `announced_date`| TEXT | 필수 | `YYYY-MM-DD` 또는 `YYYY-QN` 표기 |
| `start_date` / `end_date` | TEXT | 선택 | 계약 이행 개시 및 만료 시점 (`YYYY-QN`) |
| `confidence` | TEXT | 필수 | `C1`(루머) ~ `C4`(공식 공시) 표준 체계 적용 |
| `source` / `raw_source` | TEXT | 필수 | 기사 제목, 공시 고유번호 또는 `99.raw/contracts/` 경로 |

---

### 2.2 도메인 2: 팹 증설 및 생산 능력 (`fab_capacity`)

#### (1) 수집 대상 및 범위
- **대상 레이어**: L4(파운드리/장비/패키징), L5(메모리/스토리지), L3(인텔 등 자체 팹 보유사)
- **추적 대상 공정**:
  - **선단 로직 공정**: TSMC N3, N2, A16 / Intel 18A / Samsung SF2, SF1.4
  - **첨단 패키징**: TSMC CoWoS-S/L, Intel Foveros, ASE/Amkor 어드밴스드 SiP
  - **HBM 및 선단 DRAM**: SK하이닉스 1b/1c/1d nm, 삼성전자 평택 P3/P4 1c nm, 마이크론 1-beta/1-gamma

#### (2) 데이터 소스 채널
1. **정기 실적 발표 자료 (C4 등급)**:
   - TSMC Quarterly Management Report (월별 웨이퍼 투입량, 공정별 매출 비중, Capex 가이던스)
   - SK하이닉스 / 삼성전자 실적 IR 보도자료 및 Q&A 트랜스크립트 (장비 반입 및 램프업 일정)
2. **정부 및 규제 공시 (C4 등급)**:
   - 미국 상무부 CHIPS Act 프로그램 공시 (애리조나 팹, 테일러 팹 보조금 지급 마일스톤)
   - 한국 산업통상자원부 국가첨단전략산업 특화단지 인프라 지원 보고서 (용인 클러스터)
3. **전문 리서치 기관 데이터 (C3 등급)**:
   - TrendForce, SEMI (World Fab Forecast), Yole Intelligence, TechInsights
4. **장비사 출하 및 수주 보고서 (C3 등급)**:
   - ASML 분기 수주잔고(Backlog) 및 EUV/High-NA EUV 인도 현황

#### (3) 수집 추출 필드 요건
| 필드명 | 데이터 타입 | 필수 여부 | 수집 및 정규화 규칙 |
| :--- | :--- | :---: | :--- |
| `fab_id` | TEXT | 필수 | 규칙: `FAB-{ENTITY_ID}-{FAB_NAME_CODE}` |
| `entity_id` | TEXT | 필수 | 운영 주체 (`TSMC`, `SK_HYNIX`, `SAMSUNG`, `MICRON`, `INTEL`) |
| `fab_name` | TEXT | 필수 | 공식 명칭 (예: `TSMC Fab 20`, `SK하이닉스 청주 M15X`) |
| `process_node` | TEXT | 필수 | 주력 생산 공정 노드 (예: `2nm (N2 / A16)`, `1c nm HBM4`) |
| `fab_type` | TEXT | 필수 | `FAB` (전공정), `PACKAGING` (후공정/CoWoS), `R&D` |
| `wspm_current` | REAL | 필수 | 현재 월 생산 능력 (단위: WSPM, 장/월) |
| `wspm_target` | REAL | 필수 | 최종 증설 목표 캐파 (단위: WSPM) |
| `ramp_start_date` / `ramp_end_date` | TEXT | 선택 | 램프업 착수 및 양산 완료 목표 분기 (`YYYY-QN`) |
| `capex_invested_b`| REAL | 선택 | 누적 투입/계획 총 투자액 (**USD Billion**) |
| `utilization_pct` | REAL | 선택 | 분기별 가동률 (%) |
| `yield_pct` | REAL | 선택 | 양품 수율 추정치 (%) |
| `status` | TEXT | 필수 | `PLANNED`, `CONSTRUCTION`, `RAMP_UP`, `OPERATING`, `SUSPENDED` |
| `key_customers` | TEXT | 선택 | 해당 팹 생산 물량을 선점한 주요 고객사 목록 |

---

### 2.3 도메인 3: 전략적 이정표 (`milestones`)

#### (1) 수집 대상 및 범위
- **정의**: AI 밸류체인의 수급 불균형, 기술 패러다임 전환, 경쟁 구도에 구조적 충격을 주는 핵심 사건
- **이벤트 카테고리 (Category)**:
  - `PRODUCT_LAUNCH`: 차세대 가속기/메모리/네트워크 칩 출시 (예: NVIDIA Rubin, B200 Ultra, HBM4)
  - `FAB_MILESTONE`: 팹 착공, 클린룸 준공, First Tool-in(장비 반입), 양산 개시
  - `PARTNERSHIP`: 독점 라이선스, 얼라이언스 결성, 합작법인(JV) 설립
  - `REGULATION`: 대중국 수출 통제, 독점 규제 심사, 관세 정책 변화
  - `SCENARIO_SIGNAL`: 전력 병목 발생, 패키징 쇼티지 심화, 대체 아키텍처 부상 등 시나리오 트리거

#### (2) 데이터 소스 채널
1. **빅테크 연례 기술 컨퍼런스 (C4 등급)**:
   - NVIDIA GTC, Computex, Hot Chips, TSMC Technology Symposium, Intel Vision
2. **어닝콜 트랜스크립트 질의응답 (C4 등급)**:
   - Motley Fool, Seeking Alpha 등에서 수집한 CEO/CFO의 차세대 로드맵 발언
3. **특허 및 논문, 오픈소스 릴리즈 (C3 등급)**:
   - arXiv AI 논문, Frontier Lab 공식 기술 리포트

#### (3) 수집 추출 필드 요건
| 필드명 | 데이터 타입 | 필수 여부 | 수집 및 정규화 규칙 |
| :--- | :--- | :---: | :--- |
| `event_id` | TEXT | 필수 | 규칙: `MS-{YEAR}-{SEQ}` (예: `MS-2026-05`) |
| `entity_id` | TEXT | 필수 | 핵심 주체 기업 (`entities.entity_id`) |
| `event_date` | TEXT | 필수 | 사건 발생일 또는 예정일 (`YYYY-MM-DD` 또는 `YYYY-QN`) |
| `category` | TEXT | 필수 | 상기 정의된 카테고리 분류 표준 준수 |
| `impact_level` | TEXT | 필수 | `LOW`, `MEDIUM`, `HIGH`, `CRITICAL` (4단계) |
| `is_forecast` | INTEGER | 필수 | **타임라인 원칙 엄수**: 2026-Q2 이전 = 0, 2026-Q3 이후 = 1 |
| `confidence` | TEXT | 필수 | 신뢰 등급 (`C1`~`C4`) |
| `description` | TEXT | 필수 | 사건 개요 및 밸류체인 파급 효과 서술 |
| `source` | TEXT | 필수 | 출처 표기 (보도자료명, 컨퍼런스명 등) |

---

## 3. 엔드투엔드(End-to-End) 수집 및 가공 파이프라인 설계

```mermaid
flowchart TD
    subgraph SOURCES ["1. 멀티채널 원천 데이터 수집"]
        S1["SEC EDGAR (8-K / 10-Q / 10-K)"]
        S2["글로벌 테크 미디어 & 전문 리서치"]
        S3["각 사 공식 IR 프레스릴리즈"]
        S4["99.raw/ 수기 메모 & 북마크"]
    end

    subgraph INGESTION ["2. 적재 및 1차 파싱 계층"]
        P1["자동 다운로더 & 크롤러<br/>(scripts/fetch_*.py)"]
        P2["99.raw/ 디렉토리 저장<br/>(contracts/, fab_capacity/, milestones/)"]
    end

    subgraph EXTRACTION ["3. AI 구조화 및 정규화 추출 엔진"]
        E1["LLM 정보 추출기<br/>• Entity 매핑 (36개사 표준)<br/>• 통화/단위 변환 (B_USD, WSPM)<br/>• 시점 분기 태깅 (YYYY-QN)"]
        E2["타임라인 검증기<br/>• 2026-Q2 기준 is_forecast 판정<br/>• C1~C4 신뢰도 채점"]
    end

    subgraph REPOSITORY ["4. 통합 저장소 및 정합성 검증"]
        DB[("SQLite: memory_claude.db")]
        T1["contracts 테이블"]
        T2["fab_capacity 테이블"]
        T3["milestones 테이블"]
    end

```mermaid
flowchart TD
    subgraph SOURCES ["1. 멀티채널 원천 데이터 수집"]
        S1["SEC EDGAR (8-K / 10-Q / 10-K)"]
        S2["𝕏/Twitter 인플루언서 피드<br/>(c_1006 SignalForge twscrape)"]
        S3["글로벌 테크 미디어 & 전문 리서치"]
        S4["각 사 공식 IR 프레스릴리즈"]
        S5["99.raw/ 수기 메모 & 북마크"]
    end

    subgraph INGESTION ["2. 적재 및 1차 파싱 계층"]
        P1["자동 다운로더 & 크롤러<br/>(scripts/fetch_*.py)"]
        P2["𝕏 시그널 & 첨부링크 스텔스 수집<br/>(Scrapling / Camoufox)"]
        P3["99.raw/ 디렉토리 저장<br/>(contracts/, fab_capacity/, milestones/)"]
    end

    subgraph EXTRACTION ["3. AI 구조화 및 정규화 추출 엔진"]
        E1["LLM 정보 추출기<br/>• Entity 매핑 (36개사 표준)<br/>• 통화/단위 변환 (B_USD, WSPM)<br/>• 시점 분기 태깅 (YYYY-QN)"]
        E2["타임라인 검증기<br/>• 2026-Q2 기준 is_forecast 판정<br/>• C1~C4 신뢰도 채점"]
    end

    subgraph REPOSITORY ["4. 통합 저장소 및 정합성 검증"]
        DB[("SQLite: memory_claude.db")]
        T1["contracts 테이블"]
        T2["fab_capacity 테이블"]
        T3["milestones 테이블"]
    end

    subgraph CONSUMPTION ["5. 분석 모델 및 대시보드 표출"]
        C1["거시 자본 흐름 (Sankey Diagram)"]
        C2["HBM/CoWoS 수급 밸런스 시뮬레이터"]
        C3["Capex 흡수 워터폴 차트"]
        C4["통합 타임라인 & 원페이저 뷰어"]
    end

    SOURCES --> INGESTION
    INGESTION --> EXTRACTION
    EXTRACTION --> REPOSITORY
    DB --- T1 & T2 & T3
    REPOSITORY --> CONSUMPTION
```

### 3.1 단계별 파이프라인 상세

#### Step 1: 수집 (Ingestion)
- **SEC 8-K 수집기 (`scripts/collect_sec_8k.py`)**:
  - EDGAR API 및 RSS 피드를 통해 36개 상장사의 Form 8-K 중 Item 1.01(중대 계약) 및 Item 8.01(기타 주요 사건) 자동 모니터링.
- **𝕏/Twitter 실시간 시그널 수집기 (`c_1006_subject_outline` 연계)**:
  - 222개 마스터 인플루언서 풀(`config/influencers.yaml`) 중 반도체·HBM·빅테크 전담 인플루언서 트윗 모니터링.
  - 첨부 링크 기사(Substack, SemiAnalysis, 대만/미국 언론사)를 Scrapling 스텔스 스크래퍼로 원문 추출 후 `99.raw/`에 아카이빙.
- **뉴스/전문지 수집기 (`scripts/sync_chrome_bookmarks.py` 고도화)**:
  - 북마크 및 반도체 전문 RSS 피드 파싱 $\to$ 본문 HTML을 `99.raw/contracts/`, `99.raw/fab_capacity/`에 보존.
- **수기 메모 감지**:
  - `99.raw/manual.md`에 기재된 메모(예: "인텔 하이닉스 계약")를 감지하여 큐에 등록.

#### Step 2: 추출 및 정규화 (Extraction & Normalization)
- **엔티티 매핑**: 기사/공시/트윗 내 언급된 비공식 사명(예: "Google Cloud", "AWS", "Hynix")을 표준 마스터 `entity_id`(`GOOGLE`, `AMAZON`, `SK_HYNIX`)로 자동 치환.
- **통화 및 단위 환산**:
  - 통화: KRW, TWD, EUR 등은 발표 분기 평균 환율을 적용하여 **USD Billion (`value_b`)**으로 변환.
  - 생산 단위: 웨이퍼 월 생산량은 **WSPM**, 전력은 **MW/GW** 단위로 통일.
- **타임라인 플래그 판정 (`is_forecast`)**:
  - 2026-Q2 이전 사건 $\to$ `is_forecast = 0`
  - 2026-Q3 이후 계획/전망치 $\to$ `is_forecast = 1`

#### Step 3: 검증 및 적재 (Verification & DB Load)
- **Primary Key 및 중복 방지**:
  - 신규 계약/팹/마일스톤 등록 시 기존 레코드와 `(buyer_id, seller_id, announced_date)` 또는 `(entity_id, fab_name)` 대조.
- **신뢰도 등급 부여**:
  - 공시 원문 첨부 시 `C4`, 유력 언론/인플루언서 P0 계정 단독 보도 시 `C3`, 단순 루머/미확인 트윗 `C1~C2`.

#### Step 4: 시뮬레이션 모델 트리거 (Trigger)
- 신규 데이터 적재 완료 시 연결된 4대 분석 파이프라인 자동 갱신:
  1. `export_capex_waterfall.py`: 계약액 반영 자본 이동 재계산
  2. `generate_hbm_market_balance.py`: HBM 팹 WSPM 증설 및 출하 일정 재계산
  3. `generate_network_graph.py`: 기업 간 계약 노드 및 링크 두께 업데이트
  4. `generate_entity_one_pager.py`: 개별 기업의 계약/캐파/마일스톤 섹션 갱신

---

### 3.2 [신규] 𝕏/Twitter 기반 준실시간 인텔리전스 인제스천 설계 (`c_1006_subject_outline` 연계)

자매 프로젝트 `c_1006_subject_outline (SignalForge)`의 핵심 수집 자산을 재사용하여, 글로벌 반도체 밸류체인의 속보 및 공급망 루머를 즉각 탐지하는 세부 요건을 수립합니다.

#### (1) `c_1006` 핵심 아키텍처 재사용 방안
1. **`twscrape` 독립 계정 풀**:
   - `c_1006_subject_outline/src/collectors/twitter_fetcher.py`의 구조를 도입하여, 별도 유료 X API 없이 계정 풀(`data/accounts.db`)을 활용한 분산 비동기 수집.
2. **반도체·AI 밸류체인 특화 타깃 인플루언서 필터링 (Top Tier)**:
   - `config/influencers.yaml` 내 222개 계정 중 Memory Claude 8대 레이어와 직결되는 계정을 우선 타깃팅:
     - **L3/L4/L5 반도체 전문 분석가**: `@dylan522p` (SemiAnalysis), `@trendforce`, `@jukan05` (한국/대만 HBM 속보), `@dnystedt` (대만 공급망/TSMC), `@SemiconductorsX`, `@aleabitoreddit`
     - **L2 하이퍼스케일러 & AI 인프라**: `@StockSavvyShay`, `@TheInformation`, `@BradGerstner`
3. **`Scrapling` 기반 첨부 기사 본문 자동 획득**:
   - 트윗 본문뿐 아니라 트윗에 링크된 비공개/유료/차단 기사(Substack, SemiAnalysis, 외신)를 `StealthLinkScraper`로 Cloudflare 및 403 차단을 우회하여 수집.

#### (2) 𝕏/Twitter $\to$ Memory Claude 3대 도메인 자동 변환 필터링 규칙

트윗은 노이즈가 많으므로, LLM 필터링 프롬프트에 **3대 도메인 감지 시그니처**를 정의하여 정제합니다:

```text
[트윗 수집 (twscrape)]
        │
        ▼
[1차 키워드 필터링 (Fast Path)]
 • Contracts: ($B OR contract OR supply OR deal OR procurement OR PPA OR capacity commitment)
 • Fab Capacity: (wspm OR fab OR cleanroom OR wafer OR cowos OR packaging OR yield OR ramp)
 • Milestones: (tape-out OR launch OR mass production OR sample OR qual OR delay OR cancel)
        │
        ▼
[2차 본문 스크래핑 & LLM 구조화 (Extraction Agent)]
 • Entity 추출 (NVIDIA, TSMC, SK_HYNIX 등 36개사 매핑)
 • 정량 수치 정규화 (B_USD, WSPM)
 • 3대 도메인 분류 (contracts / fab_capacity / milestones)
        │
        ▼
[3차 신뢰도 채점 및 임시 격리 (Staging Table)]
 • P0 인플루언서 + 1차 출처 링크 존재 ──► C3 등급 ──► 검증 큐 등록
 • 단순 루머 / 출처 불명 ───────────────► C1~C2 등급 ──► milestones(category='SCENARIO_SIGNAL') 기록
```

#### (3) 트위터 데이터 격리 및 신뢰도 관리 정책
- 트위터 기반 데이터는 **초기 등록 시 기본 신뢰도를 `C2`~`C3`**로 부여합니다.
- 공시(C4)가 나오기 전까지는 `milestones` 테이블의 `category = 'SCENARIO_SIGNAL'`로 기록하거나 `contracts` 테이블의 비고에 `[Twitter Intelligence: @계정명]`을 명시하여 확정 공시 데이터와의 혼선을 방지합니다.

---

## 4. 즉시 실행 우선순위 및 실천 과제 (Action Plan)

현재 시스템에서 식별된 가장 시급한 보강 대상을 우선순위화합니다:

### P0 (최우선 실행 과제: 1~2일 내 완료)
1. **`99.raw/manual.md` 기재 건 즉시 적재**:
   - `인텔 - SK하이닉스 낸드/솔리다임 계약` 검증 후 `contracts` 테이블 추가
2. **누락된 팹 핵심 기지 6건 보강**:
   - `인텔 Fab 52/62 (애리조나 18A)`
   - `삼성전자 평택 P4 (HBM4/2nm)`
   - `마이크론 뉴욕 메가팹`
   - `TSMC 독일 드레스덴 팹 (ESMC)`
   - `ASML 벨트호벤 High-NA 제조 센터`
   - `Amkor 애리조나 첨단 패키징 팹`
3. **핵심 메가 계약 5건 보강**:
   - `OpenAI - Oracle - Microsoft 클라우드 컴퓨팅 계약 ($30B+)`
   - `Apple - TSMC 2nm 독점 초도물량 공급 계약 ($15B+)`
   - `Meta - Vertiv 데이터센터 냉각 솔루션 대규모 공급계약 ($3B+)`
   - `Amazon - Talen Energy 원자력 데이터센터 PPA 계약`
   - `Google - Kairos Power 소형모듈원전(SMR) 전력구매계약`

### P1 (파이프라인 자동화: 1주일 내 완료)
1. **`c_1006_subject_outline` 연계 트위터 수집 브릿지 구축 (`scripts/fetch_twitter_signals.py`)**:
   - `c_1006`의 `TwitterFetcher`와 `StealthLinkScraper`를 모듈 또는 서브프로세스로 호출하여 36개 기업 관련 트윗 필터링 및 `99.raw/` 수집 연동
2. **`scripts/populate_contracts.py` 단독 스크립트 작성**:
   - `contracts` 테이블 전용 시드/적재/검증 스크립트 모듈화
3. **`scripts/generate_*.py` 빈 파일 복원**:
   - 계약·캐파 데이터를 화면에 렌더링하는 `generate_hbm_market_balance.py`, `generate_network_graph.py` 복구
4. **`b_0917_10_QK_EARNING` 공시 FTS 수집기 연계 테스트**:
   - 10-K/Q 주석에서 Material Contract 키워드 자동 추출 실험

---

## 5. 결론 및 향후 전망

대규모 계약(`contracts`), 팹 캐파(`fab_capacity`), 전략적 이정표(`milestones`)는 단순한 텍스트 데이터가 아니라,  
**"빅테크의 천문학적 AI Capex가 어떤 물리적 공장과 어떤 핵심 부품으로 흡수되어 최종 기업의 이익으로 결실을 맺는가"를 설명하는 인과관계의 핵심 매개변수**입니다.

여기에 `c_1006_subject_outline`의 **𝕏/Twitter 인플루언서 및 스텔스 링크 수집 엔진**을 결합함으로써, 공식 공시보다 며칠~몇 주 앞서 시장에 회자되는 공급망 계약 루머, 팹 램프업 지연, 차세대 가속기 테이프아웃 정보를 선제적으로 감지할 수 있게 됩니다.

본 요건정의서에 정의된 멀티채널 수집 체계를 구축함으로써, `Memory Claude`는 정적 재무 열람 시스템을 넘어 **2026~2028년 글로벌 AI 반도체 슈퍼사이클을 가장 빠르고 정밀하게 예측하는 동적 인텔리전스 엔진**으로 완성될 것입니다.

