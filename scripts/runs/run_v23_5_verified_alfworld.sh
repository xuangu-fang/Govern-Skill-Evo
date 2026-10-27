#!/usr/bin/env bash
set -euo pipefail
TASK_ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
TASK_PYTHON=/Users/didi/miniforge3/envs/alfworld/bin/python
TASK_EXPERIMENT="$TASK_ROOT/experiments/methods/v23_5/alfworld_verified_feedback_001"
TASK_CAMPAIGN="$TASK_ROOT/artifacts/methods/v23_5/alfworld_verified_feedback_001/S1"
TASK_EVALUATION="$(dirname "$TASK_CAMPAIGN")/evaluation/final"
TASK_ACTION="${1:-check}"
export PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
export ALFWORLD_DATA=/Users/didi/.cache/alfworld
cd "$TASK_ROOT"
case "$TASK_ACTION" in
  check) exec "$TASK_PYTHON" scripts/runs/prepare_v23_5_alfworld.py --knowledge-review --experiment-dir "$TASK_EXPERIMENT" ;;
  status) exec "$TASK_PYTHON" -m src.skill_evolution.v23_5.evolution status --campaign "$TASK_CAMPAIGN" ;;
  test-status) exec "$TASK_PYTHON" -m src.skill_evolution.v23_5.evaluation status --root "$TASK_EVALUATION" ;;
  run|resume|test|test-resume|full|resume-full) ;;
  *) echo 'Usage: run_v23_5_verified_alfworld.sh [check|run|resume|test|test-resume|full|resume-full|status|test-status]' >&2; exit 2 ;;
esac
# Environment variables are loaded inside the Python entry points. Never print keys.
if [[ "$TASK_ACTION" == run || "$TASK_ACTION" == full ]]; then
  [[ ! -f "$TASK_CAMPAIGN/state.json" ]] || { echo 'Campaign exists; use resume.' >&2; exit 1; }
  "$TASK_PYTHON" scripts/runs/prepare_v23_5_alfworld.py --knowledge-review --experiment-dir "$TASK_EXPERIMENT"
  "$TASK_PYTHON" -m src.skill_evolution.v23_5.evolution run --campaign "$TASK_CAMPAIGN" --config "$TASK_EXPERIMENT/config/campaign.json"
elif [[ "$TASK_ACTION" == resume || "$TASK_ACTION" == resume-full ]]; then
  "$TASK_PYTHON" -m src.skill_evolution.v23_5.evolution resume --campaign "$TASK_CAMPAIGN"
fi
if [[ "$TASK_ACTION" == test || "$TASK_ACTION" == test-resume || "$TASK_ACTION" == full || "$TASK_ACTION" == resume-full ]]; then
  TASK_TEST_ACTION=run
  [[ "$TASK_ACTION" != test-resume && ! -f "$TASK_EVALUATION/input.json" ]] || TASK_TEST_ACTION=resume
  exec "$TASK_PYTHON" -m src.skill_evolution.v23_5.evaluation "$TASK_TEST_ACTION" --root "$TASK_EVALUATION" --experiment "$TASK_EXPERIMENT" --campaign "$TASK_CAMPAIGN"
fi
