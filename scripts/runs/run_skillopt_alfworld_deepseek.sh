#!/usr/bin/env bash
# Run from any directory, using the dedicated skillopt conda environment.
# With no arguments this prints a non-secret configuration summary only.
set -euo pipefail
TASK_ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
export SKILLOPT_PYTHON=/Users/didi/miniforge3/envs/skillopt/bin/python
export PATH="/Users/didi/miniforge3/envs/skillopt/bin:$PATH"
if [[ -f "$TASK_ROOT/.env" ]]; then
  set -a
  source "$TASK_ROOT/.env"
  set +a
fi
export ALFWORLD_DATA=/Users/didi/.cache/alfworld
export PYTHONUNBUFFERED=1
export PYTHONDONTWRITEBYTECODE=1
: "${OPENAI_API_KEY:?Set OPENAI_API_KEY in the project .env or environment}"
: "${OPENAI_BASE_URL:?Set OPENAI_BASE_URL in the project .env or environment}"
if [[ "${OPENAI_BASE_URL%/}" != "http://llm-proxy.intra.xiaojukeji.com" ]]; then
  echo 'Expected the V23.4 internal API endpoint.' >&2
  exit 1
fi
export OPENAI_COMPATIBLE_BASE_URL="${OPENAI_BASE_URL%/}"
export OPENAI_COMPATIBLE_API_KEY="$OPENAI_API_KEY"
export OPENAI_COMPATIBLE_TEMPERATURE=1
export OPENAI_COMPATIBLE_MAX_TOKENS=16384
export OPENAI_COMPATIBLE_TIMEOUT_SECONDS=300
export OPENAI_COMPATIBLE_CONNECT_TIMEOUT_SECONDS=10
export OPENAI_COMPATIBLE_MAX_ATTEMPTS=3
export OPENAI_COMPATIBLE_EXTRA_BODY='{"thinking":{"type":"enabled"},"reasoning_effort":"medium","stream":false}'
# Explicit role values prevent an older shell configuration overriding this run.
for role in OPTIMIZER TARGET; do
  for field in BASE_URL API_KEY TEMPERATURE MAX_TOKENS TIMEOUT_SECONDS MAX_ATTEMPTS EXTRA_BODY; do
    shared="OPENAI_COMPATIBLE_${field}"
    export "${role}_OPENAI_COMPATIBLE_${field}=${!shared}"
  done
done
export NO_PROXY="${NO_PROXY:+$NO_PROXY,}llm-proxy.intra.xiaojukeji.com"
export no_proxy="$NO_PROXY"
cd "$TASK_ROOT/external/SkillOpt"
case "${1:-check}" in
  check)
    echo 'SkillOpt target + optimizer: deepseek-v4.1-flash (internal proxy)'
    echo 'temperature=1, thinking=enabled, reasoning_effort=medium, stream=false'
    echo 'max_tokens cap=16384, timeout=300s, connect=10s, HTTP attempts<=3'
    echo 'ALFWorld: max_steps=50, workers=8; original SkillOpt learning/splits retained.'
    echo 'No network request or benchmark was started.'
    ;;
  train|eval)
    mode="$1"
    shift
    script=scripts/train.py
    [[ "$mode" != eval ]] || script=scripts/eval_only.py
    exec "${SKILLOPT_PYTHON:-python}" "$script" \
      --config "$TASK_ROOT/experiments/configs/skillopt_alfworld_deepseek_v23_4.yaml" "$@"
    ;;
  *) echo 'Usage: bash run_skillopt_alfworld_deepseek.sh [check|train|eval] [SkillOpt arguments]' >&2; exit 2 ;;
esac
