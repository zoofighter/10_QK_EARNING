# [리브랜딩 명세서] QK_EARNING × Memory Claude ➔ SiliconPulse Terminal 전환

**문서 번호**: SPEC-2026-10-09-REBRANDING-SILICONPULSE  
**작성 일자**: 2026-10-09  
**작성자**: Antigravity AI  
**상태**: 채택 및 구현 (Adopted & Implemented)  
**채택안**: **추천안 1 (프로페셔널 금융·인텔리전스 터미널 스타일: SiliconPulse Terminal)**

---

## 1. 리브랜딩 배경 및 필요성

### 1.1 기존 명칭의 한계
* **`QK_EARNING`**:
  * 초기 SEC Form 10-K, 10-Q 공시 파일 다운로더에서 유래된 프로젝트 폴더명입니다.
  * 현재 시스템은 단순 공시 뷰어를 넘어 8대 레이어 34개사 실시간 어닝 캘린더, 관세청 10일 수출입 속보치, GPU 클라우드 렌탈 스팟 시세, 메모리 현물가, 국내외 애널리스트 리포트 FTS5 전문 색인, AI 자율 보고서 생성기까지 포괄하고 있어 "QK_EARNING"이라는 명칭은 시스템의 위상과 기능을 심각하게 축소시킵니다.
* **`Memory Claude`**:
  * AI 반도체 거시 자본 흐름(Sankey), HBM/CoWoS 수급 밸런스, 데이터센터 전력 캐파 분석 엔진의 프로토타입 작성 당시 사용된 명칭입니다.
  * 앤트로픽의 "Claude" 모델명이 포함되어 있어 외부 사용자나 투자자가 볼 때 '클로드의 메모리 기능' 또는 단순 '챗봇 세션'으로 오인할 위험이 큽니다.

---

## 2. 네이밍 추천안 비교 검토 (4대 대안)

| 추천안 | 통합 브랜드명 | 미시 파이프라인 (구 QK_EARNING) | 거시 엔진 (구 Memory Claude) | 콘셉트 및 특징 |
| :--- | :--- | :--- | :--- | :--- |
| **추천안 1 (채택)** | **SiliconPulse (실리콘펄스)** | **MicroRadar (마이크로 레이더)** | **MacroFlow (매크로 플로우)** | **블룸버그/팩트셋급 기관 투자 터미널 스타일. 직관적이고 세련됨** |
| 추천안 2 | **OmniSemi (옴니세미)** | SemiTree (세미트리) | SemiForest (세미포레스트) | '숲과 나무'의 미시·거시 상호보완적 양 날개 은유 |
| 추천안 3 | **AI ChipMatrix (칩매트릭스)** | Earnings Engine | SuperCycle Simulator | AI 반도체 밸류체인 하드웨어 테크 지향 스타일 |
| 추천안 4 | **SiliconFlow (실리콘플로우)** | Company Intelligence | Macro Balance | 단일 통합 브랜드 하에 간결한 서브 탭 체계 구성 |

---

## 3. 최종 채택: 추천안 1 (SiliconPulse Terminal) 상세 구조

### 3.1 브랜드 아이덴티티 (Brand Identity)
* **메인 브랜드**: **SiliconPulse (실리콘펄스)**
  * *"The Living Pulse of the AI Semiconductor Value Chain"*
  * AI 반도체 생태계의 자본과 기술이 요동치는 맥박(Pulse)을 실시간으로 감지하고 시뮬레이션하는 인텔리전스 터미널.
* **부제 및 슬로건**:
  * **SiliconPulse Terminal — AI 반도체 밸류체인 통합 인텔리전스**
* **양대 엔진 구성**:
  1. **MicroRadar (마이크로 레이더)** *(구 QK_EARNING)*:
     * 34개 핵심 기업의 SEC 10-K/Q 공시, 10일 주기 관세청 통관, 분기 실적 Beat/Miss, 실시간 어닝 캘린더 D-Day 추적.
  2. **MacroFlow (매크로 플로우)** *(구 Memory Claude)*:
     * 빅테크 Capex의 D3 Sankey 자본 이동, HBM3e/4 수급 밸런스, 데이터센터 전력(GW) 및 CoWoS 팹 캐파 예측 시뮬레이터.

---

## 4. UI/UX 및 코드베이스 적용 명세

### 4.1 웹 브라우저 타이틀
* **기존**: `QK_EARNING × Memory Claude — 회사별 통합 인텔리전스 & 거시 수급 밸류체인`
* **변경**: `SiliconPulse Terminal — AI 반도체 밸류체인 통합 인텔리전스 (MicroRadar × MacroFlow)`

### 4.2 좌측 상단 헤더 로고 및 브랜딩
* **로고 아이콘**: 반도체 칩/펄스 심볼 (`⚡` 또는 `🌐`)
* **메인 타이틀**: `SiliconPulse`
* **서브 뱃지**: `Terminal` 및 `MicroRadar × MacroFlow`

### 4.3 메인 모드 네비게이션 탭 라벨
1. `[🏢 회사별 인텔리전스 (MicroRadar)]` (버튼: `btn-mode-company`)
2. `[🌐 거시 수급 밸류체인 (MacroFlow)]` (버튼: `btn-mode-macro`)
3. `[📈 선행 지표 & 통관]` (버튼: `btn-mode-indicators`)
4. `[📅 어닝 캘린더]` (버튼: `btn-mode-calendar`)
5. `[📑 SEC 공시 아카이브]` (버튼: `btn-mode-archive`)

### 4.4 기업별 상세 뷰 서브탭 6 배지
* 기업 허브 내 **'🔗 밸류체인 & 거시 수급 연계'** 탭의 헤더 배지:
  * **기존**: `Memory Claude`
  * **변경**: `MacroFlow Engine`

---

## 5. 변경 파일 목록 및 구현 체크리스트

- [x] [docs/2026-10-09_시스템_리브랜딩_추천안_및_SiliconPulse_적용_명세서.md](file:///Users/boon/Dropbox/03_code/b_0917_10_QK_EARNING/docs/2026-10-09_%EC%8B%9C%EC%8A%A4%ED%85%9C_%EB%A6%AC%EB%B8%8C%EB%9E%9C%EB%94%A9_%EC%추천안_및_SiliconPulse_적용_명세서.md) 신규 작성
- [ ] [static/index.html](file:///Users/boon/Dropbox/03_code/b_0917_10_QK_EARNING/static/index.html): 브라우저 타이틀, 헤더 로고, 모드 탭, 서브탭 배지 변경
- [ ] [static/js/app.js](file:///Users/boon/Dropbox/03_code/b_0917_10_QK_EARNING/static/js/app.js): 주석 및 UI 텍스트 일괄 갱신
- [ ] [static/css/style.css](file:///Users/boon/Dropbox/03_code/b_0917_10_QK_EARNING/static/css/style.css): 관련 주석 최신화
- [ ] 시스템 테스트 및 브라우저 동작 검증
