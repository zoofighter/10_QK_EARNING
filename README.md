# 10_QK_EARNING

> **AI 및 반도체 밸류체인 공시(SEC 10-K/10-Q) & 선행 실적 지표 통합 모니터링 시스템**

[![Python Version](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/)
[![Framework](https://img.shields.io/badge/framework-Flask-lightgrey.svg)](https://flask.palletsprojects.com/)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)

---

## 📌 프로젝트 개요 (Overview)

**10_QK_EARNING**은 엔비디아(NVDA), TSMC(TSM), 마이크로소프트(MSFT), 구글(GOOGL) 등 글로벌 AI 반도체 및 빅테크 밸류체인 기업들의 **SEC 공시 데이터(10-K, 10-Q, S-1 등)**와 **선행 실적 지표(컨센서스 히스토리, 관세청 반도체 10일 주기 수출 데이터, GPU 가격 지표 등)**를 통합 수집하고 분석할 수 있는 웹 대시보드 플랫폼입니다.

단순 주가 조회를 넘어 기업의 분기 실적 발표 주기 전후의 공시 원문 분석, 시장 예측치 변화, 한국 관세청의 10일 주기(1일/11일/21일) 반도체 통관 수출 실적을 교차 분석하여 조기 실적 추정 및 선행 투자 인사이트를 제공합니다.

---

## 🚀 주요 기능 (Key Features)

1. **SEC EDGAR 공시 수집 및 원문 뷰어**
   * 기업별 10-K(연간), 10-Q(분기), 8-K(수시), S-1(증권신고서) 공시 목록 자동 조회 및 원문 다운로드/캐싱
   * SEC 준수 User-Agent 및 초당 10회 미만 Rate Limit 준수
   * 공시 접수일시(Accepted), 보고서 대상 기간(Period of Report) 명확한 타임라인 제공

2. **반도체 선행 통관 데이터 트래커 (한국 관세청 UNIPASS)**
   * 매월 1일, 11일, 21일 발표되는 10일 주기 반도체 잠정 수출 통계 트래킹
   * 메모리(DRAM, NAND), 시스템반도체, HBM 관련 품목(HS Code)별 수출액 및 전년 동기 대비(YoY) 증감률 분석
   * TSMC 월별 매출 및 미국 반도체/클라우드 실적과의 시차 상관관계 분석 기초자료 제공

3. **실적 컨센서스 히스토리 & 선행 지표 모니터링**
   * 분기별 EPS / Revenue 컨센서스 리비전 추이 (어닝 서프라이즈/쇼크 히스토리)
   * GPU(H100/H200/B200 등) 클라우드 렌탈 가격 및 현물가 추이 모니터링 체계
   * 주요 반도체/AI 기업 주가 및 거래량 차트 제공

4. **직관적인 모던 웹 대시보드**
   * 반응형 웹 UI (Dark Modern 테마)
   * 기업별 인터랙티브 차트 및 원문 미리보기 모달 지원
   * 즉시 데이터 수집/동기화 트리거 기능

---

## 🏗️ 시스템 아키텍처 및 폴더 구조

```text
10_QK_EARNING/
├── app/
│   ├── config.py                 # 앱 환경설정 (포트, SEC User-Agent 등)
│   ├── __init__.py               # Flask 앱 팩토리
│   ├── models/
│   │   └── database.py           # SQLite DB 초기화 및 스키마
│   ├── routes/
│   │   └── api.py                # RESTful API 라우트
│   └── services/
│       ├── edgar_collector.py    # SEC EDGAR API 연동 및 파일링 다운로더
│       ├── kr_export_collector.py# 한국 관세청 반도체 수출 데이터 수집기
│       └── price_collector.py    # 야후 파이낸스 주가 수집기
├── data/
│   ├── qk_earning.db             # 로컬 SQLite 데이터베이스 (git 제외)
│   └── filings/                  # SEC 원문 HTML/텍스트 캐시 (git 제외)
├── docs/                         # 상세 기획 및 가이드 문서
│   ├── 2026-09-17_요건정의서.md   # 시스템 요건 정의서 (v1.1)
│   ├── 2026-09-17_데이터수집가이드.md# 공시 및 주가 수집 가이드
│   ├── 2026-09-17_추가제안.md     # 1차 추가 제안 사항
│   ├── 2026-09-18_보완및제안사항.md# 관세청 통계, GPU, 컨센서스 등 보완사항
│   └── ...
├── scripts/
│   ├── init_db.py                # DB 테이블 생성 스크립트
│   └── seed_entities.py          # AI 반도체 밸류체인 초기 기업 등록
├── static/
│   ├── css/style.css             # 모던 대시보드 스타일시트
│   ├── js/app.js                 # 프론트엔드 비동기 데이터 통신 및 렌더링
│   └── index.html                # 메인 SPA 대시보드
├── tests/
│   └── test_basic.py             # 기본 동작 및 엔드포인트 테스트
├── requirements.txt              # 의존성 패키지 목록
└── run.py                        # 애플리케이션 진입점
```

---

## ⚡ 빠른 시작 (Quick Start)

### 1. 가상환경 설정 및 패키지 설치
```bash
# 가상환경 생성 (최초 1회)
python3 -m venv .venv

# 가상환경 활성화 (macOS/Linux)
source .venv/bin/activate

# 필수 패키지 설치
pip install -r requirements.txt
```

### 2. 데이터베이스 초기화 및 시드 데이터 적재
```bash
# DB 테이블 생성
python scripts/init_db.py

# AI 밸류체인 대상 기업(NVDA, TSM, MSFT 등) 기본 데이터 적재
python scripts/seed_entities.py
```

### 3. 애플리케이션 실행
```bash
python run.py
```
* 서버가 실행되면 브라우저에서 **`http://127.0.0.1:5001`** 접속

---

## 📡 REST API 엔드포인트

| Method | Endpoint | 설명 |
| :--- | :--- | :--- |
| `GET` | `/api/entities` | 추적 대상 기업 목록 및 CIK/티커 조회 |
| `GET` | `/api/filings/<ticker>` | 특정 기업의 SEC 공시 목록 (10-K, 10-Q 등) 조회 |
| `POST` | `/api/collect/<ticker>` | SEC EDGAR로부터 최신 공시 수집 트리거 |
| `GET` | `/api/prices/<ticker>` | 최근 주가 및 일별 추이 조회 |
| `POST` | `/api/prices/collect/<ticker>` | 야후 파이낸스 최신 주가 동기화 |
| `GET` | `/api/exports/semiconductor` | 관세청 반도체 10일 주기 수출입 통계 조회 |
| `GET` | `/api/stats` | 수집된 전체 공시 및 데이터베이스 현황 요약 |

---

## 📚 상세 설계 문서

상세한 기획, 아키텍처, 데이터 수집 파이프라인 명세는 `docs/` 디렉터리에 정리되어 있습니다.

* [요건정의서 (v1.1)](docs/2026-09-17_요건정의서.md)
* [데이터 수집 가이드](docs/2026-09-17_데이터수집가이드.md)
* [추가 제안 사항 (1차)](docs/2026-09-17_추가제안.md)
* [보완 및 제안 사항 (관세청 통계/선행지표/GPU)](docs/2026-09-18_보완및제안사항.md)

---

## 🛠 Git 관리 안내

> **알림**: 본 프로젝트의 Git 커밋(`git commit`) 및 원격 푸시(`git push`)는 사용자가 직접 관리합니다.

작업 완료 후 변경사항을 GitHub에 반영하는 기본 명령어:
```bash
# 변경 파일 확인
git status

# 변경사항 스테이징
git add .

# 커밋 메시지 작성
git commit -m "feat: 커밋 메시지"

# GitHub 원격 저장소에 푸시
git push origin main
```
