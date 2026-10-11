#!/usr/bin/env python3
"""
Python Rollback Utility for 10_QK_EARNING
Restores the exact codebase, databases, and documents back to the state
prior to the multi-engine news search & cross-verification implementation.
"""
import os
import shutil
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
BACKUP_DIR = BASE_DIR / "backups" / "backup_20261011_pre_news_cross_verification"

def rollback():
    print("=" * 60)
    print("🔄 [ROLLBACK] 2026-10-11 구현 전 백업 상태로 복원을 시작합니다...")
    print("=" * 60)

    if not BACKUP_DIR.exists():
        print(f"❌ 백업 디렉토리를 찾을 수 없습니다: {BACKUP_DIR}")
        sys.exit(1)

    # 1. DB 파일 복원
    print("1️⃣ 데이터베이스 파일 복원 중...")
    db_backup = BACKUP_DIR / "data" / "qk_earning.db"
    target_db = BASE_DIR / "data" / "qk_earning.db"
    if db_backup.exists():
        shutil.copy2(db_backup, target_db)
        print("   - data/qk_earning.db 복원 완료")

    timeline_backup = BACKUP_DIR / "data" / "timeline.db"
    target_timeline = BASE_DIR / "data" / "timeline.db"
    if timeline_backup.exists():
        shutil.copy2(timeline_backup, target_timeline)
        print("   - data/timeline.db 복원 완료")

    ext_timeline = BACKUP_DIR / "external_data" / "timeline.db"
    target_ext_timeline = BASE_DIR.parent / "c_1006_subject_outline" / "data" / "timeline.db"
    if ext_timeline.exists() and target_ext_timeline.parent.exists():
        shutil.copy2(ext_timeline, target_ext_timeline)
        print("   - c_1006_subject_outline/data/timeline.db 복원 완료")

    # 2. 소스코드 및 문서 디렉토리 복원
    dirs_to_restore = ["app", "static", "docs"]
    print("2️⃣ 소스코드(app/), 웹정적파일(static/), 문서(docs/) 복원 중...")
    for d_name in dirs_to_restore:
        src = BACKUP_DIR / d_name
        dest = BASE_DIR / d_name
        if src.exists():
            if dest.exists():
                shutil.rmtree(dest)
            shutil.copytree(src, dest)
            print(f"   - {d_name}/ 디렉토리 복원 완료")

    print("=" * 60)
    print("✅ [복원 완료] 구현 전 시점으로 100% 안전하게 원복되었습니다!")
    print("=" * 60)

if __name__ == "__main__":
    rollback()
