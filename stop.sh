#!/usr/bin/env bash
set -euo pipefail

if [[ "$(uname -s)" != Linux ]]; then
  printf '%s\n' 'Run this script on the Ubuntu board.' >&2
  exit 1
fi

project_root="$(cd "$(dirname "$0")" && pwd -P)"
cd "$project_root"
umask 077
exec 9>server.lock
flock -n 9 || { printf '%s\n' 'Another start/stop operation is running.' >&2; exit 1; }

if [[ ! -f server.pid ]]; then
  printf '%s\n' 'No server.pid; no process was stopped.'
  exit 0
fi
service_pid="$(<server.pid)"
if [[ ! "$service_pid" =~ ^[1-9][0-9]*$ ]]; then
  printf '%s\n' 'Invalid server.pid; no signal was sent.' >&2
  exit 1
fi
if ! kill -0 "$service_pid" 2>/dev/null; then
  rm server.pid
  printf '%s\n' 'Recorded process has exited; removed stale server.pid.'
  exit 0
fi

process_directory="$(readlink "/proc/$service_pid/cwd" || true)"
process_command="$(ps -ww -p "$service_pid" -o args= || true)"
if [[ "$process_directory" != "$project_root" ||
      "$process_command" != "$project_root/.venv/bin/python -B -u -m carstream" ]]; then
  printf '%s\n' 'server.pid belongs to another process; no signal was sent.' >&2
  exit 1
fi

kill -TERM "$service_pid"
for attempt in {1..60}; do
  process_state="$(ps -p "$service_pid" -o stat= || true)"
  if ! kill -0 "$service_pid" 2>/dev/null || [[ "$process_state" == Z* ]]; then
    rm server.pid
    printf 'CarStream stopped (PID %s).\n' "$service_pid"
    exit 0
  fi
  sleep 0.5
done

printf 'PID %s has not exited within 30 seconds. Inspect log/; no forced kill was sent.\n' \
  "$service_pid" >&2
exit 1
