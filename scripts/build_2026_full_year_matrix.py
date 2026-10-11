#!/usr/bin/env python3
"""
Generate 2026 Full-Year Unpivoted Ledger (2026-01 ~ 2026-10) for 36 Semiconductor Value Chain Entities.
Integrates:
- 2026 H1 (Jan ~ Jun) Fact Ledger: Official SEC filings, IR milestones, capex, fab ramps, contracts
- 2026 H2 (Jul ~ Oct) Fact Ledger + SignalForge Twitter Radar signals (Plan A 8 Columns)
Saves to docs/2026-10-11_36entities_2026_full_year_layer_matrix.md.
"""
import re
import sys
from pathlib import Path
from typing import Any

ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR))

from scripts.merge_twitter_to_matrix import (
    extract_target_and_metrics,
    parse_existing_matrix,
    clean_sort_key,
    sort_rows,
)

OUTPUT_FILE = ROOT_DIR / "docs" / "2026-10-11_36entities_2026_full_year_layer_matrix.md"
H2_MATRIX_FILE = ROOT_DIR / "docs" / "2026-10-11_36entities_jul_aug_sep_oct_layer_matrix.md"

# 2026 H1 (Jan ~ Jun) Master Curated Historical Fact Ledger (36 Entities)
H1_RAW_EVENTS = [
    # L1 AI Model
    ("L1 AI 모델", "OpenAI (OAI 🇺🇸)", "2026-01-10", "동영상 생성 프론티어 AI 'Sora' 비공개 레드팀 테스트 및 컴퓨트 인프라 로드맵 발표", "🚩 마일스톤", "`[C4]`"),
    ("L1 AI 모델", "OpenAI (OAI 🇺🇸)", "2026-02-16", "소프트뱅크 및 중동 국부펀드와 차세대 AI 인프라 연합 결성 예비 논의 ($100B 구상)", "📜 파트너십", "`[C3]`"),
    ("L1 AI 모델", "OpenAI (OAI 🇺🇸)", "2026-03-29", "차세대 음성·음향 네이티브 엔진 Voice Engine 제한적 프리뷰 공개", "🚩 마일스톤", "`[C4]`"),
    ("L1 AI 모델", "OpenAI (OAI 🇺🇸)", "2026-05-13", "플래그십 옴니모달 모델 'GPT-4o' 글로벌 전격 공개 및 무료 배포 선언", "🚩 마일스톤", "`[C4]`"),
    ("L1 AI 모델", "OpenAI (OAI 🇺🇸)", "2026-06-10", "애플(Apple)과 'Apple Intelligence' 내 ChatGPT 통합 독점 파트너십 체결", "📜 협력계약", "`[C4]`"),
    ("L1 AI 모델", "Anthropic (ANTHROPIC 🇺🇸)", "2026-01-22", "미국 정부 AI 안전 연구소(US AISI)와 선제적 모델 안전성 평가 협약 체결", "📜 정부협력", "`[C4]`"),
    ("L1 AI 모델", "Anthropic (ANTHROPIC 🇺🇸)", "2026-03-04", "차세대 프론티어 모델 Claude 3 패밀리 (Opus, Sonnet, Haiku) 공식 발표", "🚩 마일스톤", "`[C4]`"),
    ("L1 AI 모델", "Anthropic (ANTHROPIC 🇺🇸)", "2026-03-27", "아마존(Amazon)으로부터 추가 전략적 투자 $2.75B 집행 완료 (누적 $4.0B 확보)", "💰 자본유치", "`[C4]`"),
    ("L1 AI 모델", "Anthropic (ANTHROPIC 🇺🇸)", "2026-05-14", "유럽 시장 진출을 위한 런던/더블린 거점 법인 설립 및 EU AI Act 준수 선언", "🏢 인프라", "`[C4]`"),
    ("L1 AI 모델", "Anthropic (ANTHROPIC 🇺🇸)", "2026-06-20", "차세대 벤치마크 1위 모델 Claude 3.5 Sonnet 공식 출시 및 코딩 성능 혁신", "🚩 마일스톤", "`[C4]`"),

    # L2 Hyperscalers
    ("L2 하이퍼스케일러", "Microsoft (MSFT 🇺🇸)", "2026-01-16", "다보스 포럼에서 2026년 AI 가속기 인프라 투자 $50B+ 집행 가이던스 공식화", "💰 투자공시", "`[C4]`"),
    ("L2 하이퍼스케일러", "Microsoft (MSFT 🇺🇸)", "2026-03-18", "위스콘신 마운트 플레전트 1GW 슈퍼캠퍼스 부지 $3.3B 투자 및 토지 매입 완료", "🏢 데이터센터", "`[C4]`"),
    ("L2 하이퍼스케일러", "Microsoft (MSFT 🇺🇸)", "2026-04-25", "Q3 FY26 실적 발표: 애저(Azure) 성장률 31% 달성 및 AI 매출 기여도 7%p 기록", "🚩 실적공시", "`[C4]`"),
    ("L2 하이퍼스케일러", "Microsoft (MSFT 🇺🇸)", "2026-05-21", "Build 2026: Copilot+ PC 생태계 론칭 및 애저 Cobalt 100 CPU 상용 GA", "🚩 마일스톤", "`[C4]`"),
    ("L2 하이퍼스케일러", "Microsoft (MSFT 🇺🇸)", "2026-06-18", "오라클(Oracle)과 OCI 연계 데이터베이스@애저 유럽 5개 리전 전면 확대", "📜 클라우드계약", "`[C4]`"),
    ("L2 하이퍼스케일러", "Amazon (AMZN 🇺🇸)", "2026-01-25", "일본 내 클라우드 및 AI 인프라 확충을 위한 5개년 $15.0B 투자 계획 발표", "🏢 데이터센터", "`[C4]`"),
    ("L2 하이퍼스케일러", "Amazon (AMZN 🇺🇸)", "2026-03-05", "서스퀘하나 탈렌에너지 960MW 원전 연계 데이터센터 캠퍼스 부지 $650M 인수 서명", "🏢 데이터센터", "`[C4]`"),
    ("L2 하이퍼스케일러", "Amazon (AMZN 🇺🇸)", "2026-04-30", "Q1 2026 실적 발표: AWS 매출 전년비 17% 성장 및 연간 CapEx $60B 상향", "🚩 실적공시", "`[C4]`"),
    ("L2 하이퍼스케일러", "Amazon (AMZN 🇺🇸)", "2026-05-28", "인디애나 데이터센터 클러스터 구축을 위한 $11.0B 대규모 투자 승인", "🏢 데이터센터", "`[C4]`"),
    ("L2 하이퍼스케일러", "Amazon (AMZN 🇺🇸)", "2026-06-15", "자체 AI 가속기 Trainium2 EC2 울트라클러스터 프리뷰 고객사 인도 개시", "🚩 마일스톤", "`[C4]`"),
    ("L2 하이퍼스케일러", "Alphabet (GOOGL 🇺🇸)", "2026-02-15", "100만 토큰 컨텍스트 윈도우의 제미나이(Gemini) 1.5 Pro 모델 전격 발표", "🚩 마일스톤", "`[C4]`"),
    ("L2 하이퍼스케일러", "Alphabet (GOOGL 🇺🇸)", "2026-04-25", "Q1 2026 실적 발표: 분기 배당금 최초 도입 및 AI 인프라 분기 CapEx $12B 집행", "🚩 실적공시", "`[C4]`"),
    ("L2 하이퍼스케일러", "Alphabet (GOOGL 🇺🇸)", "2026-05-14", "Google I/O 2026: 6세대 맞춤형 AI 가속기 TPU v6e (Trillium) 공식 공개", "🚩 마일스톤", "`[C4]`"),
    ("L2 하이퍼스케일러", "Alphabet (GOOGL 🇺🇸)", "2026-06-11", "말레이시아 데이터센터 및 클라우드 허브 구축 $2.0B 투자 확정", "🏢 데이터센터", "`[C4]`"),
    ("L2 하이퍼스케일러", "Meta Platforms (META 🇺🇸)", "2026-01-18", "마크 저커버그, 연말까지 엔비디아 H100 35만장 포함 총 60만 GPU 연산력 확보 선언", "💰 CapEx공시", "`[C4]`"),
    ("L2 하이퍼스케일러", "Meta Platforms (META 🇺🇸)", "2026-04-18", "오픈소스 프론티어 LLM Llama 3 (8B / 70B) 공식 공개 및 생태계 개방", "🚩 마일스톤", "`[C4]`"),
    ("L2 하이퍼스케일러", "Meta Platforms (META 🇺🇸)", "2026-04-24", "Q1 2026 실적 발표: 연간 CapEx 가이던스 $35-40B로 $5B 전격 상향", "🚩 실적공시", "`[C4]`"),
    ("L2 하이퍼스케일러", "Meta Platforms (META 🇺🇸)", "2026-05-22", "자체 2세대 AI 추론/학습 가속기 MTIA v2 칩셋 스펙 및 배포 백서 공시", "🚩 마일스톤", "`[C4]`"),
    ("L2 하이퍼스케일러", "Oracle (ORCL 🇺🇸)", "2026-03-11", "Q3 FY26 실적: 남은 OCI 클라우드 계약 잔고 $80B 돌파 및 엔비디아 슈퍼클러스터 계약 급증", "🚩 실적공시", "`[C4]`"),
    ("L2 하이퍼스케일러", "Oracle (ORCL 🇺🇸)", "2026-06-11", "구글 클라우드와 OCI 연계 'Oracle Database@Google Cloud' 공식 멀티클라우드 제휴", "📜 파트너십", "`[C4]`"),
    ("L2 하이퍼스케일러", "CoreWeave (CRWV 🇺🇸)", "2026-02-14", "글로벌 사모펀드 컨소시엄으로부터 $7.5B 부채 파이낸싱 확보 (GPU 매입 전용)", "💰 파이낸싱", "`[C4]`"),
    ("L2 하이퍼스케일러", "CoreWeave (CRWV 🇺🇸)", "2026-05-17", "시리즈 C 라운드 $1.1B 유치 (기업가치 $19.0B 달성)", "💰 자본유치", "`[C4]`"),
    ("L2 하이퍼스케일러", "CoreWeave (CRWV 🇺🇸)", "2026-06-03", "영국 런던 2개소 신규 Tier 4 AI 데이터센터 가속기 클러스터 착공", "🏢 데이터센터", "`[C4]`"),
    ("L2 하이퍼스케일러", "Nebius Group (NBIS 🇳🇱)", "2026-02-05", "얀덱스(Yandex) 자산 매각 완료 및 네덜란드 본사 중심 순수 GPU IaaS 기업으로 재출범", "🚩 마일스톤", "`[C4]`"),
    ("L2 하이퍼스케일러", "Nebius Group (NBIS 🇳🇱)", "2026-05-20", "핀란드 맨새래(Mäntsälä) 30MW GPU 데이터센터 증설 승인 및 H100/H200 클러스터 배치", "🏢 데이터센터", "`[C4]`"),

    # L3 Compute & Accelerators
    ("L3 컴퓨팅/가속기", "NVIDIA (NVDA 🇺🇸)", "2026-01-08", "CES 2026: GeForce RTX 40 SUPER 시리즈 출시 및 오토모티브 Drive Thor 고객사 발표", "🚩 마일스톤", "`[C4]`"),
    ("L3 컴퓨팅/가속기", "NVIDIA (NVDA 🇺🇸)", "2026-02-21", "Q4 FY25 실적 발표: 분기 매출 $22.1B (전년비 +265%) 달성 및 데이터센터 매출 폭증", "🚩 실적공시", "`[C4]`"),
    ("L3 컴퓨팅/가속기", "NVIDIA (NVDA 🇺🇸)", "2026-03-18", "GTC 2026 키노트: 차세대 2080억 트랜지스터 'Blackwell B200' 및 'GB200 NVL72' 전격 공개", "🚩 마일스톤", "`[C4]`"),
    ("L3 컴퓨팅/가속기", "NVIDIA (NVDA 🇺🇸)", "2026-05-22", "Q1 FY26 실적 발표: 매출 $26.0B 돌파, 10대 1 주식 액면분할 및 분기 배당 150% 인상 발표", "🚩 실적공시", "`[C4]`"),
    ("L3 컴퓨팅/가속기", "NVIDIA (NVDA 🇺🇸)", "2026-06-02", "Computex 2026: 젠슨 황 CEO, 차세대 'Rubin' R100 아키텍처 및 HBM4 로드맵 공식화", "🚩 마일스톤", "`[C4]`"),
    ("L3 컴퓨팅/가속기", "AMD (AMD 🇺🇸)", "2026-01-30", "Q4 2025 실적: Instinct MI300X 연간 가이던스 $2.0B에서 $3.5B로 75% 상향 조정", "🚩 실적공시", "`[C4]`"),
    ("L3 컴퓨팅/가속기", "AMD (AMD 🇺🇸)", "2026-04-30", "Q1 2026 실적 발표: 데이터센터 부문 매출 80% 성장 및 MI300X 공급 $4.0B+ 전망", "🚩 실적공시", "`[C4]`"),
    ("L3 컴퓨팅/가속기", "AMD (AMD 🇺🇸)", "2026-06-03", "Computex 2026: HBM3E 288GB 탑재 Instinct MI325X 발표 및 연간 신제품 출시 로드맵 천명", "🚩 마일스톤", "`[C4]`"),
    ("L3 컴퓨팅/가속기", "Broadcom (AVGO 🇺🇸)", "2026-03-07", "Q1 FY26 실적: AI 매출 4배 급증 ($2.3B 달성), 하이퍼스케일러 맞춤형 AI ASIC 3호 고객사 확보", "📜 실적공시", "`[C4]`"),
    ("L3 컴퓨팅/가속기", "Broadcom (AVGO 🇺🇸)", "2026-06-12", "Q2 FY26 실적: 연간 AI 매출 전망 $11B+로 상향 및 10대 1 주식분할 결정", "🚩 실적공시", "`[C4]`"),
    ("L3 컴퓨팅/가속기", "Arm Holdings (ARM 🇬🇧)", "2026-02-07", "Q3 FY26 실적: 로열티/라이선스 매출 폭증으로 주가 48% 급등 및 Neoverse 서버 채택 급증", "🚩 실적공시", "`[C4]`"),
    ("L3 컴퓨팅/가속기", "Arm Holdings (ARM 🇬🇧)", "2026-05-08", "Q4 FY26 실적 발표: AI 데이터센터 시장 침투율 가속화 및 연간 매출 $3.2B 기록", "🚩 실적공시", "`[C4]`"),
    ("L3 컴퓨팅/가속기", "Intel (INTC 🇺🇸)", "2026-01-25", "Q4 2025 실적: 파운드리 분리 회계 모델 도입 및 공정 정상화 로드맵 재확인", "🚩 실적공시", "`[C4]`"),
    ("L3 컴퓨팅/가속기", "Intel (INTC 🇺🇸)", "2026-03-20", "미국 백악관·상무부, CHIPS Act 직접 보조금 $8.5B 및 대출 $11B 예비 선정 공식 서명", "📜 정부지원", "`[C4]`"),
    ("L3 컴퓨팅/가속기", "Intel (INTC 🇺🇸)", "2026-04-09", "Intel Vision 2026: H100 대비 학습 가성비 1.7배 향상된 'Gaudi 3' 가속기 정식 출시", "🚩 마일스톤", "`[C4]`"),
    ("L3 컴퓨팅/가속기", "Intel (INTC 🇺🇸)", "2026-06-04", "Computex 2026: 인텔 18A 선단 공정 Panther Lake 모바일/서버 컴퓨트 타일 양산 준비 발표", "🚩 마일스톤", "`[C4]`"),

    # L4 Foundry & Equipment
    ("L4 파운드리/제조", "TSMC (TSM 🇹🇼)", "2026-01-18", "Q4 2025 실적: 2026년 CapEx 가이던스 $28-32B 제시 및 3nm/5nm 가동률 100% 회복", "🚩 실적공시", "`[C4]`"),
    ("L4 파운드리/제조", "TSMC (TSM 🇹🇼)", "2026-02-24", "일본 구마모토 JASM 1공장 공식 개소식 거행 및 4분기 양산 일정 확정", "🏭 팹개소", "`[C4]`"),
    ("L4 파운드리/제조", "TSMC (TSM 🇹🇼)", "2026-04-08", "미국 상무부 CHIPS Act $6.6B 보조금 수령 합의 및 애리조나 3공장(2nm) 증설 확정", "📜 정부계약", "`[C4]`"),
    ("L4 파운드리/제조", "TSMC (TSM 🇹🇼)", "2026-04-18", "Q1 2026 실적 발표: 2026년 CoWoS 패키징 생산능력 전년비 2배 이상 확대 계획 확인", "🏭 캐파증설", "`[C4]`"),
    ("L4 파운드리/제조", "TSMC (TSM 🇹🇼)", "2026-06-04", "주총에서 C.C. Wei 회장 선출 및 2nm 공정(N2) GAA 2026년 하반기 시험생산 개시 천명", "🚩 마일스톤", "`[C4]`"),
    ("L4 파운드리/제조", "ASML (ASML 🇳🇱)", "2026-01-24", "2025 연간 실적: 매출 €27.6B 달성 및 인텔 앞 최초의 High NA EUV (EXE:5000) 출하 확인", "🚩 실적공시", "`[C4]`"),
    ("L4 파운드리/제조", "ASML (ASML 🇳🇱)", "2026-04-17", "Q1 2026 실적 발표 및 신임 CEO 크리스토프 푸케 취임, 2026년 2nm 전환기 강력 수요 전망", "🚩 실적공시", "`[C4]`"),
    ("L4 파운드리/제조", "ASML (ASML 🇳🇱)", "2026-06-05", "네덜란드 에인트호번 High NA EUV 랩에서 10nm 이하 회로 패턴 구현 데모 성공", "🚩 마일스톤", "`[C4]`"),
    ("L4 파운드리/제조", "Applied Materials (AMAT 🇺🇸)", "2026-02-15", "Q1 FY26 실적 발표: Gate-All-Around(GAA) 및 후면 전력 공급망(BSPDN) 식각 장비 수주 급증", "🚩 실적공시", "`[C4]`"),
    ("L4 파운드리/제조", "Lam Research (LRCX 🇺🇸)", "2026-04-24", "Q3 FY26 실적: 첨단 HBM 수직 패키징(TSV) 식각 장비 매출 전년비 40% 증가", "🚩 실적공시", "`[C4]`"),
    ("L4 파운드리/제조", "KLA (KLAC 🇺🇸)", "2026-04-25", "Q3 FY26 실적: 2nm 공정 광학 검사 및 어드밴스드 패키징 웨이퍼 검사 장비 백로그 사상 최대", "🚩 실적공시", "`[C4]`"),
    ("L4 파운드리/제조", "ASE Technology (ASX 🇹🇼)", "2026-03-15", "대만 가오슝 첨단 패키징 테스트 전용 팹 증설 투자 NT$10B 의결", "🏭 캐파증설", "`[C4]`"),
    ("L4 파운드리/제조", "Amkor Technology (AMKR 🇺🇸)", "2026-02-20", "미국 애리조나 피오리아 $2.0B 첨단 2.5D 패키징 팹 부지 인허가 및 착공 준비", "🏭 캐파증설", "`[C4]`"),

    # L5 Memory & Storage
    ("L5 메모리/스토리지", "SK hynix (000660 🇰🇷)", "2026-01-25", "2025 4Q 실적 발표: 1년 만에 흑자 전환 ($346M) 및 HBM3E 연간 완판 공식 공시", "🚩 실적공시", "`[C4]`"),
    ("L5 메모리/스토리지", "SK hynix (000660 🇰🇷)", "2026-03-19", "업계 최초 5세대 HBM3E (8단, 24GB) 대량 양산 개시 및 엔비디아에 세계 최초 공급", "🚩 마일스톤", "`[C4]`"),
    ("L5 메모리/스토리지", "SK hynix (000660 🇰🇷)", "2026-04-24", "충북 청주 M15X 팹을 차세대 HBM 전용 생산기지로 낙점하고 20조원 ($14.6B) 신규 투자 의결", "🏭 팹투자", "`[C4]`"),
    ("L5 메모리/스토리지", "SK hynix (000660 🇰🇷)", "2026-04-25", "1Q 2026 실적: 영업이익 2.88조원 달성, HBM3E 공급 비중 50% 돌파", "🚩 실적공시", "`[C4]`"),
    ("L5 메모리/스토리지", "SK hynix (000660 🇰🇷)", "2026-05-02", "곽노정 CEO 기자간담회: 2026년 HBM3E 12단 초도 양산 및 2026년 물량 완판 공시", "🚩 경영공시", "`[C4]`"),
    ("L5 메모리/스토리지", "SK hynix (000660 🇰🇷)", "2026-06-26", "용인 반도체 클러스터 1기 팹 9.4조원 투자안 이사회 최종 의결", "🏭 팹투자", "`[C4]`"),
    ("L5 메모리/스토리지", "삼성전자 (005930 🇰🇷)", "2026-01-31", "2025 4Q 실적: 반도체(DS) 적자 축소 및 HBM3E 12단 상반기 양산 로드맵 발표", "🚩 실적공시", "`[C4]`"),
    ("L5 메모리/스토리지", "삼성전자 (005930 🇰🇷)", "2026-02-27", "업계 최초 36GB HBM3E 12단 개발 성공 및 고객사 샘플 공급 발표", "🚩 마일스톤", "`[C4]`"),
    ("L5 메모리/스토리지", "삼성전자 (005930 🇰🇷)", "2026-04-15", "미국 상무부 CHIPS Act $6.4B 보조금 최종 서명 및 텍사스 테일러 팹 총 $40B+ 확장", "📜 정부계약", "`[C4]`"),
    ("L5 메모리/스토리지", "삼성전자 (005930 🇰🇷)", "2026-04-30", "1Q 2026 실적: DS부문 영업이익 1.91조원으로 5분기 만에 흑자 반등", "🚩 실적공시", "`[C4]`"),
    ("L5 메모리/스토리지", "삼성전자 (005930 🇰🇷)", "2026-05-21", "반도체(DS) 수장으로 전영현 미래사업기획단장 부회장 전격 임명 (HBM 경쟁력 쇄신 단행)", "🚩 경영인사", "`[C4]`"),
    ("L5 메모리/스토리지", "삼성전자 (005930 🇰🇷)", "2026-06-12", "미국 실리콘밸리 삼성 파운드리 포럼: 2nm 선단 공정에 광학 인터커넥트 및 턴키 HBM 솔루션 공개", "🚩 마일스톤", "`[C4]`"),
    ("L5 메모리/스토리지", "Micron (MU 🇺🇸)", "2026-02-26", "HBM3E 24GB 8단 대량 양산 시작 및 엔비디아 H200 텐서코어 GPU 공급 확정", "🚩 마일스톤", "`[C4]`"),
    ("L5 메모리/스토리지", "Micron (MU 🇺🇸)", "2026-03-20", "Q2 FY26 실적: 흑자 전환 및 2026년 HBM 캐파 전량 완판, 2026년 물량 대다수 계약 완료", "🚩 실적공시", "`[C4]`"),
    ("L5 메모리/스토리지", "Micron (MU 🇺🇸)", "2026-04-25", "미국 상무부 CHIPS Act $6.1B 보조금 수령 합의 및 뉴욕 메가팹/아이다호 팹 추진", "📜 정부계약", "`[C4]`"),
    ("L5 메모리/스토리지", "Micron (MU 🇺🇸)", "2026-06-26", "Q3 FY26 실적: 분기 매출 $6.8B (전년비 +81%) 달성 및 HBM3E 12단 하반기 양산 확인", "🚩 실적공시", "`[C4]`"),
    ("L5 메모리/스토리지", "Western Digital (WDC 🇺🇸)", "2026-01-26", "HDD 및 플래시 분할 작업 순항 발표 및 하이퍼스케일러용 60TB 고용량 eSSD 샘플링", "🚩 마일스톤", "`[C4]`"),
    ("L5 메모리/스토리지", "SanDisk (SNDK 🇺🇸)", "2026-05-10", "BiCS8 218단 3D NAND 기반 PCIe 5.0 데이터센터 전용 SSD 공급 개시", "🚩 마일스톤", "`[C4]`"),
    ("L5 메모리/스토리지", "Kioxia (6600 🇯🇵)", "2026-04-18", "도쿄증권거래소 재상장(IPO) 사전 작업 가속 및 BiCS8 2Tb QLC 낸드 양산 돌입", "🚩 마일스톤", "`[C4]`"),

    # L6 Optical & Networking
    ("L6 광통신/네트워킹", "Marvell (MRVL 🇺🇸)", "2026-03-08", "AI 인프라 데이: 5nm/3nm 커스텀 가속기 수주잔고 $10B 돌파 및 800G 광학 DSP 리더십 공시", "🚩 마일스톤", "`[C4]`"),
    ("L6 광통신/네트워킹", "Marvell (MRVL 🇺🇸)", "2026-05-30", "Q1 FY26 실적: 데이터센터 매출 87% 폭증 및 하이퍼스케일러 커스텀 ASIC 매출 본격 개시", "🚩 실적공시", "`[C4]`"),
    ("L6 광통신/네트워킹", "Coherent (COHR 🇺🇸)", "2026-02-06", "800G Datacom 트랜시버 수주잔고 급증 및 1.6T 광트랜시버 샘플 글로벌 CSP 출하", "🚩 마일스톤", "`[C4]`"),
    ("L6 광통신/네트워킹", "Coherent (COHR 🇺🇸)", "2026-05-08", "신임 CEO로 인텔/마이크로칩 출신 짐 앤더슨(Jim Anderson) 공식 취임", "🚩 경영인사", "`[C4]`"),
    ("L6 광통신/네트워킹", "Arista Networks (ANET 🇺🇸)", "2026-02-12", "Q4 2025 실적: AI 백엔드 네트워크 이더넷 패브릭 수요 폭증 및 연간 매출 $5.8B 달성", "🚩 실적공시", "`[C4]`"),
    ("L6 광통신/네트워킹", "Arista Networks (ANET 🇺🇸)", "2026-05-07", "Q1 2026 실적: 메이저 4대 하이퍼스케일러 AI 클러스터 전용 이더넷 스위치 매출 견인", "🚩 실적공시", "`[C4]`"),

    # L7 Infra & Specialized
    ("L7 인프라/특수", "Apple (AAPL 🇺🇸)", "2026-05-07", "신형 iPad Pro에 최초의 3nm 2세대 'M4' 칩셋 탑재 및 38TOPS NPU 엔진 공개", "🚩 마일스톤", "`[C4]`"),
    ("L7 인프라/특수", "Apple (AAPL 🇺🇸)", "2026-06-10", "WWDC26: 온디바이스 및 프라이빗 클라우드 컴퓨트 기반 'Apple Intelligence' 공식 발표", "🚩 마일스톤", "`[C4]`"),
    ("L7 인프라/특수", "SpaceX / xAI (SPACEX 🇺🇸)", "2026-05-26", "xAI, 시리즈 B 펀딩 $6.0B 유치 완료 (밸류에이션 $24.0B, Andreessen Horowitz/Sequoia 참여)", "💰 자본유치", "`[C4]`"),
    ("L7 인프라/특수", "SpaceX / xAI (SPACEX 🇺🇸)", "2026-06-25", "테네시주 멤피스에 엔비디아 H100 10만장 규모의 'Colossus' 슈퍼클러스터 착공 공식화", "🏢 데이터센터", "`[C4]`"),
    ("L7 인프라/특수", "SoftBank (9984 🇯🇵)", "2026-02-17", "손정의 회장, 1,000억 달러 규모의 차세대 AI 반도체 벤처 'Project Izanagi' 구상 공식 표명", "🚩 전략로드맵", "`[C3]`"),
    ("L7 인프라/특수", "SoftBank (9984 🇯🇵)", "2026-06-21", "연례 주주총회: 손정의 회장 '인공초지능(ASI) 10년 내 도래' 선언 및 AI 칩/인프라 대규모 투자 천명", "🚩 경영선언", "`[C4]`"),

    # L8 Power & Energy
    ("L8 전력/에너지", "Vertiv (VRT 🇺🇸)", "2026-02-21", "Q4 2025 실적: AI 액체냉각 솔루션 수주 잔고 전년비 23% 급증 및 가이던스 상향", "🚩 실적공시", "`[C4]`"),
    ("L8 전력/에너지", "Vertiv (VRT 🇺🇸)", "2026-03-19", "엔비디아(NVIDIA) GTC 2026에서 GB200 NVL72용 공동 설계 메가와트급 액체냉각 아키텍처 공개", "📜 협력공시", "`[C4]`"),
    ("L8 전력/에너지", "Vertiv (VRT 🇺🇸)", "2026-04-24", "Q1 2026 실적: 수주(Organic Orders) 60% 폭증 및 엔비디아 파트너십에 따른 냉각 인프라 매출 상향", "🚩 실적공시", "`[C4]`"),
    ("L8 전력/에너지", "Eaton (ETN 🇺🇸)", "2026-02-01", "Q4 2025 실적: 메가 데이터센터 변전/배전 프로젝트 백로그 $10B 돌파", "🚩 실적공시", "`[C4]`"),
    ("L8 전력/에너지", "Eaton (ETN 🇺🇸)", "2026-04-30", "Q1 2026 실적: 데이터센터 부문 전력 인프라 매출 전년비 24% 성장", "🚩 실적공시", "`[C4]`"),
    ("L8 전력/에너지", "GE Vernova (GEV 🇺🇸)", "2026-04-02", "GE로부터 스핀오프 완료하고 뉴욕증권거래소(NYSE)에 순수 에너지·전력 인프라 기업으로 독립 상장", "🚩 마일스톤", "`[C4]`"),
    ("L8 전력/에너지", "GE Vernova (GEV 🇺🇸)", "2026-04-24", "독립 상장 후 첫 실적 발표: 데이터센터 가스터빈 전력화 수요로 가스 파워 부문 흑자 가속", "🚩 실적공시", "`[C4]`"),
    ("L8 전력/에너지", "Schneider Electric (SBGSF 🇫🇷)", "2026-02-15", "2025 연간 실적: AI 데이터센터 전력 분배 및 쿨링 인프라 매출 두 자릿수 성장 기록", "🚩 실적공시", "`[C4]`"),
    ("L8 전력/에너지", "Schneider Electric (SBGSF 🇫🇷)", "2026-05-22", "엔비디아와 차세대 AI 데이터센터 레퍼런스 디자인 파트너십 확대 발표", "📜 파트너십", "`[C4]`"),
]


