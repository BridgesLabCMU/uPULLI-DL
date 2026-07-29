#!/usr/bin/env bash
#
# TEMPLATE — DINOv2 embeddings for one already-processed dataset (single magnification).
#
# Copy this per dataset and fill in the DATA block below. The point of keeping one
# script per dataset is that the script IS the reproducible record: it pins the
# frame count and any non-default model settings, so re-running it months later
# reproduces the same cache rather than whatever the defaults happen to be.
#
# EMBED-ONLY: assumes image processing has already run. This walks every
# <plate>/processedImages/index.csv under the data root, embeds each well's
# _processed.tif, and writes <root>/embeddings/cls_cache.pt. Run it on a GPU
# machine; it detaches with nohup so it survives logout.
#
# ---------------------------------------------------------------------------
# DATA: <describe the dataset here — this block is the part worth keeping>
#   organism/strains : e.g. 6 K. pneumoniae mutants, one per plate
#   plates x wells   : e.g. 6 plates x 96 wells = 576
#   magnification    : e.g. _02 = 4x (single mag, so one cache at <root>/embeddings/)
#   frames           : e.g. 25, uniform  -> pinned below with --n-frames
#   model settings   : defaults (dinov2-base / 518 / grid 3) unless noted
#
# COMPARABILITY: embeddings are only comparable across datasets that share the
# same magnification, frame count, model, image size, and grid size. A 4x/25-frame
# set is NOT comparable to a 10x/31-frame set.
# ---------------------------------------------------------------------------
#
# Usage:
#   conda activate biofilm-embeddings
#   bash extract_dataset_template.sh /path/to/data/root --dry-run          # verify, no GPU
#   bash extract_dataset_template.sh /path/to/data/root --well-batch 24    # full run
#
# Any extra flags are passed straight through to biofilm-embeddings-run.
#
set -euo pipefail

# --- Frames per stack. Pin this explicitly. -------------------------------
# Inferring from the first stack is fragile: if the first well happens to be a
# short one, every other well gets truncated to match it. Wells with FEWER than
# this are skipped and listed in <root>/embeddings/excluded_short_wells.csv.
N_FRAMES=25

# --- Data root comes from the caller, not from this file ------------------
# Do not hardcode mount points here: they differ per machine and leak local
# storage layout into a public repository.
if [[ $# -lt 1 ]]; then
    echo "usage: $(basename "$0") <data-root> [extra flags for biofilm-embeddings-run]" >&2
    echo "  <data-root> is the directory containing <plate>/processedImages/index.csv" >&2
    exit 2
fi
ROOT="$1"; shift

if [[ ! -d "$ROOT" ]]; then
    echo "ERROR: not a directory: $ROOT" >&2
    exit 2
fi
if [[ ! -w "$ROOT" ]]; then
    echo "ERROR: $ROOT is not writable (the cache is written to <root>/embeddings/)." >&2
    echo "       Use --cache-dir to write elsewhere if the source tree is read-only." >&2
    exit 2
fi
echo "Data root: $ROOT"

# Prefer the installed console script; fall back to module form for a source
# checkout. REPO_ROOT is resolved from this script's own location (examples/ is
# two levels below the repo root) rather than from the working directory, so the
# fallback works no matter where you invoke this from.
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
RUN_CMD="biofilm-embeddings-run"
command -v biofilm-embeddings-run >/dev/null 2>&1 || \
    RUN_CMD="env PYTHONPATH=$REPO_ROOT/src python -m biofilm_embeddings.embeddings.extract_run"

TS=$(date +%Y%m%d_%H%M%S)
LOG="$(pwd)/extract_$(basename "$ROOT")_${TS}.log"

# shellcheck disable=SC2086  # RUN_CMD may be multi-word (module-form fallback)
nohup $RUN_CMD "$ROOT" --n-frames "$N_FRAMES" "$@" < /dev/null > "$LOG" 2>&1 &
PID=$!

echo
echo "Embedding run launched detached (survives logout)."
echo "  Root:    $ROOT"
echo "  Frames:  $N_FRAMES"
echo "  PID:     $PID"
echo "  Log:     $LOG"
echo "  Monitor: tail -f \"$LOG\""
echo "  Stop:    kill $PID"
echo "  Output:  $ROOT/embeddings/cls_cache.pt"
