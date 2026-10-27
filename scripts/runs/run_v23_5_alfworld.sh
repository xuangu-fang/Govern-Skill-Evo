#!/usr/bin/env bash
set -euo pipefail
TASK_ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
TASK_PYTHON=/Users/didi/miniforge3/envs/alfworld/bin/python
TASK_CAMPAIGN="$TASK_ROOT/artifacts/methods/v23_5/alfworld_action_feedback_001/S1"
TASK_CONFIG="$TASK_ROOT/experiments/methods/v23_5/alfworld_action_feedback_001/config/campaign.json"
export PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
cd "$TASK_ROOT"
case "${1:-check}" in
  check) exec "$TASK_PYTHON" scripts/runs/prepare_v23_5_alfworld.py ;;
  status) exec "$TASK_PYTHON" -m src.skill_evolution.v23_5.evolution status --campaign "$TASK_CAMPAIGN" ;;
  test-status) exec "$TASK_PYTHON" -m src.skill_evolution.v23_5.evaluation status ;;
  run|resume|test|test-resume) ;;
  *) echo 'Usage: run_v23_5_alfworld.sh [check|run|resume|status|test|test-resume|test-status]' >&2; exit 2 ;;
esac
# Existing process variables take precedence; dotenv never prints credentials.
eval "$("$TASK_PYTHON" - <<'PY'
from dotenv import dotenv_values
import os, shlex
for name, value in dotenv_values('.env').items():
    if name in ('OPENAI_API_KEY', 'OPENAI_BASE_URL') and name not in os.environ and value:
        print('export ' + name + '=' + shlex.quote(value))
PY
)"
: "${OPENAI_API_KEY:?Set OPENAI_API_KEY in environment or ignored .env}"
: "${OPENAI_BASE_URL:?Set OPENAI_BASE_URL in environment or ignored .env}"
export NO_PROXY="${NO_PROXY:+$NO_PROXY,}llm-proxy.intra.xiaojukeji.com"
export no_proxy="$NO_PROXY"
export ALFWORLD_DATA=/Users/didi/.cache/alfworld
if [[ "$1" == test || "$1" == test-resume ]]; then
  TASK_ACTION=run
  [[ "$1" != test-resume ]] || TASK_ACTION=resume
  exec "$TASK_PYTHON" -m src.skill_evolution.v23_5.evaluation "$TASK_ACTION"
fi
if [[ "$1" == run ]]; then
  if [[ -f "$TASK_CAMPAIGN/state.json" ]]; then
    echo 'Campaign already initialized; use resume explicitly.' >&2
    exit 1
  fi
  "$TASK_PYTHON" scripts/runs/prepare_v23_5_alfworld.py
  exec "$TASK_PYTHON" -m src.skill_evolution.v23_5.evolution run --campaign "$TASK_CAMPAIGN" --config "$TASK_CONFIG"
else
  exec "$TASK_PYTHON" -m src.skill_evolution.v23_5.evolution resume --campaign "$TASK_CAMPAIGN"
fi