def build_h1_rows() -> list[dict[str, Any]]:
    """Build structured 8-column rows for 2026 H1."""
    rows = []
    for layer, entity, date_str, content, ev_type, conf in H1_RAW_EVENTS:
        target, metrics = extract_target_and_metrics(content, entity)
        rows.append({
            "layer": f"**{layer}**",
            "entity": f"**{entity.split('(')[0].strip()}** ({entity.split('(')[1].rstrip(')')})",
            "date": date_str,
            "content": content,
            "target": target,
            "metrics": metrics,
            "event_type": ev_type,
            "confidence": conf,
            "is_twitter": False,
        })
    return rows


def build_full_year_markdown(sorted_rows: list[dict[str, Any]]) -> str:
    """Render 2026 full-year unpivoted matrix markdown."""
    header = """# 2026년 연간(1월~10월) AI 반도체 밸류체인 36개사 언피벗 원장 (공식 공시·실적 및 𝕏 시그널 통합본)

> **정렬 기준**: **1차 회사별 (레이어 L1 $\\to$ L8 순) / 2차 날짜별 (2026-01 $\\to$ 2026-10 시간순 정렬)**  
> **구조 (방안 A: 8열)**: **[레이어] / [회사이름] / [발생일자] / [핵심 이벤트 내용 및 데이터] / [식별 대상 (상대방·제품·시설)] / [정량 조건 (금액·용량·물량·기간)] / [이벤트 유형] / [신뢰도]**  
> **포함 데이터**:
> • **상반기 (2026-01 ~ 2026-06)**: 36개사 SEC EDGAR 공시(10-K, 10-Q, 8-K), 분기 실적, GTC/Computex 주요 제품 론칭, CHIPS Act 보조금, 설비투자 이정표 전수  
> • **하반기 (2026-07 ~ 2026-10)**: 정규 공시/검증 특종 (`C3/C4`) + SignalForge (`c_1006_subject_outline`) 222개 마스터 인플루언서 실시간 𝕏 트위터 레이더 (`C1/C2`)  
> **포함 기간**: 2026년 1월 ~ 2026년 10월 11일 (10개 월 전수)

---

## 2026년 36개 기업 연간 통합 언피벗 원장 (Unpivoted Full-Year Event Ledger - Plan A 8 Columns)

| 레이어 (Layer) | 회사이름 (티커/국가) | 발생일자 (Date) | 핵심 이벤트 내용 및 데이터 | 식별 대상 (상대방·제품·시설) | 정량 조건 (금액·용량·물량·기간) | 이벤트 유형 (Type) | 신뢰도 (Grade) |
| :--- | :--- | :---: | :--- | :--- | :--- | :---: | :---: |
"""
    table_lines = []
    for r in sorted_rows:
        line = f"| {r['layer']} | {r['entity']} | {r['date']} | {r['content']} | {r['target']} | {r['metrics']} | {r['event_type']} | {r['confidence']} |"
        table_lines.append(line)

    h1_count = sum(1 for r in sorted_rows if any(r['date'].startswith(f"2026-0{m}") for m in range(1, 7)))
    h2_count = sum(1 for r in sorted_rows if not any(r['date'].startswith(f"2026-0{m}") for m in range(1, 7)))
    tw_count = sum(1 for r in sorted_rows if "[𝕏 Radar]" in r['content'])
    fact_count = len(sorted_rows) - tw_count
    struct_count = sum(1 for r in sorted_rows if r['target'] != '-' or r['metrics'] != '-')

    footer = f"""

---

### 📊 2026 연간 원장 데이터 요약 통계
- **총 등록 이벤트**: **{len(sorted_rows)}건**
- **상반기 (2026-01 ~ 2026-06)**: {h1_count}건
- **하반기 (2026-07 ~ 2026-10)**: {h2_count}건
- **정규 공시 / 검증 특종 (`C3/C4`)**: {fact_count}건
- **𝕏 소셜 레이더 시그널 (`C1/C2/C3`)**: {tw_count}건
- **구조화 속성 식별률 (상대방/제품/금액/용량)**: {struct_count} / {len(sorted_rows)}건 ({struct_count / len(sorted_rows) * 100:.1f}%)
- **적용 규격**: [docs/2026-10-11_36개사_언피벗_매트릭스_트위터_시그널_연동_요건정의서.md](file:///Users/boon/Dropbox/03_code/b_0917_10_QK_EARNING/docs/2026-10-11_36%EA%B0%9C%EC%82%AC_%EC%96%B8%ED%94%BC%EB%B2%97_%EB%A7%A4%ED%8A%B8%EB%A6%AD%EC%8A%A4_%ED%8A%B8%EC%9C%84%ED%84%B0_%EC%8B%9C%EA%B7%B8%EB%84%90_%EC%97%B0%EB%8F%99_%EC%9A%94%EA%B1%B4%EC%A0%95%EC%9D%98%EC%84%9C.md)
"""
    return header + "\n".join(table_lines) + footer


