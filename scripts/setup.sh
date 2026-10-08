#!/usr/bin/env bash
# One-shot setup for biofilm-embeddings (macOS / Linux, or Git Bash on Windows).
# Thin wrapper around scripts/setup.py, which holds the logic. Safe to re-run.
#
#   bash scripts/setup.sh        # this wrapper
#   python scripts/setup.py      # identical, and the only option on Windows cmd/PowerShell
set -euo pipefail
cd "$(dirname "$0")/.."

PY="python3"
command -v python3 >/dev/null 2>&1 || PY="python"
command -v "$PY" >/dev/null 2>&1 || {
  echo "ERROR: no python interpreter on PATH. Activate your environment first:" >&2
  echo "         conda activate biofilm-embeddings" >&2
  exit 1
}

exec "$PY" scripts/setup.py "$@"
