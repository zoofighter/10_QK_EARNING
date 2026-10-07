#!/usr/bin/env bash
# ==============================================================================
# b_0917_10_QK_EARNING Environment Setup Script (Cross-Machine Dropbox Support)
# 타 컴퓨터에서 드롭박스로 동기화 후 최초 1회 실행하여 가상환경을 자동 세팅합니다.
# ==============================================================================
set -e

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_NAME="b_0917_10_QK_EARNING"
VENV_TARGET="$HOME/.venv/$PROJECT_NAME"

echo "=================================================================="
echo "⚡ $PROJECT_NAME 가상환경 자동 셋업 (타 컴퓨터 드롭박스 동기화 지원)"
echo "• 프로젝트 위치: $PROJECT_DIR"
echo "• 타겟 가상환경: $VENV_TARGET"
echo "=================================================================="

# 1. ~/.venv 디렉터리 생성
mkdir -p "$HOME/.venv"

# 2. 가상환경 건전성 검사 (타 머신 복사본이거나 깨진 경우 자동 초기화)
NEED_INIT=0
if [ ! -f "$VENV_TARGET/bin/python" ]; then
    NEED_INIT=1
elif ! "$VENV_TARGET/bin/python" -c "import sys" &>/dev/null; then
    NEED_INIT=1
elif ! "$VENV_TARGET/bin/python" -m pip --version &>/dev/null; then
    NEED_INIT=1
fi

if [ "$NEED_INIT" -eq 1 ]; then
    echo "📦 현재 컴퓨터 환경에 맞춰 신규 가상환경 생성 중 (--clear)..."
    python3 -m venv --clear "$VENV_TARGET"
    echo "✓ 가상환경 생성 완료: $VENV_TARGET"
else
    echo "✓ 기존 유효 가상환경 확인 완료: $VENV_TARGET"
fi

# 3. 프로젝트 내 심볼릭 링크 (.venv) 갱신
echo "🔗 .venv 심볼릭 링크 갱신 중..."
rm -f "$PROJECT_DIR/.venv"
ln -s "$VENV_TARGET" "$PROJECT_DIR/.venv"
echo "✓ 연결 완료: $PROJECT_DIR/.venv -> $VENV_TARGET"

# 4. pip 업그레이드 및 requirements.txt 설치
echo "📥 필수 라이브러리 설치/검증 중 (requirements.txt)..."
"$VENV_TARGET/bin/python" -m pip install --upgrade pip --quiet
"$VENV_TARGET/bin/python" -m pip install -r "$PROJECT_DIR/requirements.txt" --quiet

echo "=================================================================="
echo "🎉 셋업이 성공적으로 완료되었습니다!"
echo "👉 실행 방법:"
echo "   source .venv/bin/activate"
echo "   python run.py"
echo "=================================================================="
