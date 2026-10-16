#!/usr/bin/env bash
# Steam wrapper: preserve the game command and its exit code.
set -u
ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
PYTHON="$ROOT/.venv/bin/python"
if [[ ! -x "$PYTHON" ]]; then
  PYTHON="$(command -v python3 || true)"
fi
if [[ -z "$PYTHON" ]]; then
  echo 'Python 3 is required for MCSM Live Presence.' >&2
  exit 1
fi
if [[ $# -eq 0 ]]; then
  echo 'Use this wrapper before %command% in Steam launch options.' >&2
  exit 2
fi
PRESENCE_PID=''
cleanup() {
  if [[ -n "$PRESENCE_PID" ]]; then
    kill -TERM "$PRESENCE_PID" 2>/dev/null || true
    wait "$PRESENCE_PID" 2>/dev/null || true
  fi
}
trap cleanup EXIT
export PYTHONPATH="$ROOT/src${PYTHONPATH:+:$PYTHONPATH}"
export MCSM_PRESENCE_SESSION_NS="$("$PYTHON" -c 'import time; print(time.time_ns())')"
"$PYTHON" -m mcsm_live_presence run &
PRESENCE_PID=$!
"$@"
exit $?
