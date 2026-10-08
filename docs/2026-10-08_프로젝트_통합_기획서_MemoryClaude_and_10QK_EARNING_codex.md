# [통합 기획서] Memory Claude × 10_QK_EARNING 시스템 통합 전략 및 로드맵

**문서 작성일**: 2026-10-08  
**대상 시스템**: 
- `b_0910_memory_claude` (AI 반도체 밸류체인 자본·기술 흐름 및 슈퍼사이클 예측 시스템)
- `b_0917_10_QK_EARNING` (AI 반도체 공시 SEC 10-K/Q 및 관세청 10일 선행통관 지표 모니터링 시스템)

---

## 1. 통합 배경 및 목적

두 시스템은 모두 **동일한 AI 반도체 밸류체인(8대 레이어, 36개 핵심 기업)**을 분석 대상으로 삼고 있으나, 접근 방식과 아키텍처에서 상호보완적인 명확한 양 날개 구조를 띠고 있습니다.

- **b_0910_memory_claude (Top-Down)**: 거시 자본 흐름(Sankey), HBM/CoWoS 수급 밸런스, 데이터센터 전력 캐파(GW), 메가 계약 추적, 2026~2028 중장기 사이클 예측 시뮬레이터
- **b_0917_10_QK_EARNING (Bottom-Up)**: Flask 기반 모듈형 REST API, SEC EDGAR 공시(10-K/Q) 자동 수집 및 FTS5 전문 검색, 한국 관세청 10일 주기(1/11/21일) 반도체 통관 수출 실적, 주가/GPU 가격 크롤링

본 통합의 목적은 두 프로젝트를 결합하여 **"실시간 선행 데이터(공시·통관)로 구동되는 동적 AI 반도체 밸류체인 자본·수급 시뮬레이션 플랫폼"**을 완성하는 것입니다.

---

## 2. 두 프로젝트 상세 비교

| 비교 항목 | `b_0910_memory_claude` (거시 분석 엔진) | `b_0917_10_QK_EARNING` (미시 수집 파이프라인) |
| :--- | :--- | :--- |
| **시스템 역할** | **Macro Intelligence Engine (분석 모델 & 시뮬레이터)** | **Micro Data Pipeline (실시간 수집 & 감각 기관)** |
| **핵심 지표** | Capex 워터폴, HBM 수급 밸런스, CoWoS 캐파, 데이터센터 전력, 장기 계약 | SEC 파일링(10-K/Q/8-K), 관세청 10일 통관, EPS/Rev 컨센서스, GPU 스팟 가격 |
| **데이터베이스 자산** | • 36개 기업 마스터<br>• 2020~2026 657건 분기 실적<br>• $877B 메가 계약 15건<br>• 전력/팹 캐파 25건 | • SQLite + FTS5 전문검색 가상 테이블<br>• 관세청 품목별(HS코드) 수출입 통계<br>• 야후 파이낸스 일별 주가(OHLCV) |
| **시각화 / UI** | • D3 Sankey 자본 이동 다이어그램<br>• 밸류체인 인터랙티브 네트워크 그래프<br>• HBM 시장 밸런스 시뮬레이터<br>• Capex 흡수 워터폴 차트 | • 반응형 모던 SPA 대시보드 (Dark 테마)<br>• SEC 공시 목록 및 원문 뷰어 모달<br>• 수집 즉시 동기화 트리거 UI |
| **소프트웨어 스택** | Python 표준 라이브러리(`http.server`), 정적 HTML/JS | Flask, SQLite3 (FTS5), BeautifulSoup/Requests, Chart.js |
| **주요 한계점** | 실적·캐파 데이터가 정적 스크립트에 머물러 실시간 갱신 부재 | 거시적 밸류체인 순환 및 중장기 업황 예측 시뮬레이션 모델 부재 |

---

## 3. 핵심 통합 중심축 (4대 필러)

### 필러 1. 데이터 파이프라인 중심 통합: 동적 시뮬레이터 구동
- **구조**: `10_QK_EARNING`의 수집기(`edgar_collector.py`, `kr_export_collector.py`)가 최신 10-Q/K 확정 실적과 10일 주기 통관 데이터를 적재하면, `memory_claude`의 시뮬레이션 모델(Sankey 자본이동, Capex 워터폴, HBM 수급 모델)이 트리거되어 자동 갱신됩니다.
- **가치**: 기존에 멈춰 있던 정적 분석 모델이 **살아서 실시간으로 업데이트되는 예측 엔진**으로 전환됩니다.

### 필러 2. 사용자 경험(UI/UX) 중심 통합: "숲(Macro) ↔ 나무(Micro)" 드릴다운
- **사용자 동선**:
  1. **Macro View**: 메인 화면에서 거시적 자본 흐름(Sankey) 및 HBM 수급 밸런스를 탐색.
  2. **Node Drill-down**: 특정 기업(예: NVIDIA, SK하이닉스, TSMC) 또는 특정 분기 클릭.
  3. **Micro View**: 해당 기업의 **SEC 10-Q 원문(FTS 검색), 관세청 10일 수출입 통계, 컨센서스 Beat/Miss 히스토리, GPU 렌탈 가격** 모달이 즉시 연동.
