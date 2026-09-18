# Phase 1 구축 구현 계획: QK_EARNING 시스템

미국 주식 10-Q, 10-K, 8-K 및 어닝콜 관리 시스템(QK_EARNING)의 **Phase 1 — 기반 구축** 작업을 진행합니다.
요건정의서(v1.1)에 정의된 8개 레이어 34개 기업을 등록하고, SQLite 기반 11개 테이블 스키마 구성, Flask 백엔드 API, SEC EDGAR/yfinance 데이터 수집 엔진, 그리고 프리미엄 다크 테마 기반의 웹 대시보드를 완성합니다.

---

## User Review Required

> [!IMPORTANT]
> **Python 환경 및 패키지 설치 방식**
> 시스템 내 Python 3.13(`/opt/homebrew/bin/python3.13`)을 기반으로 프로젝트 루트에 `.venv` 가상환경을 구성하고 필요한 종속성(`flask`, `requests`, `yfinance`, `pandas`, `beautifulsoup4`, `lxml` 등)을 설치합니다.

> [!NOTE]
> **SEC EDGAR 데이터 수집 정책 준수**
> SEC EDGAR API는 초당 최대 10회 요청 제한과 필수적인 `User-Agent: Sample Company Name AdminContact@<sample company domain>.com` 헤더를 요구합니다. 기본 설정(`app/config.py`)에 안전한 rate-limiter(초당 5회 이하) 및 SEC 규정 준수 헤더를 기본 적용합니다.

---

## Proposed Changes

### 1. 가상환경 및 종속성 구성

#### [NEW] [requirements.txt](file:///Users/chansoojeon/Library/CloudStorage/Dropbox/03_code/b_0917_10_QK_EARNING/requirements.txt)
- `Flask>=3.0.0` (경량 REST API 및 템플릿/정적파일 서빙)
- `requests>=2.31.0` (SEC EDGAR API 및 외부 데이터 수집)
- `yfinance>=0.2.40` (주가 OHLCV 수집)
- `pandas>=2.2.0` (시계열 데이터 조작 및 집계)
- `beautifulsoup4>=4.12.0` 및 `lxml` (HTML/XML 공시 파싱)
- `python-dotenv>=1.0.0` (환경변수 관리)

---

### 2. 데이터베이스 및 시딩 스크립트

#### [NEW] [app/models/database.py](file:///Users/chansoojeon/Library/CloudStorage/Dropbox/03_code/b_0917_10_QK_EARNING/app/models/database.py)
- SQLite3 연결 풀 및 헬퍼 함수 (`get_db_connection()`, Row 매핑)
- 트랜잭션 관리 및 쿼리 편의 함수

#### [NEW] [scripts/init_db.py](file:///Users/chansoojeon/Library/CloudStorage/Dropbox/03_code/b_0917_10_QK_EARNING/scripts/init_db.py)
- 요건정의서 §4.2에 정의된 **11개 전체 테이블** 생성:
  1. `layer` (8개 레이어 마스터)
  2. `entity` (34개 기업 마스터)
  3. `filing` (10-Q, 10-K, 8-K, 20-F, 6-K 등)
  4. `earning_call` (어닝콜 트랜스크립트)
  5. `financial_metric` (매출, EPS, CapEx, 마진, 가이던스)
  6. `consensus` (컨센서스 및 Beat/Miss, 어닝 후 1d/5d 주가)
  7. `earning_calendar` (실적 발표 캘린더)
  8. `stock_price` (일간 OHLCV)
  9. `industry_indicator` (TSMC 월매출, 메모리 현물가, 하이퍼스케일러 CapEx 등)
  10. `keyword_analysis` (어닝콜 키워드 빈도 및 맥락)
  11. `llm_summary` (LLM 요약 및 인사이트)
- SQLite **FTS5 가상 테이블** 생성 (`filing_fts` 전문 검색용)
- 인덱스(Index) 최적화 (ticker, filing date, layer_code, metric_type)

#### [NEW] [scripts/seed_entities.py](file:///Users/chansoojeon/Library/CloudStorage/Dropbox/03_code/b_0917_10_QK_EARNING/scripts/seed_entities.py)
- 8개 레이어 마스터 데이터 삽입 (L2_HYPERSCALER ~ L8_POWER)
- 34개 기업 정밀 시딩:
  - Ticker, 영문명, 한글명, Layer, Exchange, SEC CIK, 국가, 데이터 소스(SEC/DART/TSE/MANUAL), 회계연도 종료월
- 초기 더미/최근 실적 캘린더 데이터 등록 (다가오는 D-day 카운트다운 표시용)

---

### 3. 백엔드 Flask 애플리케이션 및 서비스

#### [NEW] [app/__init__.py](file:///Users/chansoojeon/Library/CloudStorage/Dropbox/03_code/b_0917_10_QK_EARNING/app/__init__.py)
- Flask 애플리케이션 팩토리 (`create_app()`)
- Blueprint 등록 (API 라우트 및 페이지 서빙)

#### [NEW] [app/config.py](file:///Users/chansoojeon/Library/CloudStorage/Dropbox/03_code/b_0917_10_QK_EARNING/app/config.py)
- DB 경로 (`data/qk_earning.db`), 원본 파일 저장 경로 (`data/filings/`)
- SEC 헤더 설정 (`SEC_USER_AGENT`) 및 API Rate Limit 설정

