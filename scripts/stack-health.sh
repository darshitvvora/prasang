#!/usr/bin/env bash
# Checks every infrastructure service of the local stack. Exit 1 if any check fails.
# Usage: stack-health.sh [max-wait-seconds]  (default 90; retries until healthy or timeout)
set -u
deadline=$(( $(date +%s) + ${1:-90} ))
run_checks() {
fail=0
check() { local name=$1; shift; if "$@" >/dev/null 2>&1; then echo "OK   $name"; else echo "FAIL $name"; fail=1; fi; }

dbs=$(docker compose exec -T postgres psql -U prasang -d postgres -Atc "select string_agg(datname, ',' order by datname) from pg_database" 2>/dev/null)
for db in prasang prasang_test supertokens temporal temporal_visibility; do
  check "postgres db $db" grep -qw "$db" <<<"$dbs"
done
check "elasticsearch health" bash -c "curl -sf localhost:9200/_cluster/health | grep -Eq '\"status\":\"(green|yellow)\"'"
check "temporal namespace default" temporal operator namespace describe -n default --address localhost:7233
check "temporal ui" curl -sf localhost:8080
check "supertokens core" bash -c "curl -sf localhost:3567/hello | grep -q Hello"

}
while true; do
  out=$(run_checks)
  if ! grep -q '^FAIL' <<<"$out"; then echo "$out"; echo "STACK HEALTHY"; exit 0; fi
  if [ "$(date +%s)" -ge "$deadline" ]; then echo "$out"; echo "STACK UNHEALTHY"; exit 1; fi
  sleep 3
done
