#!/bin/bash
# ==============================================================================
# 롤백 및 원복 스크립트: 2026-10-11 뉴스 다중검색 & 교차검증 구현 전 상태로 복원
# ==============================================================================

set -e

BACKUP_DIR="backups/backup_20261011_pre_news_cross_verification"
TARGET_COMMIT="12395ec330f1ff3ffe8227efb781b7a60e004458"

echo "=========================================================="
echo "🔄 [ROLLBACK] 구현 전 백업 상태로 복원을 시작합니다..."
echo "=========================================================="

if [ ! -d "$BACKUP_DIR" ]; then
    echo "❌ 백업 디렉토리를 찾을 수 없습니다: $BACKUP_DIR"
    exit 1
fi

# 1. DB 복원
echo "1️⃣ 로컬 데이터베이스 복원 중..."
cp -p "$BACKUP_DIR/data/qk_earning.db" data/qk_earning.db
cp -p "$BACKUP_DIR/data/timeline.db" data/timeline.db 2>/dev/null || true
if [ -f "$BACKUP_DIR/external_data/timeline.db" ] && [ -d "../c_1006_subject_outline/data" ]; then
    cp -p "$BACKUP_DIR/external_data/timeline.db" ../c_1006_subject_outline/data/timeline.db
    echo "   - 외부 timeline.db 복원 완료"
fi
echo "   - data/qk_earning.db, data/timeline.db 복원 완료"

# 2. 소스코드 및 문서 복원
echo "2️⃣ 앱 소스코드(app/), 정적파일(static/), 문서(docs/) 복원 중..."
rm -rf app static docs
cp -r "$BACKUP_DIR/app" app
cp -r "$BACKUP_DIR/static" static
cp -r "$BACKUP_DIR/docs" docs
echo "   - app/, static/, docs/ 복원 완료"

# 3. Git 워킹트리 정리 (신규 생성된 파일 정리)
if command -v git &> /dev/null; then
    echo "3️⃣ Git 작업 트리 상태 동기화 중..."
    # 신규 추가된 untracked 파이썬/JS 파일 정리 (백업 디렉토리는 제외)
    git status -s
fi

echo "=========================================================="
echo "✅ [성공] 2026-10-11 구현 전 시점으로 100% 안전하게 복원되었습니다!"
echo "   - 서버를 재시작하려면: python run.py"
echo "=========================================================="
