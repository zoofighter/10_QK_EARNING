# 🔍 산업 선행지표 수집 방법 조사

> **대상 지표**: TSMC 월매출, 메모리 현물가(DRAM/NAND), 하이퍼스케일러 CapEx 집계

---

## 1. TSMC 월간 매출

### 데이터 소스

| 소스 | URL | 비용 | 자동화 |
|------|-----|------|--------|
| **TSMC IR 페이지** (권장) | `https://investor.tsmc.com/english/monthly-revenue/{YYYY}` | 무료 | 크롤링 가능 |
| TW Market Data API | `https://api.twmarketdata.com/` | 무료 Tier 있음 | REST API |
| MacroMicro | `https://www.macromicro.me/` | 일부 무료 | 차트 레벨 |

### 수집 방식: TSMC IR 페이지 크롤링 (추천)

TSMC는 매월 10일경 전월 매출을 IR 페이지에 HTML 테이블로 공개합니다.

```python
import pandas as pd
import requests

def get_tsmc_monthly_revenue(year: int) -> pd.DataFrame:
    """TSMC IR 페이지에서 월간 매출 데이터 크롤링"""
    url = f"https://investor.tsmc.com/english/monthly-revenue/{year}"
    headers = {
        "User-Agent": "QK_EARNING/1.0 (your.email@example.com)"
    }
    
    response = requests.get(url, headers=headers)
    response.raise_for_status()
    
    # pandas가 HTML 테이블을 자동 파싱
    tables = pd.read_html(response.text)
    revenue_df = tables[0]  # 첫 번째 테이블이 월매출
    
    return revenue_df

# 2020~2026년 전체 수집
for year in range(2020, 2027):
    df = get_tsmc_monthly_revenue(year)
    print(f"=== {year} ===")
    print(df.head())
```

### 데이터 형태

| Month | Net Revenue (NT$ M) | MoM (%) | YoY (%) |
|-------|---------------------|---------|---------|
| Jan   | 263,524             | -5.2    | +35.9   |
| Feb   | 243,618             | -7.5    | +31.4   |
| ...   | ...                 | ...     | ...     |

### 주의사항
- 단위: **NTD (신대만달러)**. USD 변환 필요 시 환율 적용 필요
- 매월 10일경 전월 데이터 공개 (비감사)
- `robots.txt` 존중, 요청 간 1초 이상 딜레이

---

## 2. 메모리 현물가 (DRAM / NAND)

### 데이터 소스

| 소스 | 접근 방식 | 비용 | 자동화 |
|------|-----------|------|--------|
| **MemoryIndex API** (추천) | REST API (JSON) | 무료 Tier (10종목, 12h 딜레이) | ✅ API |
| DRAMeXchange (TrendForce) | 웹사이트 수동 확인 | 유료 (Silver/Gold/Platinum) | ❌ 스크래핑 금지 |
| Silicon Analysts | REST API (JSON) | 무료 | ✅ API |
| 수동 입력 | 업계 보고서/뉴스 참조 | 무료 | ❌ |

### 수집 방식 A: MemoryIndex API (추천)

```python
import requests

def get_memory_spot_prices():
    """MemoryIndex 무료 API로 메모리 현물가 조회"""
    url = "https://memoryindex.io/api/public/v1/prices"
    
    response = requests.get(url)
    response.raise_for_status()
    data = response.json()
    
    for item in data:
        print(f"{item['name']}: ${item['price']} ({item['change_pct']}%)")
    
    return data

# 특정 제품 조회 (예: DDR5)
def get_memory_price_by_id(contract_id):
    url = f"https://memoryindex.io/api/public/v1/prices/{contract_id}"
    response = requests.get(url)
    return response.json()
```

### 무료 Tier 제한사항
- 10개 제품(Contract)까지만 조회
- 12시간 딜레이 (실시간 아님)
- 히스토리 데이터 없음 (Professional/Enterprise 유료)

### 수집 방식 B: 수동 입력 + DB 저장

무료 API 제한이 있으므로, 주요 DRAM/NAND 가격만 주 1회 수동 입력하는 하이브리드 방식도 실용적입니다:

```
수동 입력 대상:
- DDR5 8Gb 1Rx8 스팟 가격 (USD)
- HBM3e 가격 (USD, 가능한 경우)
- NAND 128L TLC 512Gb 스팟 가격 (USD)
```

→ 웹 UI의 수동 입력 폼에서 `industry_indicator` 테이블에 저장

