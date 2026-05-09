#!/usr/bin/env bash
# Smoke test — verifies all JARVIS API endpoints return valid envelopes.
# Usage: ./scripts/smoke_test.sh [gateway_url]
# Default gateway: http://localhost:8000

set -euo pipefail

GATEWAY="${1:-http://localhost:8000}"
PASS=0
FAIL=0
SKIP=0

GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[0;33m'
RESET='\033[0m'

pass() { echo -e "${GREEN}  PASS${RESET}  $1"; ((PASS++)); }
fail() { echo -e "${RED}  FAIL${RESET}  $1: $2"; ((FAIL++)); }
skip() { echo -e "${YELLOW}  SKIP${RESET}  $1: $2"; ((SKIP++)); }

# Returns "ok" field from JSON response
ok_field() { echo "$1" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('ok','false'))" 2>/dev/null || echo "false"; }

check_get() {
  local name="$1" path="$2"
  local url="${GATEWAY}${path}"
  local resp http_code body
  http_code=$(curl -s -o /tmp/jarvis_smoke.json -w "%{http_code}" \
    -H "X-Request-ID: smoke-$$" \
    -H "X-Session-ID: smoke-session" \
    -H "X-Client-Version: 0.0.1" \
    "${url}" 2>/dev/null) || { fail "${name}" "curl error"; return; }
  body=$(cat /tmp/jarvis_smoke.json)
  if [[ "${http_code}" =~ ^[245] ]]; then
    local ok
    ok=$(ok_field "${body}")
    if [[ "${ok}" == "True" || "${ok}" == "true" ]]; then
      pass "${name} (${http_code})"
    else
      fail "${name}" "ok=false, HTTP ${http_code}, body=${body:0:120}"
    fi
  else
    fail "${name}" "HTTP ${http_code}"
  fi
}

check_post() {
  local name="$1" path="$2" payload="$3"
  local url="${GATEWAY}${path}"
  local http_code body
  http_code=$(curl -s -o /tmp/jarvis_smoke.json -w "%{http_code}" \
    -X POST \
    -H "Content-Type: application/json" \
    -H "X-Request-ID: smoke-$$" \
    -H "X-Session-ID: smoke-session" \
    -H "X-Client-Version: 0.0.1" \
    -d "${payload}" \
    "${url}" 2>/dev/null) || { fail "${name}" "curl error"; return; }
  body=$(cat /tmp/jarvis_smoke.json)
  if [[ "${http_code}" =~ ^[245] ]]; then
    local ok
    ok=$(ok_field "${body}")
    if [[ "${ok}" == "True" || "${ok}" == "true" ]]; then
      pass "${name} (${http_code})"
    else
      fail "${name}" "ok=false, HTTP ${http_code}, body=${body:0:120}"
    fi
  else
    fail "${name}" "HTTP ${http_code}"
  fi
}

echo ""
echo "JARVIS smoke test — gateway: ${GATEWAY}"
echo "─────────────────────────────────────────"

# ── Health ────────────────────────────────────────────────────────────────────
check_get "health"              "/api/health"

# ── Bootstrap ─────────────────────────────────────────────────────────────────
check_get "bootstrap"           "/api/bootstrap"

# ── System ────────────────────────────────────────────────────────────────────
check_get "system/status"       "/api/system/status"
check_get "system/metrics"      "/api/system/metrics"

# ── GPU ───────────────────────────────────────────────────────────────────────
check_get "gpu/status"          "/api/gpu/status"
check_get "gpu/workloads"       "/api/gpu/workloads"

# ── Providers ─────────────────────────────────────────────────────────────────
check_get "providers"           "/api/providers"

# ── Models ────────────────────────────────────────────────────────────────────
check_get "models"              "/api/models"

# ── Chat ──────────────────────────────────────────────────────────────────────
check_get  "chat/history"       "/api/chat/history"
check_post "chat/completions"   "/api/chat/completions" \
  '{"messages":[{"role":"user","content":"ping"}],"stream":false}'

# ── Voice ─────────────────────────────────────────────────────────────────────
check_get "voice/status"        "/api/voice/status"

# ── Memory ────────────────────────────────────────────────────────────────────
check_get  "memory/status"      "/api/memory/status"
check_post "memory/search"      "/api/memory/search"      '{"query":"test","topK":3}'
check_post "memory/store"       "/api/memory/store"       '{"content":"smoke test entry"}'

# ── Execution ─────────────────────────────────────────────────────────────────
check_get  "execution/status"   "/api/execution/status"
check_post "execution/run"      "/api/execution/run"      '{"language":"python","code":"print(42)"}'

# ── Tools ─────────────────────────────────────────────────────────────────────
check_get "tools"               "/api/tools"

# ── Search ────────────────────────────────────────────────────────────────────
check_get  "search/status"      "/api/search/status"
check_post "search"             "/api/search"             '{"query":"hello world","maxResults":3}'

# ── Vision ────────────────────────────────────────────────────────────────────
check_get "vision/status"       "/api/vision/status"

# ── Self-improvement ──────────────────────────────────────────────────────────
check_get "self-improvement/status"      "/api/self-improvement/status"
check_get "self-improvement/suggestions" "/api/self-improvement/suggestions"

# ── Local actions ─────────────────────────────────────────────────────────────
check_get  "local-actions"        "/api/local-actions"
check_get  "local-actions/pending" "/api/local-actions/pending"

# ── Monitoring ────────────────────────────────────────────────────────────────
check_get "monitoring/metrics"  "/api/monitoring/metrics"

echo ""
echo "─────────────────────────────────────────"
printf "Results: ${GREEN}%d passed${RESET}  ${RED}%d failed${RESET}  ${YELLOW}%d skipped${RESET}\n" \
  "${PASS}" "${FAIL}" "${SKIP}"
echo ""

[[ "${FAIL}" -eq 0 ]]
