#!/usr/bin/env bash

set -euo pipefail

st_script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
st_repo_root="$(cd "${st_script_dir}/../../.." && pwd)"
st_compose_file="${st_repo_root}/external/ST-WebAgentBench/suitecrm_setup/docker-compose.yaml"
st_reset="${st_script_dir}/reset_suitecrm_db.sh"
st_prepare="${st_script_dir}/prepare_suitecrm_worker.sh"
st_worker_1="gse_suitecrm_isolation_worker_1"
st_worker_2="gse_suitecrm_isolation_worker_2"

st_cleanup() {
  SUITECRM_PORT=8181 docker compose -p "${st_worker_1}" -f "${st_compose_file}" down -v >/dev/null 2>&1 || true
  SUITECRM_PORT=8182 docker compose -p "${st_worker_2}" -f "${st_compose_file}" down -v >/dev/null 2>&1 || true
}

trap st_cleanup EXIT

GSE_COMPOSE_PROJECT="${st_worker_1}" SUITECRM_PORT=8181 "${st_prepare}"
GSE_COMPOSE_PROJECT="${st_worker_2}" SUITECRM_PORT=8182 "${st_prepare}"
GSE_COMPOSE_PROJECT="${st_worker_1}" SUITECRM_PORT=8181 "${st_reset}"
GSE_COMPOSE_PROJECT="${st_worker_2}" SUITECRM_PORT=8182 "${st_reset}"

st_query="SELECT COALESCE(title, '__NULL__') FROM bitnami_suitecrm.contacts WHERE first_name='Michael' AND last_name='Scott' AND deleted=0 LIMIT 1;"
st_update="UPDATE bitnami_suitecrm.contacts SET title='__WORKER1_TEST__' WHERE first_name='Michael' AND last_name='Scott' AND deleted=0;"

docker compose -p "${st_worker_1}" -f "${st_compose_file}" exec -T mariadb mariadb -u root -e "${st_update}"
st_worker_1_value="$(docker compose -p "${st_worker_1}" -f "${st_compose_file}" exec -T mariadb mariadb -u root -Nse "${st_query}")"
st_worker_2_pristine="$(docker compose -p "${st_worker_2}" -f "${st_compose_file}" exec -T mariadb mariadb -u root -Nse "${st_query}")"

if [[ "${st_worker_1_value}" != "__WORKER1_TEST__" ]]; then
  echo "Worker 1 mutation was not visible in Worker 1." >&2
  exit 1
fi
if [[ "${st_worker_2_pristine}" != "__NULL__" ]]; then
  echo "Worker 1 mutation leaked into Worker 2." >&2
  exit 1
fi

GSE_COMPOSE_PROJECT="${st_worker_1}" SUITECRM_PORT=8181 "${st_reset}"
st_worker_1_restored="$(docker compose -p "${st_worker_1}" -f "${st_compose_file}" exec -T mariadb mariadb -u root -Nse "${st_query}")"
st_worker_2_after_reset="$(docker compose -p "${st_worker_2}" -f "${st_compose_file}" exec -T mariadb mariadb -u root -Nse "${st_query}")"

if [[ "${st_worker_1_restored}" != "__NULL__" ]]; then
  echo "Worker 1 reset did not restore the pristine value." >&2
  exit 1
fi
if [[ "${st_worker_2_after_reset}" != "__NULL__" ]]; then
  echo "Worker 1 reset changed Worker 2." >&2
  exit 1
fi

printf 'Worker DB isolation verified: worker1=%q, worker2=%q\n' \
  "${st_worker_1_restored}" "${st_worker_2_after_reset}"
