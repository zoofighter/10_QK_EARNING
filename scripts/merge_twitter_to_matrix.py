#!/usr/bin/env python3
"""
Merge curated Twitter radar events from SignalForge into 36entities_jul_aug_sep_oct_layer_matrix.md.
Implements Plan A: 8 columns format separating:
- 식별 대상 (상대방·제품·시설)
- 정량 조건 (금액·용량·물량·기간)
- 이벤트 유형 (Type)
- 신뢰도 (Grade)
Sorts by Layer -> Entity -> Date.
"""
import re
import sys
from pathlib import Path
from typing import Any

ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR))

from app.services.twitter_bridge import TwitterBridge


MATRIX_FILE = ROOT_DIR / "docs" / "2026-10-11_36entities_jul_aug_sep_oct_layer_matrix.md"
ORIGINAL_MATRIX_FILE = ROOT_DIR / "docs" / "2026-10-11_36entities_jul_aug_sep_oct_layer_matrix copy.md"


def split_type_and_confidence(val: str) -> tuple[str, str]:
    """Split a combined type & confidence string like '🚩 마일스톤 `[C4]`' into type and grade."""
    val = val.strip()
    match = re.search(r"^(.*?)\s*(`?\[C[1-4]\]`?)$", val)
    if match:
        ev_type = match.group(1).strip()
        conf = match.group(2).strip()
        if not conf.startswith("`"):
            conf = f"`{conf}`"
        return ev_type, conf
    return val, "`[C1]`"


