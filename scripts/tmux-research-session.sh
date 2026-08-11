#!/usr/bin/env bash
set -Eeuo pipefail

session_name="${1:-cotcodec}"
repo_dir="$(pwd -P)"

if [[ ! "${session_name}" =~ ^[A-Za-z0-9_-]{1,40}$ ]]; then
  echo "session name must use 1-40 letters, numbers, underscores, or hyphens" >&2
  exit 2
fi
if ! command -v tmux >/dev/null 2>&1; then
  echo "tmux is required on the cluster login host" >&2
  exit 1
fi

if tmux has-session -t "=${session_name}" 2>/dev/null; then
  if [[ -n "${TMUX:-}" ]]; then
    exec tmux switch-client -t "=${session_name}"
  fi
  exec tmux attach-session -t "=${session_name}"
fi

exec tmux new-session -s "${session_name}" -c "${repo_dir}"
