#!/usr/bin/env bash
set -euo pipefail

# Target is fixed to this task's board; SSH prompts normally, no embedded password.
project_root="$(cd "$(dirname "$0")/.." && pwd)"
target="${CARSTREAM_SSH_TARGET:-cat@100.94.108.3}"
release_name="carstream-$(date -u +%Y%m%dT%H%M%SZ)"
remote_directory="/home/cat/${release_name}"

ssh -o ConnectTimeout=30 "$target" \
  "test -d /home/cat && ls -ld /home/cat && test ! -e '$remote_directory' && mkdir -m 700 '$remote_directory'"

# Allowlist only project artifacts. No .env, .venv, local credentials or deletion.
cd "$project_root"
rsync -rtpv --stats --timeout=60 \
  --exclude='__pycache__' --exclude='*.pyc' --exclude='.DS_Store' \
  -e 'ssh -o ConnectTimeout=30' \
  carstream tests scripts docs start.sh stop.sh README.md pyproject.toml requirements.txt \
  uv.lock .env.example .gitignore progress.md "$target:$remote_directory/"

printf '\nUploaded without installing or starting anything: %s:%s\n' "$target" "$remote_directory"
printf 'Rollback (preserve files, disable this release): ssh %s "mv %s %s.disabled"\n' \
  "$target" "$remote_directory" "$remote_directory"
