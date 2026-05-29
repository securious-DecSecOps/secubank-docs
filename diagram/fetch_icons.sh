#!/usr/bin/env bash
# 도구 로고를 icons/ 에 받는다. 실패해도 architecture.py가 라벨 박스로 폴백하므로 안전.
# slug는 architecture.py의 tool(..., "slug") 와 반드시 일치해야 함.
set -u
cd "$(dirname "$0")"
mkdir -p icons
get() {
  if curl -fsSL "$2" -o "icons/$1.png" 2>/dev/null; then
    echo "ok   : $1"
  else
    rm -f "icons/$1.png"
    echo "miss : $1  (수동으로 icons/$1.png 넣으면 실제 로고로 표시)"
  fi
}

# --- CNCF artwork (비교적 안정적) ---
get cilium    "https://raw.githubusercontent.com/cncf/artwork/main/projects/cilium/icon/color/cilium_icon-color.png"
get falco     "https://raw.githubusercontent.com/cncf/artwork/main/projects/falco/icon/color/falco-icon-color.png"
get kubescape "https://raw.githubusercontent.com/cncf/artwork/main/projects/kubescape/icon/color/kubescape-icon-color.png"

# --- best-effort (실패 가능, 그땐 수동) ---
get sonarqube "https://raw.githubusercontent.com/SonarSource/sonarqube/master/server/sonar-web/public/apple-touch-icon.png"
get zap       "https://raw.githubusercontent.com/zaproxy/zaproxy/main/zap/src/main/resources/resource/zap1024x1024.png"

echo "---"
echo "받은 로고:"; ls -1 icons/ 2>/dev/null || echo "(없음)"
echo ""
echo "슬러그 목록(필요시 수동으로 icons/<slug>.png): sonarqube gitleaks checkov kubescape syft cilium falco zap defectdojo"
echo "없는 건 다이어그램에서 라벨 박스로 표시됩니다."
