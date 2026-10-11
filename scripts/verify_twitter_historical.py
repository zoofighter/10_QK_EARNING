#!/usr/bin/env python3
"""
Test script for verifying TwitterBridge with actual historical SignalForge data.
"""
import sys
from pathlib import Path
from collections import Counter

ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR))

from app.services.twitter_bridge import TwitterBridge


def run_test():
    print("=" * 80)
    print("🧪 1. SignalForge TwitterBridge 과거 데이터 연동 테스트 시작")
    print("=" * 80)

    bridge = TwitterBridge()
    print(f"📁 타겟 DB 경로: {bridge.db_path}")

    # 1. Fetch raw tweets
    raw_tweets = bridge.fetch_raw_tweets(limit=2000)
    print(f"📥 수집된 전체 𝕏 트윗 개수: {len(raw_tweets):,}건")

    if not raw_tweets:
        print("❌ 트윗 데이터가 없습니다.")
        return

    # 2. Convert to unpivoted events
    events = bridge.convert_to_unpivoted_events(limit=2000)
    print(f"🎯 36개 기업 엔티티 매칭 성공 이벤트: {len(events):,}건")

    # 3. Analyze breakdown by layer and entity
    layer_counter = Counter(ev.layer for ev in events)
    entity_counter = Counter(ev.entity for ev in events)
    conf_counter = Counter(ev.event_type_confidence for ev in events)

    print("\n📊 [레이어별 매칭 분포]")
    for layer, count in layer_counter.most_common():
        print(f"  • {layer}: {count}건")

    print("\n🏢 [상위 매칭 기업 Top 10]")
    for entity, count in entity_counter.most_common(10):
        print(f"  • {entity}: {count}건")

    print("\n🏷️ [신뢰도 등급 분포]")
    for conf, count in conf_counter.most_common():
        print(f"  • {conf}: {count}건")

    # 4. Print sample unpivoted markdown table
    print("\n" + "=" * 80)
    print("📋 [36개사 언피벗 매트릭스 변환 샘플 (최근 15건)]")
    print("=" * 80)
    print("| 레이어 (Layer) | 회사이름 (티커/국가) | 발생일자 (Date) | 핵심 이벤트 내용 및 데이터 | 이벤트 유형 & 신뢰도 |")
    print("| :--- | :--- | :---: | :--- | :---: |")
    for ev in events[:15]:
        print(f"| {ev.layer} | {ev.entity} | {ev.date} | {ev.content} | {ev.event_type_confidence} |")
    print("=" * 80)
    print("✅ 테스트 완료!")


if __name__ == "__main__":
    run_test()
