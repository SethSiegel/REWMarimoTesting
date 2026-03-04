#!/usr/bin/env bash
set -euo pipefail

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
repo_dir="$(cd "$script_dir/.." && pwd)"
cd "$repo_dir"

if [[ -x ".venv/bin/python" ]]; then
  ./.venv/bin/python ./launcher/build_rew_dashboard.py
elif command -v uv >/dev/null 2>&1; then
  uv run python ./launcher/build_rew_dashboard.py
else
  python3 ./launcher/build_rew_dashboard.py
fi