def extract_target_and_metrics(content: str, current_entity: str) -> tuple[str, str]:
    """
    Extract structured target (counterparty, product, facility)
    and quantitative metrics (amount, capacity, volume, term) from text.
    """
    text_lower = content.lower()
    current_ent_lower = current_entity.lower()

    # 1. Counterparties (exclude current entity itself)
    counterparties = [
        ("OpenAI", ["openai", "오픈ai"]),
        ("Anthropic", ["anthropic", "앤트로픽"]),
        ("Microsoft", ["microsoft", "msft", "마이크로소프트", "azure"]),
        ("Amazon", ["amazon", "aws", "아마존"]),
        ("Google", ["google", "alphabet", "구글"]),
        ("Meta", ["meta", "메타"]),
        ("Oracle", ["oracle", "오라클", "oci"]),
        ("CoreWeave", ["coreweave", "코어위브"]),
        ("Nebius", ["nebius", "네비우스"]),
        ("NVIDIA", ["nvidia", "엔비디아"]),
        ("AMD", ["amd"]),
        ("Broadcom", ["broadcom", "브로드컴"]),
        ("Intel", ["intel", "인텔"]),
        ("TSMC", ["tsmc"]),
        ("ASML", ["asml"]),
        ("Applied Materials", ["applied materials", "어플라이드"]),
        ("Lam Research", ["lam research", "램리서치"]),
        ("KLA", ["kla"]),
        ("ASE", ["ase", "asx", "일월광"]),
        ("Amkor", ["amkor", "앰코"]),
        ("SK hynix", ["sk hynix", "sk하이닉스", "hynix"]),
        ("Samsung", ["samsung", "삼성전자"]),
        ("Micron", ["micron", "마이크론"]),
        ("Western Digital", ["western digital", "웨스턴"]),
        ("Kioxia", ["kioxia", "키옥시아"]),
        ("Marvell", ["marvell", "마벨"]),
        ("Arista", ["arista", "아리스타"]),
        ("Apple", ["apple", "애플"]),
        ("xAI", ["xai"]),
        ("Tesla", ["tesla", "테슬라"]),
        ("Vertiv", ["vertiv", "버티브"]),
        ("Constellation", ["constellation", "콘스텔레이션"]),
        ("Talen Energy", ["talen", "탈렌"]),
        ("Kairos Power", ["kairos", "카이로스"]),
        ("Lambda", ["lambda", "람다"]),
        ("Hut 8", ["hut 8"]),
        ("Humat Al-Watan", ["humat al-watan"]),
        ("Toshiba", ["toshiba", "도시바"]),
        ("Seagate", ["seagate", "씨게이트"]),
    ]

    matched_cps = []
    for cp_name, aliases in counterparties:
        if any(alias in current_ent_lower for alias in aliases):
            continue  # Don't tag self as counterparty
        if any(alias in text_lower for alias in aliases):
            matched_cps.append(cp_name)

    # 2. Products / Technologies
    products = [
        ("3nm Custom ASIC", ["3nm 맞춤형", "3nm custom", "custom asic", "독자 asic", "3nm asic"]),
        ("2nm GAA", ["2nm 파운드리", "2nm process", "2nm 공정", "2nm 파일럿", "2nm"]),
        ("18A 공정", ["18a", "intel 18a"]),
        ("Blackwell B200", ["blackwell b200", "b200", "blackwell"]),
        ("GB200 NVL72", ["gb200 nvl72", "gb200", "nvl72"]),
        ("Rubin R100", ["rubin r100", "rubin", "r100"]),
        ("MI300X", ["mi300x", "mi300"]),
        ("MI325X", ["mi325x", "mi325"]),
        ("MI350X", ["mi350x", "mi350"]),
        ("Trainium2", ["trainium2", "trainium", "tr3.5", "tr4"]),
        ("TPU v6p", ["tpu v6p", "trillium"]),
        ("TPU v5p", ["tpu v5p"]),
        ("TPU v8t", ["tpu v8t"]),
        ("TPU", ["tpu"]),
        ("HBM3E", ["hbm3e"]),
        ("HBM4", ["hbm4"]),
        ("HBM", ["hbm"]),
        ("MTIA", ["mtia"]),
        ("Claude 3.7", ["claude 3.7"]),
        ("Claude 3.5", ["claude 3.5"]),
        ("Llama 4", ["llama 4"]),
        ("Llama 3.1", ["llama 3.1"]),
        ("GPT-4o", ["gpt-4o"]),
        ("CoWoS", ["cowos"]),
        ("High NA EUV", ["high na"]),
        ("EUV/DUV", ["euv", "duv"]),
        ("800G 광스위치", ["800g"]),
        ("액체냉각 CDU", ["액체냉각", "액체 냉각", "수랭", "cdu", "liquid cooling"]),
        ("SMR 소형원전", ["smr", "소형원전"]),
        ("원전 PPA", ["원전 ppa", "원전"]),
        ("가스터빈", ["가스터빈", "7ha"]),
    ]

    matched_prods = []
    for prod_name, aliases in products:
        if any(alias in text_lower for alias in aliases):
            matched_prods.append(prod_name)
            if len(matched_prods) >= 2:
                break

    # 3. Facilities
    facilities = [
        ("평택 P4", ["평택 p4", "p4"]),
        ("테일러 팹", ["테일러", "taylor"]),
        ("용인 클러스터", ["용인"]),
        ("마운트 플레전트 1GW", ["마운트 플레전트"]),
        ("Crane 3마일 원전", ["crane", "3마일"]),
        ("서스퀘하나 원전", ["서스퀘하나"]),
        ("프로메테우스 1.2GW", ["프로메테우스"]),
        ("오하이오 DC", ["오하이오"]),
        ("헬싱키 DC", ["헬싱키"]),
        ("암스테르담 DC", ["암스테르담"]),
        ("Colossus DC", ["colossus"]),
        ("Terafab", ["terafab"]),
    ]

    matched_facs = []
    for fac_name, aliases in facilities:
        if any(alias in text_lower for alias in aliases):
            matched_facs.append(fac_name)
            if len(matched_facs) >= 1:
                break

    # Assemble Target Column
    target_parts = []
    if matched_cps:
        target_parts.append(f"상대: {', '.join(matched_cps[:2])}")
    if matched_prods:
        target_parts.append(f"제품: {', '.join(matched_prods[:2])}")
    if matched_facs:
        target_parts.append(f"시설: {', '.join(matched_facs[:1])}")
    target_str = " | ".join(target_parts) if target_parts else "-"

    # 4. Quantitative Metrics
    # Amount: $65.0B, $280B, €13BN, $500M
    amounts = re.findall(r"[\$€][\d\.]+\s*(?:B|M|K|BN)?", content)
    # Power / Capacity: 835MW, 1GW, 200MW, 60 GW, 1.5GW
    powers = re.findall(r"\b\d+(?:\.\d+)?\s*(?:GW|MW|kW|WSPM)\b", content, re.IGNORECASE)
    # Volume: 5만장, 10만장, 115K Rubins, 1.5 million units, 50k GPU
    volumes = re.findall(
        r"\b\d+(?:,\d+)?(?:\.\d+)?\s*(?:만장|장|만개|개|k\s*(?:gpus?|units?|chips?|b200|rubins?)|million\s*(?:gpus?|units?|chips?))\b",
        content,
        re.IGNORECASE
    )
    # Term: 20년 PPA, 20년, 2031년, CY27
    terms = re.findall(r"\b(?:\d+년(?:\s*PPA)?|CY\d{2}|through\s*\d{4})\b", content, re.IGNORECASE)

    metric_parts = []
    if amounts:
        metric_parts.append(f"금액: {amounts[0].strip()}")
    if powers:
        metric_parts.append(f"용량: {powers[0].strip()}")
    if volumes:
        metric_parts.append(f"물량: {volumes[0].strip()}")
    if terms:
        metric_parts.append(f"기간: {terms[0].strip()}")
    metric_str = " | ".join(metric_parts) if metric_parts else "-"

    return target_str, metric_str