#### [NEW] [app/services/edgar_collector.py](file:///Users/chansoojeon/Library/CloudStorage/Dropbox/03_code/b_0917_10_QK_EARNING/app/services/edgar_collector.py)
- SEC submissions API (`https://data.sec.gov/submissions/CIK{cik.zfill(10)}.json`) 연동
- 대상 기업의 최신 10-Q, 10-K, 8-K, 20-F, 6-K 메타데이터 조회
- 공시 원문 다운로드 및 `data/filings/{type}/` 로컬 저장 기능
- `filing` 테이블 및 `filing_fts` 동기화

#### [NEW] [app/services/price_collector.py](file:///Users/chansoojeon/Library/CloudStorage/Dropbox/03_code/b_0917_10_QK_EARNING/app/services/price_collector.py)
- `yfinance` 기반 기업별 일간 OHLCV 데이터 수집
- `stock_price` 테이블 적재 및 최근 종가/변동률 갱신

#### [NEW] [app/routes/api.py](file:///Users/chansoojeon/Library/CloudStorage/Dropbox/03_code/b_0917_10_QK_EARNING/app/routes/api.py)
- `/api/entities`: 기업 목록 (레이어 필터 지원)
- `/api/entities/<ticker>`: 기업 상세 정보
- `/api/filings`: Filing 목록 (기업, 유형, 분기 필터)
- `/api/filings/<id>`: Filing 상세
- `/api/calendar`: 실적 발표 캘린더 및 D-day
- `/api/prices/<ticker>`: 주가 차트 데이터
- `/api/stats`: 대시보드 통계 (기업 수, Filing 수, 레이어 분포 등)
- `/api/collect/trigger`: 수집 수동 트리거 (Filing 또는 주가)
- `/api/collect/status`: 수집 진행 상태 및 이력

#### [NEW] [run.py](file:///Users/chansoojeon/Library/CloudStorage/Dropbox/03_code/b_0917_10_QK_EARNING/run.py)
- Flask 앱 실행 엔트리포인트 (포트: 5001 기본값)

---

### 4. 프론트엔드 대시보드 UI (최고 수준의 비주얼 디자인)

#### [NEW] [static/css/style.css](file:///Users/chansoojeon/Library/CloudStorage/Dropbox/03_code/b_0917_10_QK_EARNING/static/css/style.css)
- 현대적인 다크 글래스모피즘(Dark Glassmorphism) 테마:
  - 딥 네이비/차콜 배경 컬러 팔레트 (`#0B0F19`, `#111827`, `#1F2937`)
  - 레이어별 고유 엑센트 배지 컬러 (L2 Cyan, L3 Purple, L4 Emerald, L5 Amber, L6 Blue, L7 Rose, L8 Indigo)
  - 은은한 그라데이션, 보더 글로우 효과 및 백드롭 블러
  - Outfit / Inter 웹 폰트 적용
  - 반응형 네비게이션 및 그리드 레이아웃

#### [NEW] [static/index.html](file:///Users/chansoojeon/Library/CloudStorage/Dropbox/03_code/b_0917_10_QK_EARNING/static/index.html)
- SPA형 탭 내비게이션:
  - 📊 **대시보드 (Overview)**: KPI 카드 4종 (대상 기업 34개, 수집 Filing 수, 추적 레이어 8개, 최근 D-Day), 레이어별 기업 매트릭스 그리드, 최근 수집 Filing 피드, 실적 발표 카운트다운 위젯
  - 🏢 **기업 탐색 (Companies)**: 8개 레이어 탭 필터링, 검색바, 기업별 상세 모달 (CIK, 거래소, 최근 공시, 주가 차트)
  - 📑 **Filing 아카이브 (Filings)**: 10-Q, 10-K, 8-K 통합 뷰어, 실시간 필터 및 원문 링크
  - 📅 **어닝 캘린더 (Calendar)**: D-Day 카드 및 분기별 발표 일정
  - ⚡ **데이터 수집 제어센터 (Collection Console)**: 기업별 EDGAR / 주가 수집 즉시 실행 버튼, 수집 로그 터미널

#### [NEW] [static/js/app.js](file:///Users/chansoojeon/Library/CloudStorage/Dropbox/03_code/b_0917_10_QK_EARNING/static/js/app.js)
- REST API 비동기 통신 (`fetch`)
- 탭 전환, 검색, 레이어 필터링 실시간 반영
- Chart.js 연동 (기업별 주가 추이 미니 차트)
- 수집 진행 상태 실시간 알림 토스트

---

## Verification Plan

### 1. 자동화 및 스크립트 검증
- 가상환경 생성 및 의존성 설치 정상 확인
- `python scripts/init_db.py` 실행 → `data/qk_earning.db` 생성 및 11개 테이블, FTS5 검증
- `python scripts/seed_entities.py` 실행 → 8개 레이어 및 34개 기업 정확히 인입되었는지 SELECT 쿼리 검증
- `python -c "from app.services.edgar_collector import EdgarCollector; ..."`로 NVDA 등 대표 기업 SEC 메타데이터 수집 테스트
- `python -c "from app.services.price_collector import PriceCollector; ..."`로 NVDA 최신 주가 수집 테스트

### 2. 브라우저 실물 검증
- Flask 서버 구동 (`http://127.0.0.1:5001`)
- Browser Subagent를 통해:
  - 대시보드 메인 화면 로딩 및 KPI 카드/레이어별 기업 카드 렌더링 확인
  - 탭 전환 (Companies, Filings, Calendar, Collection Console) 정상 작동 확인
  - 기업 검색 및 레이어 필터링 상호작용 검증
  - 수집 제어센터에서 수집 트리거 후 결과 반영 확인
  - 스크린샷 캡처하여 시각적 완성도 검증
