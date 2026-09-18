# 🔍 2차 개발 데이터 5종 수집 방법 조사

> **대상**: S-1 IPO 문서, 컨센서스 히스토리, SEMI 장비 출하, GPU 가격, 애널리스트 의견

---

## 1. S-1 IPO 문서

### 결론: ✅ 완전 자동 수집 가능 (무료)

S-1은 SEC EDGAR에 공식 제출되는 문서이므로, 1차 개발의 10-Q/10-K 수집 파이프라인과 **동일한 방식**으로 수집 가능합니다.

### 데이터 소스

| 소스 | 방식 | 비용 |
|------|------|------|
| **SEC EDGAR + EdgarTools** | Python 라이브러리 | 무료 |

### 대상 기업

| 기업 | 티커 | Filing 유형 | 비고 |
|------|------|-------------|------|
| CoreWeave | CRWV | S-1 | 2025년 3월 제출 |
| Nebius | NBIS | S-1 또는 F-1 (외국기업) | FPI로 6-K/20-F 주로 사용 |
| Kioxia | 6600.T | 해당 없음 | SEC Filing 없음 (도쿄증권거래소) |

### 코드 예시

```python
from edgar import Company, set_identity

set_identity("your.name@example.com")

# CoreWeave S-1 수집
coreweave = Company("CRWV")
s1_filings = coreweave.get_filings(form="S-1")
latest_s1 = s1_filings.latest()

# S-1/A (수정본) 포함 전체 조회
all_s1 = coreweave.get_filings(form=["S-1", "S-1/A"])
for filing in all_s1:
    print(f"{filing.filing_date} | {filing.form} | {filing.accession_no}")
    
# Nebius — 외국 기업이므로 F-1 또는 F-4 확인
nebius = Company("NBIS")
ipo_filings = nebius.get_filings(form=["S-1", "F-1", "F-4", "20-F"])
```

### 구현 방향
- 기존 `edgar_collector.py`에 `form="S-1"` 파라미터만 추가하면 끝
- `filing` 테이블에 `filing_type='S-1'`로 저장 — **DB 변경 불필요**

---

## 2. 컨센서스 히스토리 (애널리스트 추정치 변화)

### 결론: 🟡 무료 API로 가능하나 제한 있음

### 데이터 소스

| 소스 | 데이터 | 무료 Tier | 자동화 |
|------|--------|-----------|--------|
| **Financial Modeling Prep (FMP)** (추천) | 컨센서스 EPS/Revenue + 히스토리 | 250건/일 | ✅ REST API |
| **Finnhub** | 컨센서스 + 서프라이즈 | 60건/분 | ✅ REST API |
| **Business Quant** | 컨센서스 + high/low 범위 | 무료 | ✅ REST API |
| 수동 입력 | 직접 데이터 입력 | 무료 | ❌ |

### FMP API 예시

```python
import requests

FMP_API_KEY = "your_api_key"  # 무료 가입 시 발급

def get_consensus_history(ticker: str) -> list:
    """FMP에서 분기별 컨센서스 추정치 히스토리 조회"""
    url = f"https://financialmodelingprep.com/api/v3/analyst-estimates/{ticker}"
    params = {
        "apikey": FMP_API_KEY,
        "period": "quarter",
        "limit": 30,  # 최근 30분기
    }
    response = requests.get(url, params=params)
    return response.json()

# 예시: NVDA 컨센서스 히스토리
data = get_consensus_history("NVDA")
for item in data:
    print(f"{item['date']} | EPS est: {item['estimatedEpsAvg']:.2f} "
          f"| Rev est: ${item['estimatedRevenueAvg']:,.0f}")
```

### 무료 Tier 제한사항
- **FMP**: 일 250건 요청 → 34개 기업 × 7 지표 = ~238건/일로 딱 가능
- **Finnhub**: 분 60건 → 충분하나 히스토리 깊이 제한적
- **컨센서스 "변화 추이"**: 대부분 유료 (Bloomberg, FactSet 급). 무료로는 시점별 스냅샷만 가능

### 구현 방향
- `consensus` 테이블에 `estimate_date` 컬럼 추가하여 시점별 스냅샷 기록
- 주 1회 배치로 현재 컨센서스 스냅샷 저장 → 시간이 쌓이면 자연스럽게 변화 추이 확보
- 무료 API 한계 시 수동 입력 폼 대안으로 제공

---

## 3. SEMI 장비 출하 데이터

### 결론: 🔴 유료 구독 필수, 대안 활용

### 데이터 소스

