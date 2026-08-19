#!/usr/bin/env bash

set -euo pipefail

st_script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
st_repo_root="$(cd "${st_script_dir}/../../.." && pwd)"

st_compose_file="${st_repo_root}/external/ST-WebAgentBench/suitecrm_setup/docker-compose.yaml"
st_snapshot="${st_repo_root}/artifacts/stweb_suitecrm_poc_v01/db/suitecrm_pristine_v01.sql"
st_compose_cmd=(docker compose -f "${st_compose_file}")

if [[ -n "${GSE_COMPOSE_PROJECT:-}" ]]; then
  st_compose_cmd=(docker compose -p "${GSE_COMPOSE_PROJECT}" -f "${st_compose_file}")
fi

cd "${st_repo_root}"

if [[ ! -s "${st_snapshot}" ]]; then
  echo "Database snapshot is missing or empty: ${st_snapshot}" >&2
  exit 1
fi

"${st_compose_cmd[@]}" up -d --pull never mariadb suitecrm

"${st_compose_cmd[@]}" exec -T mariadb \
  mariadb -u root < "${st_snapshot}"

st_counts="$(
  "${st_compose_cmd[@]}" exec -T mariadb \
    mariadb -u root -Nse \
    "SELECT
       (SELECT COUNT(*) FROM bitnami_suitecrm.contacts WHERE deleted=0),
       (SELECT COUNT(*) FROM bitnami_suitecrm.accounts WHERE deleted=0),
       (SELECT COUNT(*) FROM bitnami_suitecrm.leads WHERE deleted=0);"
)"

if [[ "${st_counts}" != $'10\t9\t10' ]]; then
  echo "Unexpected restored database counts: ${st_counts}" >&2
  exit 1
fi

echo "SuiteCRM database restored successfully: ${st_counts}"
