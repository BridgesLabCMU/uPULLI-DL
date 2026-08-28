#!/usr/bin/env bash
# One-shot setup for biofilm-embeddings (macOS / Linux, or Git Bash on Windows).
#
# This is a thin wrapper around scripts/setup.py, which holds the actual logic. The real
# work lives in Python because the Anaconda Prompt on Windows has no `bash`, so a shell
# script cannot be the single documented install path. Keeping one implementation means
# the two cannot drift apart.
#
#   bash scripts/setup.sh        # this wrapper
#   python scripts/setup.py      # identical, and the only option on Windows cmd/PowerShell
#
# Safe to re-run.
set -euo pipefail
cd "$(dirname "$0")/.."

# `python` is not guaranteed to exist (some installs only provide `python3`), and an
# activated conda env provides both. Prefer python3 when present.
PY="python3"
command -v python3 >/dev/null 2>&1 || PY="python"
command -v "$PY" >/dev/null 2>&1 || {
  echo "ERROR: no python interpreter on PATH. Activate your environment first:" >&2
  echo "         conda activate biofilm-embeddings" >&2
  exit 1
}

exec "$PY" scripts/setup.py "$@"
