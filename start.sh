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

if [[ -f server.pid ]]; then
  service_pid="$(<server.pid)"
  if [[ ! "$service_pid" =~ ^[1-9][0-9]*$ ]]; then
    printf '%s\n' 'Invalid server.pid; inspect it before starting.' >&2
    exit 1
  fi
  if kill -0 "$service_pid" 2>/dev/null; then
    process_directory="$(readlink "/proc/$service_pid/cwd" || true)"
    process_command="$(ps -ww -p "$service_pid" -o args= || true)"
    if [[ "$process_directory" != "$project_root" ||
          "$process_command" != "$project_root/.venv/bin/python -B -u -m carstream" ]]; then
      printf '%s\n' 'server.pid belongs to another process; refusing to replace it.' >&2
      exit 1
    fi
    printf 'CarStream is already running (PID %s).\n' "$service_pid"
    exit 0
  fi
  rm server.pid
fi

[[ -f .env ]] || { printf '%s\n' 'Missing .env; see README.' >&2; exit 1; }
[[ -x .venv/bin/python ]] || { printf '%s\n' 'Missing .venv/bin/python; see README.' >&2; exit 1; }
set -a
. ./.env
set +a
"$project_root/.venv/bin/python" -c 'from carstream.config import Settings; Settings.from_environment()'
service_port="${CARSTREAM_PORT:-8080}"
listeners="$(ss -H -ltn "sport = :$service_port")"
if [[ -n "$listeners" ]]; then
  printf 'Port %s is already listening; no service was started.\n' "$service_port" >&2
  exit 1
fi

mkdir -p log
chmod 700 log
log_file="$project_root/log/carstream-$(date -u +%Y%m%dT%H%M%S.%NZ).log"
touch "$log_file"
chmod 600 "$log_file"
# Do not let the background service retain the lifecycle-operation lock.
nohup "$project_root/.venv/bin/python" -B -u -m carstream >>"$log_file" 2>&1 < /dev/null 9>&- &
service_pid=$!
printf '%s\n' "$service_pid" >server.pid
chmod 600 server.pid

for attempt in {1..50}; do
  if ! kill -0 "$service_pid" 2>/dev/null; then
    wait "$service_pid" || true
    rm server.pid
    printf 'Startup failed; inspect %s.\n' "$log_file" >&2
    exit 1
  fi
  listeners="$(ss -H -ltnp "sport = :$service_port")"
  if [[ "$listeners" == *"pid=$service_pid,"* ]]; then
    printf 'CarStream started (PID %s, port %s). Log: %s\n' \
      "$service_pid" "$service_port" "$log_file"
    exit 0
  fi
  sleep 0.2
done

printf 'PID %s has not opened port %s within 10 seconds. Inspect %s; use ./stop.sh before retrying.\n' \
  "$service_pid" "$service_port" "$log_file" >&2
exit 1