def parse_existing_matrix(filepath: Path) -> list[dict[str, Any]]:
    """Parse existing markdown matrix table into row dicts."""
    lines = filepath.read_text(encoding="utf-8").splitlines()
    rows = []
    in_table = False

    for line in lines:
        line_clean = line.strip()
        if line_clean.startswith("| 레이어") or line_clean.startswith("| Layer"):
            in_table = True
            continue
        if in_table and line_clean.startswith("| :---"):
            continue
        if in_table and line_clean.startswith("|"):
            parts = [p.strip() for p in line_clean.split("|")[1:-1]]
            if len(parts) >= 8:
                rows.append({
                    "layer": parts[0],
                    "entity": parts[1],
                    "date": parts[2],
                    "content": parts[3],
                    "target": parts[4],
                    "metrics": parts[5],
                    "event_type": parts[6],
                    "confidence": parts[7],
                    "is_twitter": False,
                })
            elif len(parts) >= 6:
                target, metrics = extract_target_and_metrics(parts[3], parts[1])
                rows.append({
                    "layer": parts[0],
                    "entity": parts[1],
                    "date": parts[2],
                    "content": parts[3],
                    "target": target,
                    "metrics": metrics,
                    "event_type": parts[4],
                    "confidence": parts[5],
                    "is_twitter": False,
                })
            elif len(parts) == 5:
                ev_type, conf = split_type_and_confidence(parts[4])
                target, metrics = extract_target_and_metrics(parts[3], parts[1])
                rows.append({
                    "layer": parts[0],
                    "entity": parts[1],
                    "date": parts[2],
                    "content": parts[3],
                    "target": target,
                    "metrics": metrics,
                    "event_type": ev_type,
                    "confidence": conf,
                    "is_twitter": False,
                })

    return rows


def get_curated_twitter_events() -> list[dict[str, Any]]:
    """Fetch and filter high-value Twitter events from SignalForge."""
    bridge = TwitterBridge()
    events = bridge.convert_to_unpivoted_events(limit=2000)

    curated = []
    seen_contents = set()

    signal_keywords = [
        "hbm", "cowos", "packaging", "capacity", "wafer", "n2", "3nm", "blackwell", "rubin",
        "mi300", "mi325", "mi350", "18a", "tpu", "trainium", "llama", "euv", "duv", "fab",
        "contract", "deal", "pricing", "delay", "capex", "cluster", "gpu", "terafab",
        "asic", "ppa", "smr", "order", "shipment", "guidance", "yield"
    ]

    for ev in events:
        content_lower = ev.content.lower()

        if not (ev.date.startswith("2026-07") or ev.date.startswith("2026-08") or
                ev.date.startswith("2026-09") or ev.date.startswith("2026-10")):
            continue

        has_signal = any(kw in content_lower for kw in signal_keywords)
        is_high_tier = "C2" in ev.event_type_confidence or "C3" in ev.event_type_confidence

        if not (has_signal or is_high_tier):
            continue

        snippet_key = (ev.entity, ev.content[:60])
        if snippet_key in seen_contents:
            continue
        seen_contents.add(snippet_key)

        ev_type, conf = split_type_and_confidence(ev.event_type_confidence)
        target, metrics = extract_target_and_metrics(ev.content, ev.entity)

        curated.append({
            "layer": ev.layer,
            "entity": ev.entity,
            "date": ev.date,
            "content": ev.content,
            "target": target,
            "metrics": metrics,
            "event_type": ev_type,
            "confidence": conf,
            "is_twitter": True,
        })

    return curated


def clean_sort_key(entity_str: str) -> str:
    """Extract clean entity name for sorting."""
    match = re.search(r"\*\*(.*?)\*\*", entity_str)
    return match.group(1) if match else entity_str


