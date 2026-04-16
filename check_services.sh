#!/usr/bin/env bash
# ═══════════════════════════════════════════════════════════════════════════
# 🏥 Autonomous Multi-Agent AI Organization — Service Health Check
# Usage: ./check_services.sh
# ═══════════════════════════════════════════════════════════════════════════

# ── Colors ──────────────────────────────────────────────────────────────────
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
BOLD='\033[1m'
NC='\033[0m'

PASS="${GREEN}✅ UP       ${NC}"
FAIL="${RED}❌ DOWN     ${NC}"
WARN="${YELLOW}⚠️  UNHEALTHY${NC}"

pass=0; fail=0; warn=0

print_header() {
  echo ""
  echo -e "${BOLD}${BLUE}═══════════════════════════════════════════════════════════════${NC}"
  echo -e "${BOLD}${BLUE}  🤖 Autonomous Multi-Agent AI Org — Service Status Report${NC}"
  echo -e "${BOLD}${BLUE}═══════════════════════════════════════════════════════════════${NC}"
  echo ""
}

check_container() {
  local name="$1"
  local display="$2"
  local status
  status=$(docker inspect --format='{{.State.Status}}:{{if .State.Health}}{{.State.Health.Status}}{{else}}ok{{end}}' "$name" 2>/dev/null || echo "missing:missing")
  local state; state=$(echo "$status" | cut -d: -f1)
  local health; health=$(echo "$status" | cut -d: -f2)

  if   [[ "$state" == "missing" ]];                        then printf "  ${FAIL}  %-35s %s\n" "$display" "(not found)";        ((fail++))
  elif [[ "$state" == "running" && "$health" == "healthy" ]]; then printf "  ${PASS}  %-35s\n" "$display";                        ((pass++))
  elif [[ "$state" == "running" && "$health" == "ok" ]];   then printf "  ${PASS}  %-35s %s\n" "$display" "(no healthcheck)"; ((pass++))
  elif [[ "$state" == "running" ]];                        then printf "  ${WARN}  %-35s %s\n" "$display" "($health)";           ((warn++))
  else                                                          printf "  ${FAIL}  %-35s %s\n" "$display" "($state)";            ((fail++))
  fi
}

check_http() {
  local url="$1"
  local display="$2"
  local code
  code=$(curl -s -o /dev/null -w "%{http_code}" --max-time 3 "$url" 2>/dev/null || echo "000")
  if [[ "$code" =~ ^(200|204|301|302)$ ]]; then
    printf "  ${PASS}  %-35s %s\n" "$display" "[HTTP $code]";   ((pass++))
  else
    printf "  ${FAIL}  %-35s %s\n" "$display" "[HTTP $code — not reachable]"; ((fail++))
  fi
}

# ── Container name prefix ────────────────────────────────────────────────────
PREFIX="autonomousmulti-agentaiorganization-"

# ── Main Report ──────────────────────────────────────────────────────────────
print_header

echo -e "${BOLD}📊 System Resources${NC}"
echo -e "  RAM  : $(free -h | awk '/Mem:/ {print $3 " used / " $2 " total"}')"
echo -e "  Disk : $(df -h / | awk 'NR==2 {print $3 " used / " $2 " total (" $5 " full)"}')"
echo -e "  CPUs : $(nproc) cores"
echo ""

echo -e "${BOLD}🗄️  Infrastructure Services${NC}"
check_container "${PREFIX}postgres-1"  "PostgreSQL"
check_container "${PREFIX}redis-1"     "Redis"
check_container "${PREFIX}qdrant-1"    "Qdrant (Vector DB)"
echo ""

echo -e "${BOLD}📨 Message Bus${NC}"
check_container "${PREFIX}zookeeper-1" "Zookeeper"
check_container "${PREFIX}kafka-1"     "Kafka"
check_container "${PREFIX}kafka-ui-1"  "Kafka UI"
echo ""

echo -e "${BOLD}⚙️  Core Go Services${NC}"
check_container "${PREFIX}egress-proxy-1"  "Egress Proxy"
check_container "${PREFIX}orchestrator-1"  "Orchestrator (gRPC)"
check_container "${PREFIX}api-gateway-1"   "API Gateway"
check_container "${PREFIX}ws-hub-1"        "WebSocket Hub"
echo ""

echo -e "${BOLD}🤖 AI Agent Microservices${NC}"
check_container "${PREFIX}ceo-agent-1"           "CEO Agent"
check_container "${PREFIX}cto-agent-1"           "CTO Agent"
check_container "${PREFIX}engineer-backend-1"    "Engineer Backend Agent"
check_container "${PREFIX}engineer-frontend-1"   "Engineer Frontend Agent"
check_container "${PREFIX}qa-agent-1"            "QA Agent"
check_container "${PREFIX}devops-agent-1"        "DevOps Agent"
check_container "${PREFIX}finance-agent-1"       "Finance Agent"
echo ""

echo -e "${BOLD}🖥️  Dashboard${NC}"
check_container "${PREFIX}dashboard-1" "Next.js Dashboard"
echo ""

echo -e "${BOLD}📈 Observability Stack${NC}"
check_container "${PREFIX}prometheus-1" "Prometheus"
check_container "${PREFIX}grafana-1"    "Grafana"
check_container "${PREFIX}jaeger-1"     "Jaeger Tracing"
echo ""

echo -e "${BOLD}🌐 HTTP Endpoint Checks${NC}"
check_http "http://localhost:8080/health"  "API Gateway      :8080"
check_http "http://localhost:9091/healthz" "Orchestrator     :9091"
check_http "http://localhost:8082/healthz" "WS Hub           :8082"
check_http "http://localhost:3000"         "Dashboard        :3000"
check_http "http://localhost:6333/readyz"  "Qdrant           :6333"
check_http "http://localhost:9090"         "Prometheus       :9090"
check_http "http://localhost:3002"         "Grafana          :3002"
check_http "http://localhost:16686"        "Jaeger UI        :16686"
check_http "http://localhost:8888"         "Kafka UI         :8888"
echo ""

# ── Summary ──────────────────────────────────────────────────────────────────
total=$((pass + fail + warn))
echo -e "${BOLD}${BLUE}═══════════════════════════════════════════════════════════════${NC}"
echo -e "  ${BOLD}Summary:${NC}  ${GREEN}${pass} UP${NC}  |  ${YELLOW}${warn} UNHEALTHY${NC}  |  ${RED}${fail} DOWN${NC}  |  Total checked: ${total}"
echo -e "${BOLD}${BLUE}═══════════════════════════════════════════════════════════════${NC}"
echo ""

if [[ $fail -gt 0 || $warn -gt 0 ]]; then
  echo -e "${YELLOW}💡 To start all services:${NC}"
  echo -e "   docker compose up -d"
  echo ""
fi