- **가치**: 하나의 플랫폼에서 거시적 전략 인사이트와 1차 공시 원문 검증을 동시에 완결.

### 필러 3. 아키텍처 중심 통합: Flask 기반 모듈형 백엔드로 단일화
- `b_0910`의 단순 정적 파일 서빙(`http.server`) 한계를 극복하고, `b_0917`의 **Flask 웹 애플리케이션 구조**를 표준으로 채택합니다.
- 구조 확장:
  - `app/services/macro_analytics.py`: Sankey, HBM 밸런스, Capex 워터폴 계산 엔진
  - `app/routes/analytics.py`: 거시 분석 데이터 제공 REST API
  - `app/routes/filings.py`, `app/routes/indicators.py`: 기존 공시 및 선행지표 API 유지

### 필러 4. 데이터베이스 단일화: Single Source of Truth
- 동일한 8개 레이어, 36개 기업 엔티티 체계를 통합 마스터로 정립합니다.
  - **마스터**: `layer`, `entity` (통합)
  - **거시/캐파**: `contracts`, `fab_capacity`, `datacenter_capacity`, `milestones` (`b_0910` 이관)
  - **실적/선행지표**: `filing`, `filing_fts`, `financial_metric`, `consensus`, `industry_indicator` (`b_0917` 구조에 `b_0910`의 657건 분기 실적 매핑 적재)

---

## 4. 통합 아키텍처 설계

```text
[Data Sources]
  ├── SEC EDGAR (10-K, 10-Q, 8-K) ────┐
  ├── 관세청 UNIPASS (10일 주기 수출) ──┤
  ├── Yahoo Finance & GPU Cloud Rates ─┼─► [Automated Collectors]
  └── IR 컨콜 & 메가 계약/캐파 공시 ──┘            │
                                                  ▼
                                       [Integrated SQLite DB]
                                         ├── Master (layer, entity)
                                         ├── Micro (filing, fts5, indicators)
                                         └── Macro (capacity, contracts, forecast)
                                                  │
                                                  ▼
                                         [Flask Backend API]
                                         ├── /api/filings
                                         ├── /api/exports
                                         └── /api/analytics (Sankey, HBM, Capex)
                                                  │
                                                  ▼
                                      [Unified SPA Dashboard]
     ┌───────────────────┬───────────────────┬───────────────────┬───────────────────┐
     ▼                   ▼                   ▼                   ▼                   ▼
 [1. 거시 자본흐름]   [2. HBM/팹 캐파]   [3. 선행 통관지표]   [4. 공시/원문 뷰어]   [5. AI 종합 리포트]
  (Sankey, 워터폴)     (수급 시뮬레이터)    (10일 수출입 추이)   (10-K/Q FTS 검색)    (정량+원문 통합)
```

---

## 5. 단계별 통합 로드맵 (Action Items)

### Phase 1: DB 스키마 및 엔티티 정합성 통일
- [ ] 36개 기업 엔티티 마스터 통일 (티커, CIK, DART 코드 교차 검증)
- [ ] `memory_claude.db`의 역사적 데이터(실적 657건, 계약 15건, 캐파 25건)를 통합 DB로 이전
- [ ] Capex 및 OPM(영업이익률) 결측치 보강 뷰 생성

### Phase 2: 백엔드 모듈 및 API 통합
- [ ] `b_0917_10_QK_EARNING`의 Flask 프레임워크 기반으로 소스 통합
- [ ] `app/services/macro_analytics.py` 추가 (Sankey 계산, HBM 수급 모델, Capex 전파 로직)
- [ ] `/api/analytics/*` REST API 엔드포인트 구현

### Phase 3: 통합 웹 대시보드 구축 (SPA)
- [ ] 프론트엔드 네비게이션 탭 통합:
  - **Tab 1: 거시 밸류체인 & 자본 흐름** (Sankey, Network Graph, Capex Waterfall)
  - **Tab 2: 선행지표 & 통관 분석** (관세청 10일 통계, TSMC 월매출, GPU 렌탈가)
  - **Tab 3: 기업별 실적 & 공시 원문** (10-K/Q 타임라인, FTS 검색, Beat/Miss)
  - **Tab 4: HBM & Fab 캐파 시뮬레이터** (수급 크로스오버, 전력/데이터센터)
- [ ] 거시 차트 노드 클릭 시 해당 기업의 공시/통관 모달이 열리는 상호작용 연결

### Phase 4: 인텔리전스 고도화 및 자동화
- [ ] 데이터 수집 스케줄러 연동 (매월 1/11/21일 관세청 자동 수집, SEC 신규 공시 데몬)
- [ ] 정량 DB 데이터와 10-Q 본문 발췌문을 결합한 AI 자동 리포트 에이전트 완성