def sort_rows(all_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Sort rows primarily by layer order (L1->L8), entity name, then date."""
    layer_order = {
        "L1": 1, "L2": 2, "L3": 3, "L4": 4, "L5": 5, "L6": 6, "L7": 7, "L8": 8
    }

    def row_key(r):
        layer_num = 99
        for k, v in layer_order.items():
            if k in r["layer"]:
                layer_num = v
                break
        ent_name = clean_sort_key(r["entity"])
        date_str = r["date"]
        if len(date_str) == 7:
            date_str += "-00"
        return (layer_num, ent_name, date_str)

    return sorted(all_rows, key=row_key)


def render_markdown(sorted_rows: list[dict[str, Any]]) -> str:
    """Render markdown document with 8-column unpivoted ledger (Plan A)."""
    header = """# 2026년 7·8·9·10월 AI 반도체 밸류체인 36개사 언피벗 원장 (𝕏 트위터 시그널 및 구조화 컬럼 통합본)

> **정렬 기준**: **1차 회사별 (레이어 L1 $\\to$ L8 순) / 2차 날짜별 (2026-07 $\\to$ 2026-10 시간순 정렬)**  
> **구조 (방안 A: 8열)**: **[레이어] / [회사이름] / [발생일자] / [핵심 이벤트 내용 및 데이터] / [식별 대상 (상대방·제품·시설)] / [정량 조건 (금액·용량·물량·기간)] / [이벤트 유형] / [신뢰도]**  
> **포함 데이터**:
> • **정규 팩트 데이터 (`C3/C4`)**: SEC EDGAR 공시, 기업 IR 보도자료, 메이저 언론 검증 특종  
> • **𝕏 소셜 레이더 데이터 (`C1/C2`)**: SignalForge (`c_1006_subject_outline`) 222개 마스터 인플루언서 타임라인 실시간 추출 신호  
> **포함 기간**: 2026년 7월, 8월, 9월, 10월(10/1~10/11) 4개 월 전수

---

## 36개 기업 통합 이벤트 언피벗 원장 (Unpivoted Event Ledger - Plan A 8 Columns)

| 레이어 (Layer) | 회사이름 (티커/국가) | 발생일자 (Date) | 핵심 이벤트 내용 및 데이터 | 식별 대상 (상대방·제품·시설) | 정량 조건 (금액·용량·물량·기간) | 이벤트 유형 (Type) | 신뢰도 (Grade) |
| :--- | :--- | :---: | :--- | :--- | :--- | :---: | :---: |
"""
    table_lines = []
    for r in sorted_rows:
        line = f"| {r['layer']} | {r['entity']} | {r['date']} | {r['content']} | {r['target']} | {r['metrics']} | {r['event_type']} | {r['confidence']} |"
        table_lines.append(line)

    footer = f"""

---

### 📊 데이터 요약 통계
- **총 등록 이벤트**: {len(sorted_rows)}건
- **정규 공시/검증 보도 (`C3/C4`)**: {sum(1 for r in sorted_rows if not r['is_twitter'])}건
- **𝕏 트위터 레이더 (`C1/C2/C3`)**: {sum(1 for r in sorted_rows if r['is_twitter'])}건
- **구조화 속성 식별률**: {sum(1 for r in sorted_rows if r['target'] != '-' or r['metrics'] != '-')} / {len(sorted_rows)}건 ({sum(1 for r in sorted_rows if r['target'] != '-' or r['metrics'] != '-') / len(sorted_rows) * 100:.1f}%)
- **적용 규칙**: [docs/2026-10-11_36개사_언피벗_매트릭스_트위터_시그널_연동_요건정의서.md](file:///Users/boon/Dropbox/03_code/b_0917_10_QK_EARNING/docs/2026-10-11_36%EA%B0%9C%EC%82%AC_%EC%96%B8%ED%94%BC%EB%B2%97_%EB%A7%A4%ED%8A%B8%EB%A6%AD%EC%8A%A4_%ED%8A%B8%EC%9C%84%ED%84%B0_%EC%8B%9C%EA%B7%B8%EB%84%90_%EC%97%B0%EB%8F%99_%EC%9A%94%EA%B1%B4%EC%A0%95%EC%9D%98%EC%84%9C.md)
"""
    return header + "\n".join(table_lines) + footer


def main():
    print("🚀 기존 순수 매트릭스 파싱 및 구조화 추출 중...")
    target_parse_file = ORIGINAL_MATRIX_FILE if ORIGINAL_MATRIX_FILE.exists() else MATRIX_FILE
    existing = parse_existing_matrix(target_parse_file)
    print(f"  • 기준 정규 이벤트: {len(existing)}건")

    print("🛰️ SignalForge 트위터 이벤트 수집 및 구조화 추출 중...")
    twitter_events = get_curated_twitter_events()
    print(f"  • 선별된 트위터 레이더 이벤트: {len(twitter_events)}건")

    combined = existing + twitter_events
    sorted_all = sort_rows(combined)
    print(f"✨ 최종 병합된 이벤트: {len(sorted_all)}건")

    rendered = render_markdown(sorted_all)
    MATRIX_FILE.write_text(rendered, encoding="utf-8")
    print(f"💾 8열 구조화 원장 파일 업데이트 완료: {MATRIX_FILE}")


if __name__ == "__main__":
    main()