### 대안: 뉴스/보고서 기반 반자동

DRAMeXchange의 무료 회원 등록 후 가격 스냅샷 확인 → 수동 입력
- URL: `https://www.dramexchange.com/`
- 무료 회원도 현재 스팟 가격 확인 가능 (다운로드/API 불가)

---

## 3. 하이퍼스케일러 CapEx 집계

### 데이터 소스

| 소스 | 방식 | 비용 | 자동화 |
|------|------|------|--------|
| **SEC EDGAR + EdgarTools** (추천) | Python 라이브러리 | 무료 | ✅ 완전 자동 |
| financial_metric 테이블 자동 집계 | DB 뷰/쿼리 | 무료 | ✅ 자동 |
| yfinance | Yahoo Finance | 무료 | ✅ 부분 자동 |

### 수집 방식: EdgarTools로 XBRL에서 자동 추출 (추천)

```python
from edgar import Company, set_identity

set_identity("your.name@example.com")

HYPERSCALERS = {
    "GOOGL": "Alphabet",
    "AMZN": "Amazon",
    "MSFT": "Microsoft",
    "META": "Meta",
}

def get_capex(ticker: str) -> dict:
    """SEC 10-Q/10-K에서 CapEx 자동 추출"""
    company = Company(ticker)
    financials = company.get_financials()
    
    # CapEx (현금흐름표에서 추출)
    capex = financials.get_capital_expenditures()
    
    return {
        "ticker": ticker,
        "capex": capex,
    }

# 하이퍼스케일러 4사 CapEx 집계
total_capex = 0
for ticker, name in HYPERSCALERS.items():
    result = get_capex(ticker)
    print(f"{name} ({ticker}): ${result['capex']:,.0f}")
    total_capex += result['capex']

print(f"\n=== 하이퍼스케일러 4사 합계: ${total_capex:,.0f} ===")
```

### 대안: financial_metric 테이블에서 자동 집계

이미 F3(핵심 지표 자동 추출)에서 각 기업의 CapEx를 `financial_metric` 테이블에 저장하므로, 별도 수집 없이 **SQL 뷰**로 집계 가능:

```sql
-- 하이퍼스케일러 4사 분기별 CapEx 합계 뷰
CREATE VIEW v_hyperscaler_capex AS
SELECT 
    fm.fiscal_year,
    fm.fiscal_quarter,
    SUM(fm.value) as total_capex_m,
    COUNT(DISTINCT fm.entity_id) as company_count,
    GROUP_CONCAT(e.ticker, ', ') as tickers
FROM financial_metric fm
JOIN entity e ON fm.entity_id = e.id
WHERE fm.metric_type = 'capex'
  AND e.layer_code = 'L2_HYPERSCALER'
  AND e.ticker IN ('GOOGL', 'AMZN', 'MSFT', 'META')
GROUP BY fm.fiscal_year, fm.fiscal_quarter
ORDER BY fm.fiscal_year, fm.fiscal_quarter;
```

→ **추가 수집 불필요**, 기존 파이프라인에서 자동으로 확보

---

## 종합: 구현 전략

| 지표 | 수집 방식 | 자동화 수준 | 구현 난이도 |
|------|-----------|-------------|-------------|
| **TSMC 월매출** | TSMC IR 크롤링 (`pd.read_html`) | 🟢 반자동 (월 1회 배치) | 쉬움 |
| **메모리 현물가** | MemoryIndex API (무료) + 수동 보완 | 🟡 하이브리드 | 쉬움 |
| **하이퍼스케일러 CapEx** | financial_metric 테이블 SQL 집계 | 🟢 완전 자동 | 매우 쉬움 |

### 필요 패키지 (requirements.txt 추가)

```
edgartools>=3.0     # SEC EDGAR XBRL 파싱
yfinance>=0.2       # 주가 데이터 (이미 추가)
pandas>=2.0         # 데이터 처리 + HTML 파싱
requests>=2.31      # HTTP 요청
lxml>=5.0           # HTML 파서 (pd.read_html 백엔드)
```

### 수집 스케줄

| 지표 | 빈도 | 시점 |
|------|------|------|
| TSMC 월매출 | 월 1회 | 매월 11일 (TSMC 발표 다음날) |
| 메모리 현물가 | 주 1회 | 매주 금요일 |
| 하이퍼스케일러 CapEx | 분기 1회 | 실적 발표 시 자동 (F3 파이프라인) |