| 소스 | 데이터 | 비용 | 자동화 |
|------|--------|------|--------|
| **SEMI EMDS** (공식) | 월간 Billing, 지역별, 장비별 | 💰 유료 구독 | ❌ 구독자 전용 |
| **SEMI 보도자료** (대안 1) | 분기별 하이라이트 수치 | 무료 | 🟡 크롤링 가능 |
| **장비사 10-Q 프록시** (대안 2) | AMAT, LRCX, KLAC 등 매출 합산 | 무료 | ✅ 자동 |

### 대안 1: SEMI 보도자료 크롤링

SEMI는 분기마다 장비 출하 통계를 보도자료로 발표합니다:
- URL: `https://www.semi.org/en/news`
- 내용: "글로벌 반도체 장비 출하 $XX B, 전년 대비 +XX%"

```python
# SEMI 보도자료에서 헤드라인 수치를 추출하는 방식
# → 수동 입력이 더 현실적 (분기 1회이므로)
```

### 대안 2: 장비사 매출 합산 (프록시 지표) — 추천

**이미 수집하는 데이터로 대체 가능합니다!**

L4_FOUNDRY 기업(AMAT, LRCX, KLAC, ASML)의 분기 매출을 합산하면 SEMI Billing의 프록시가 됩니다:

```sql
-- L4 장비사 매출 합산 = SEMI Billing 프록시
CREATE VIEW v_equipment_billing_proxy AS
SELECT 
    fm.fiscal_year,
    fm.fiscal_quarter,
    SUM(fm.value) as total_revenue_m,
    COUNT(DISTINCT fm.entity_id) as company_count
FROM financial_metric fm
JOIN entity e ON fm.entity_id = e.id
WHERE fm.metric_type = 'revenue'
  AND e.ticker IN ('AMAT', 'LRCX', 'KLAC', 'ASML')
GROUP BY fm.fiscal_year, fm.fiscal_quarter
ORDER BY fm.fiscal_year, fm.fiscal_quarter;
```

### 구현 방향
- **1순위**: L4 장비사 매출 합산 뷰 (추가 수집 불필요)
- **2순위**: SEMI 보도자료 수치를 `industry_indicator` 테이블에 분기 1회 수동 입력
- 유료 구독은 ROI 고려하여 추후 결정

---

## 4. GPU 가격 추이

### 결론: 🟢 무료 API 있음 (렌탈 가격 중심)

### 데이터 소스

| 소스 | 데이터 | 비용 | 자동화 |
|------|--------|------|--------|
| **Ornn Data (OCPI)** (추천) | H100, B200 렌탈 가격 (실시간) | 무료 | ✅ REST API |
| GPUs.io | 렌탈 가격 비교 + 히스토리 | 무료 | ✅ REST API |
| Silicon Data (Silicon Index) | 기관용 일간 벤치마크 | 유료 | ✅ API |
| SemiAnalysis | 종합 GPU 가격 지수 | 유료 | ✅ API |
| GitHub (gpu-price-tracker) | 커뮤니티 수집 히스토리 | 무료 | ✅ JSON 파일 |

### Ornn Data API 예시

```python
import requests

def get_gpu_rental_prices():
    """Ornn Data에서 GPU 렌탈 가격 조회 (무료)"""
    # H100 가격
    url = "https://api.ornn.io/v1/gpu/prices"
    params = {"model": "H100"}
    
    response = requests.get(url)
    data = response.json()
    
    for provider in data:
        print(f"{provider['provider']}: "
              f"${provider['price_per_hour']}/hr "
              f"({provider['gpu_model']})")
    
    return data
```

### 가격 유형 구분

| 유형 | 설명 | 데이터 가용성 |
|------|------|---------------|
| **클라우드 렌탈 (On-Demand)** | AWS/Azure/Lambda 등 시간당 요금 | ✅ 투명하고 추적 가능 |
| **클라우드 렌탈 (Spot)** | 변동 가격 | ✅ 추적 가능 |
| **하드웨어 구매** | H100 카드 물리적 구매가 | 🔴 불투명, 협상 기반 |
| **중고 리세일** | 중고 시장 거래 가격 | 🔴 비공개 |

### 구현 방향
- **렌탈 가격** 중심으로 추적 (투명하고 API 접근 가능)
- `industry_indicator` 테이블에 `indicator_type = 'GPU_RENTAL_H100'`, `'GPU_RENTAL_B200'`
- 주 1회 배치 수집 또는 일간 수집
- 하드웨어 구매가는 뉴스/보고서 기반 수동 입력

---

## 5. 애널리스트 투자의견 (업그레이드/다운그레이드)

