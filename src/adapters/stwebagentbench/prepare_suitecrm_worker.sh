#!/usr/bin/env bash

set -euo pipefail

st_script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
st_repo_root="$(cd "${st_script_dir}/../../.." && pwd)"
st_compose_file="${st_repo_root}/external/ST-WebAgentBench/suitecrm_setup/docker-compose.yaml"
st_port="${SUITECRM_PORT:-8080}"
st_compose_cmd=(docker compose -f "${st_compose_file}")

if [[ -n "${GSE_COMPOSE_PROJECT:-}" ]]; then
  st_compose_cmd=(docker compose -p "${GSE_COMPOSE_PROJECT}" -f "${st_compose_file}")
fi

"${st_compose_cmd[@]}" up -d --pull never mariadb suitecrm

for st_attempt in {1..120}; do
  if "${st_compose_cmd[@]}" logs suitecrm 2>/dev/null \
      | grep -F '** SuiteCRM setup finished! **' >/dev/null \
      && curl -fsS "http://127.0.0.1:${st_port}" >/dev/null; then
    exit 0
  fi
  if [[ "${st_attempt}" -eq 120 ]]; then
    echo "SuiteCRM worker did not become ready on port ${st_port}." >&2
    exit 1
  fi
  sleep 2
done