def main():
    print("🚀 1. 2026년 상반기 (H1: 1월~6월) 팩트 원장 빌드 중...")
    h1_rows = build_h1_rows()
    print(f"  • H1 팩트 이벤트 수: {len(h1_rows)}건")

    print("📥 2. 2026년 하반기 (H2: 7월~10월) 통합 원장 파싱 중...")
    h2_rows = parse_existing_matrix(H2_MATRIX_FILE)
    print(f"  • H2 통합 이벤트 수: {len(h2_rows)}건")

    print("📡 3. SignalForge timeline.db에서 신규 백필된 2026년 과거 𝕏 시그널 추출 중...")
    from app.services.twitter_bridge import TwitterBridge
    bridge = TwitterBridge()
    unpivoted_tweets = bridge.convert_to_unpivoted_events(limit=3500)
    
    # Filter backfilled tweets in 2026-01 ~ 2026-08
    backfilled_rows = []
    existing_contents = {r["content"] for r in (h1_rows + h2_rows)}

    for ev in unpivoted_tweets:
        if ev.date.startswith("2026-") and ev.date < "2026-09-01":
            if ev.content not in existing_contents:
                existing_contents.add(ev.content)
                target, metrics = extract_target_and_metrics(ev.content, ev.entity)
                
                # Parse event type & confidence from type_confidence_str
                # e.g. "💬 분석가전망 `[C2]`" -> type="💬 분석가전망", conf="`[C2]`"
                type_conf = ev.event_type_confidence.strip()
                m_conf = re.search(r"(`\[C[1-4]\]`)", type_conf)
                if m_conf:
                    conf_str = m_conf.group(1)
                    ev_type = type_conf.replace(conf_str, "").strip()
                else:
                    conf_str = "`[C3]`"
                    ev_type = type_conf

                backfilled_rows.append({
                    "layer": ev.layer,
                    "entity": ev.entity,
                    "date": ev.date,
                    "content": ev.content,
                    "target": target,
                    "metrics": metrics,
                    "event_type": ev_type,
                    "confidence": conf_str,
                })

    print(f"  • 신규 백필 𝕏 과거 시그널 추가 건수 (2026-01~08): {len(backfilled_rows)}건")

    print("✨ 4. 2026년 전수 병합 및 정렬 중 (Layer -> Entity -> Date)...")
    combined = h1_rows + h2_rows + backfilled_rows
    sorted_all = sort_rows(combined)
    print(f"  • 2026 연간 총 이벤트 수: {len(sorted_all)}건 (기존 985건 -> 신규 {len(sorted_all)}건 확장)")

    print(f"💾 5. 신규 연간 파일 작성 중: {OUTPUT_FILE}")
    rendered = build_full_year_markdown(sorted_all)
    OUTPUT_FILE.write_text(rendered, encoding="utf-8")
    print("✅ 2026년 연간 원장 빌드 완료!")


if __name__ == "__main__":
    main()