### 결론: 🟢 무료 API로 수집 가능

### 데이터 소스

| 소스 | 데이터 | 무료 Tier | 자동화 |
|------|--------|-----------|--------|
| **Financial Modeling Prep** (추천) | 업/다운그레이드, 목표가, 투자의견 | 250건/일 | ✅ REST API |
| **Finnhub** | 업/다운그레이드 히스토리 | 60건/분 | ✅ REST API |
| Finnworlds | 15년+ 애널리스트 이력 | 유료 | ✅ REST API |
| 수동 입력 | 직접 입력 | 무료 | ❌ |

### FMP API 예시

```python
import requests

FMP_API_KEY = "your_api_key"

def get_analyst_ratings(ticker: str) -> list:
    """FMP에서 애널리스트 업/다운그레이드 히스토리 조회"""
    url = f"https://financialmodelingprep.com/api/v3/upgrades-downgrades/{ticker}"
    params = {"apikey": FMP_API_KEY}
    
    response = requests.get(url, params=params)
    return response.json()

def get_price_target(ticker: str) -> list:
    """FMP에서 목표가 히스토리 조회"""
    url = f"https://financialmodelingprep.com/api/v4/price-target/{ticker}"
    params = {"apikey": FMP_API_KEY}
    
    response = requests.get(url, params=params)
    return response.json()

# 예시: NVDA
ratings = get_analyst_ratings("NVDA")
for r in ratings[:5]:
    print(f"{r['publishedDate']} | {r['analystCompany']} | "
          f"{r['previousGrade']} → {r['newGrade']}")
```

### 데이터 항목

| 필드 | 설명 | 예시 |
|------|------|------|
| publishedDate | 변경 일자 | 2026-07-15 |
| analystCompany | 증권사 | Goldman Sachs |
| previousGrade | 이전 의견 | Neutral |
| newGrade | 변경 의견 | Buy |
| priceTarget | 목표가 | $180 |
| action | 행동 유형 | upgrade / downgrade / reiterate |

### 구현 방향
- 신규 `analyst_rating` 테이블 필요 (2차 개발 시)
- FMP 무료 Tier로 34개 기업 커버 가능 (일 250건 내)
- 주 1~2회 배치 수집

---

## 종합 비교

| # | 데이터 | 수집 방식 | 비용 | 난이도 | 자동화 |
|---|--------|-----------|------|--------|--------|
| 1 | **S-1 IPO** | SEC EDGAR (EdgarTools) | 무료 | ⭐ 쉬움 | 🟢 완전 자동 |
| 2 | **컨센서스 히스토리** | FMP / Finnhub API | 무료 Tier | ⭐⭐ 보통 | 🟡 반자동 |
| 3 | **SEMI 장비 출하** | 장비사 매출 프록시 (DB 뷰) | 무료 | ⭐ 쉬움 | 🟢 완전 자동 |
| 4 | **GPU 가격** | Ornn Data API | 무료 | ⭐⭐ 보통 | 🟢 자동 (렌탈) |
| 5 | **애널리스트 의견** | FMP / Finnhub API | 무료 Tier | ⭐⭐ 보통 | 🟢 자동 |

### 필요 API 키 (무료 가입)

| 서비스 | 가입 URL | 용도 |
|--------|----------|------|
| Financial Modeling Prep | `https://financialmodelingprep.com/` | 컨센서스 + 애널리스트 |
| Finnhub | `https://finnhub.io/` | 백업 소스 |
| Ornn Data | `https://ornn.io/` | GPU 렌탈 가격 |

### 신규 DB 테이블 (2차 개발 시)

#### `analyst_rating` — 애널리스트 투자의견

| 컬럼 | 타입 | 설명 |
|------|------|------|
| id | INTEGER PK | 자동 증가 |
| entity_id | INTEGER FK | 기업 ID |
| published_date | TEXT | 발표일 |
| analyst_company | TEXT | 증권사 |
| action | TEXT | upgrade / downgrade / reiterate |
| previous_grade | TEXT | 이전 의견 |
| new_grade | TEXT | 변경 의견 |
| price_target | REAL | 목표가 (USD) |
| source | TEXT | 데이터 소스 |

#### `consensus` 테이블 추가 컬럼 (2차)

| 컬럼 | 타입 | 설명 |
|------|------|------|
| estimate_date | TEXT | 추정치 기록 시점 (스냅샷용) |
| estimate_high | REAL | 최고 추정치 |
| estimate_low | REAL | 최저 추정치 |
| num_analysts | INTEGER | 참여 애널리스트 수 |
