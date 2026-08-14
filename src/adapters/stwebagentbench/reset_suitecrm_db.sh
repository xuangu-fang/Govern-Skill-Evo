#!/usr/bin/env bash

set -euo pipefail

st_script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
st_repo_root="$(cd "${st_script_dir}/../../.." && pwd)"

st_compose_file="${st_repo_root}/external/ST-WebAgentBench/suitecrm_setup/docker-compose.yaml"
st_snapshot="${st_repo_root}/artifacts/stweb_suitecrm_poc_v01/db/suitecrm_pristine_v01.sql"

cd "${st_repo_root}"

if [[ ! -s "${st_snapshot}" ]]; then
  echo "Database snapshot is missing or empty: ${st_snapshot}" >&2
  exit 1
fi

docker compose -f "${st_compose_file}" up -d --pull never mariadb
docker compose -f "${st_compose_file}" stop suitecrm

start_suitecrm_on_exit() {
  docker compose -f "${st_compose_file}" start suitecrm >/dev/null 2>&1 || true
}

trap start_suitecrm_on_exit EXIT

docker compose -f "${st_compose_file}" exec -T mariadb \
  mariadb -u root < "${st_snapshot}"

docker compose -f "${st_compose_file}" start suitecrm
trap - EXIT

for attempt in {1..120}; do
  if curl -fsS http://127.0.0.1:8080/public >/dev/null; then
    break
  fi

  if [[ "${attempt}" -eq 120 ]]; then
    echo "SuiteCRM did not become ready after database restore." >&2
    exit 1
  fi

  sleep 2
done

st_counts="$(
  docker compose -f "${st_compose_file}" exec -T mariadb \
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
