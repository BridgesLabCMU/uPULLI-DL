#!/usr/bin/env bash
#
# TEMPLATE — DINOv2 embeddings for a dataset imaged at MORE THAN ONE magnification.
#
# WHY THIS IS A SEPARATE TEMPLATE: embeddings of different objectives describe
# different physical scales and must NOT share a cache. A single run over a mixed
# tree would silently blend them. Instead each magnification is extracted in its
# own pass with --mag, into its own cache directory via --cache-dir:
#
#   <root>/10X/embeddings/cls_cache.pt    (--mag _04)
#   <root>/4X/embeddings/cls_cache.pt     (--mag _03)
#
# Downstream, treat those as two separate embedding spaces. Do not concatenate them.
#
# ---------------------------------------------------------------------------
# DATA: <describe the dataset here>
#   organism/strains : e.g. multispecies panel across an LB dilution series
#   plates x wells   : e.g. 6 plates
#   magnifications   : e.g. _03 = 4x and _04 = 10x (every plate imaged at both)
#   frames           : e.g. 24, uniform -> pinned below with --n-frames
#   labels           : if a well -> condition table exists, note its filename here
#                      and how to join it (typically on plate + well)
# ---------------------------------------------------------------------------
#
# Usage:
#   conda activate biofilm-embeddings
#   bash extract_multi_mag_template.sh /path/to/data/root --dry-run
#   bash extract_multi_mag_template.sh /path/to/data/root --well-batch 24
#
# Extra flags are passed through to BOTH magnification passes.
#
set -euo pipefail

N_FRAMES=24

# Magnification suffix -> cache subdirectory label. Suffixes come from the `mag`
# column of each plate's index.csv; confirm yours with --dry-run before running,
# because the suffix -> objective mapping is per-plate and microscope-dependent.
MAGS=(_04 _03)
LABELS=(10X 4X)

if [[ $# -lt 1 ]]; then
    echo "usage: $(basename "$0") <data-root> [extra flags for biofilm-embeddings-run]" >&2
    exit 2
fi
ROOT="$1"; shift

if [[ ! -d "$ROOT" ]]; then
    echo "ERROR: not a directory: $ROOT" >&2
    exit 2
fi
if [[ ! -w "$ROOT" ]]; then
    echo "ERROR: $ROOT is not writable (per-mag caches are written under it)." >&2
    exit 2
fi
echo "Data root: $ROOT"

# REPO_ROOT is resolved from this script's location, not the working directory,
# so the module-form fallback works from anywhere.
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
RUN_CMD="biofilm-embeddings-run"
command -v biofilm-embeddings-run >/dev/null 2>&1 || \
    RUN_CMD="env PYTHONPATH=$REPO_ROOT/src python -m biofilm_embeddings.embeddings.extract_run"

TS=$(date +%Y%m%d_%H%M%S)
LOG="$(pwd)/extract_$(basename "$ROOT")_multimag_${TS}.log"

# Sequential per-mag passes inside one detached nohup. The bash -c body receives
# root, runner, frame count, then the user's passthrough args as positionals,
# which avoids re-quoting problems. $RUN is intentionally unquoted so the
# module-form fallback word-splits correctly.
nohup bash -c '
    ROOT="$1"; shift
    RUN="$1";  shift
    NF="$1";   shift
    MAGS_CSV="$1"; shift
    LABELS_CSV="$1"; shift
    IFS=, read -r -a MAGS   <<< "$MAGS_CSV"
    IFS=, read -r -a LABELS <<< "$LABELS_CSV"
    for i in "${!MAGS[@]}"; do
        mag="${MAGS[$i]}"; lbl="${LABELS[$i]}"
        echo "===== embedding mag $mag  ->  $ROOT/$lbl/embeddings/cls_cache.pt ====="
        $RUN "$ROOT" --mag "$mag" --n-frames "$NF" --cache-dir "$ROOT/$lbl" "$@" \
            || echo "  mag $mag FAILED (rc=$?) — continuing to next mag"
    done
' _ "$ROOT" "$RUN_CMD" "$N_FRAMES" \
    "$(IFS=,; echo "${MAGS[*]}")" "$(IFS=,; echo "${LABELS[*]}")" \
    "$@" < /dev/null > "$LOG" 2>&1 &
PID=$!

echo
echo "Multi-magnification embedding run launched detached (survives logout)."
echo "  Root:    $ROOT"
echo "  Mags:    ${MAGS[*]}  ->  ${LABELS[*]} (separate caches)"
echo "  Frames:  $N_FRAMES"
echo "  PID:     $PID"
echo "  Log:     $LOG"
echo "  Monitor: tail -f \"$LOG\""
echo "  Stop:    kill $PID"
